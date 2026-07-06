"""The demiurge command-line interface.

demiurge mint <need.yaml> [--stable-dir DIR]   mint an Archon from a need statement
demiurge validate <file.agf.yaml>              validate any Agent Format document
demiurge scaffold <archon-id>                  generate a runnable project for an Archon
demiurge deploy <archon-id> [--port N]         scaffold (if needed) and serve over A2A
demiurge delegate <archon-id> <text>           send a task to a running Archon; record it
demiurge admit <archon-id> --endpoint URL      run the eval suite; full pass enters the stable
demiurge verdict <archon-id> <task-id> ...     judge a delegated task (success/failure)
demiurge distill <archon-id> <task-id> ...     turn a field failure into a regression eval
demiurge tenure <archon-id>                    summarize outcomes into keep/revise/retire
demiurge retire <archon-id> --reason ...       end an Archon's tenure
demiurge revise <need.yaml>                    re-mint from an updated need, keep earned evals
"""

import argparse
import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from demiurge.adapters import DeployError, get_adapter
from demiurge.curate import (
    admit,
    distill_failure,
    record_verdict,
    retire,
    revise,
    tenure_review,
)
from demiurge.delegate import DelegationError, delegate, record_delegation
from demiurge.mint.need import load_need
from demiurge.mint.pipeline import MintError, mint
from demiurge.spec.validate import validate_document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="demiurge",
        description="Mint, delegate to, and curate Archon agents.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    mint_parser = subparsers.add_parser("mint", help="mint an Archon from a need statement")
    mint_parser.add_argument("need", type=Path, help="path to a need-statement YAML file")
    mint_parser.add_argument(
        "--stable-dir",
        type=Path,
        default=Path("stable"),
        help="directory holding the Archon stable (default: ./stable)",
    )

    validate_parser = subparsers.add_parser(
        "validate", help="validate a .agf.yaml document against the Agent Format schema"
    )
    validate_parser.add_argument("file", type=Path, help="path to an Agent Format YAML document")

    scaffold_parser = subparsers.add_parser(
        "scaffold", help="generate a runnable project for a minted Archon"
    )
    deploy_parser = subparsers.add_parser(
        "deploy", help="scaffold (if needed) and serve an Archon over A2A"
    )
    for subparser in (scaffold_parser, deploy_parser):
        subparser.add_argument("archon_id", help="id of a minted Archon in the stable")
        subparser.add_argument("--stable-dir", type=Path, default=Path("stable"))
        subparser.add_argument(
            "--scaffold-dir",
            type=Path,
            default=Path("scaffolds"),
            help="directory holding generated projects (default: ./scaffolds)",
        )
        subparser.add_argument(
            "--adapter", default="claude-sdk", help="runtime adapter (default: claude-sdk)"
        )
    deploy_parser.add_argument("--port", type=int, default=9999)
    deploy_parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="seconds to wait for the Archon to become healthy (default: 300)",
    )

    delegate_parser = subparsers.add_parser(
        "delegate", help="send a task to a running Archon and record it in the ledger"
    )
    delegate_parser.add_argument("archon_id", help="id of a minted Archon in the stable")
    delegate_parser.add_argument("text", help="the task to delegate")
    delegate_parser.add_argument("--stable-dir", type=Path, default=Path("stable"))
    delegate_parser.add_argument(
        "--endpoint",
        default="http://127.0.0.1:9999",
        help="base URL of the running Archon (default: http://127.0.0.1:9999)",
    )
    delegate_parser.add_argument("--timeout", type=float, default=300.0)

    admit_parser = subparsers.add_parser(
        "admit", help="run the eval suite against a running Archon; a full pass admits it"
    )
    admit_parser.add_argument("archon_id")
    admit_parser.add_argument("--endpoint", default="http://127.0.0.1:9999")
    admit_parser.add_argument("--stable-dir", type=Path, default=Path("stable"))
    admit_parser.add_argument("--timeout", type=float, default=300.0)

    verdict_parser = subparsers.add_parser("verdict", help="record a judgment on a delegated task")
    verdict_parser.add_argument("archon_id")
    verdict_parser.add_argument("task_id")
    verdict_parser.add_argument("--outcome", choices=("success", "failure"), required=True)
    verdict_parser.add_argument("--note", default="")
    verdict_parser.add_argument("--stable-dir", type=Path, default=Path("stable"))

    distill_parser = subparsers.add_parser(
        "distill", help="distill a failed delegation into a regression eval case"
    )
    distill_parser.add_argument("archon_id")
    distill_parser.add_argument("task_id")
    distill_parser.add_argument("--note", required=True, help="what went wrong / what must hold")
    distill_parser.add_argument(
        "--expect-contains",
        action="append",
        default=[],
        help="machine-checkable substring the fixed response must contain (repeatable)",
    )
    distill_parser.add_argument("--stable-dir", type=Path, default=Path("stable"))

    tenure_parser = subparsers.add_parser(
        "tenure", help="summarize ledger outcomes into keep/revise/retire"
    )
    tenure_parser.add_argument("archon_id")
    tenure_parser.add_argument("--stable-dir", type=Path, default=Path("stable"))
    tenure_parser.add_argument("--window", type=int, default=20)

    retire_parser = subparsers.add_parser("retire", help="end an Archon's tenure")
    retire_parser.add_argument("archon_id")
    retire_parser.add_argument("--reason", required=True)
    retire_parser.add_argument("--stable-dir", type=Path, default=Path("stable"))

    revise_parser = subparsers.add_parser(
        "revise", help="re-mint an existing Archon from an updated need statement"
    )
    revise_parser.add_argument("need", type=Path)
    revise_parser.add_argument("--stable-dir", type=Path, default=Path("stable"))

    args = parser.parse_args(argv)
    if args.command == "mint":
        return _cmd_mint(args.need, args.stable_dir)
    if args.command == "scaffold":
        return _cmd_scaffold(args)
    if args.command == "deploy":
        return _cmd_deploy(args)
    if args.command == "delegate":
        return _cmd_delegate(args)
    if args.command in ("admit", "verdict", "distill", "tenure", "retire", "revise"):
        return _cmd_curate(args)
    return _cmd_validate(args.file)


def _cmd_mint(need_path: Path, stable_dir: Path) -> int:
    try:
        need = load_need(need_path)
    except (OSError, ValueError, ValidationError) as error:
        print(f"demiurge: invalid need statement: {error}", file=sys.stderr)
        return 2
    try:
        result = mint(need, stable_dir)
    except MintError as error:
        print(f"demiurge: {error}", file=sys.stderr)
        return 1
    print(f"minted archon '{result.archon_id}' (status: specced)")
    for path in (result.spec_path, result.charter_path, result.evals_path, result.record_path):
        print(f"  {path}")
    return 0


def _cmd_scaffold(args: argparse.Namespace) -> int:
    archon_dir = args.stable_dir / args.archon_id
    if not archon_dir.is_dir():
        print(f"demiurge: no archon '{args.archon_id}' in {args.stable_dir}", file=sys.stderr)
        return 2
    try:
        adapter = get_adapter(args.adapter)
    except ValueError as error:
        print(f"demiurge: {error}", file=sys.stderr)
        return 2
    result = adapter.scaffold(archon_dir, args.scaffold_dir)
    print(f"scaffolded '{result.archon_id}' ({args.adapter}) at {result.scaffold_dir}")
    return 0


def _cmd_deploy(args: argparse.Namespace) -> int:
    scaffold_dir = args.scaffold_dir / args.archon_id
    if not scaffold_dir.is_dir():
        exit_code = _cmd_scaffold(args)
        if exit_code != 0:
            return exit_code
    adapter = get_adapter(args.adapter)
    try:
        deployment = adapter.deploy(scaffold_dir, port=args.port, timeout_seconds=args.timeout)
    except DeployError as error:
        print(f"demiurge: {error}", file=sys.stderr)
        return 1
    print(f"archon '{deployment.archon_id}' is up at {deployment.endpoint}")
    print(f"  agent card: {deployment.agent_card_url}")
    print("  Ctrl+C to stop")
    try:
        deployment.process.wait()
    except KeyboardInterrupt:
        deployment.teardown()
        print(f"archon '{deployment.archon_id}' stopped")
    return 0


def _cmd_delegate(args: argparse.Namespace) -> int:
    archon_dir = args.stable_dir / args.archon_id
    if not archon_dir.is_dir():
        print(f"demiurge: no archon '{args.archon_id}' in {args.stable_dir}", file=sys.stderr)
        return 2
    try:
        result = delegate(args.endpoint, args.text, timeout=args.timeout)
    except DelegationError as error:
        print(f"demiurge: {error}", file=sys.stderr)
        return 1
    record_delegation(archon_dir, args.text, result)
    print(f"state: {result.state} ({result.duration_seconds}s)")
    print(result.text)
    return 0


def _cmd_curate(args: argparse.Namespace) -> int:
    if args.command == "revise":
        try:
            need = load_need(args.need)
        except (OSError, ValueError, ValidationError) as error:
            print(f"demiurge: invalid need statement: {error}", file=sys.stderr)
            return 2
        try:
            result = revise(need, args.stable_dir)
        except FileNotFoundError as error:
            print(f"demiurge: {error}", file=sys.stderr)
            return 2
        print(
            f"revised archon '{result.archon_id}' to "
            f"v{result.spec.metadata.version} (status: specced — must re-pass admission)"
        )
        return 0

    archon_dir = args.stable_dir / args.archon_id
    if not archon_dir.is_dir():
        print(f"demiurge: no archon '{args.archon_id}' in {args.stable_dir}", file=sys.stderr)
        return 2

    if args.command == "admit":
        try:
            report = admit(archon_dir, args.endpoint, timeout=args.timeout)
        except DelegationError as error:
            print(f"demiurge: {error}", file=sys.stderr)
            return 1
        for result in report.results:
            marker = "PASS" if result.passed else "FAIL"
            print(f"  [{marker}] {result.case_id} ({result.origin})")
            for check in result.checks:
                print(f"         {check}")
        if report.passed:
            print(f"archon '{args.archon_id}' ADMITTED to the stable")
            return 0
        print(f"archon '{args.archon_id}' NOT admitted — status remains specced")
        return 1

    if args.command == "verdict":
        try:
            entry = record_verdict(archon_dir, args.task_id, args.outcome, args.note)
        except ValueError as error:
            print(f"demiurge: {error}", file=sys.stderr)
            return 2
        print(f"recorded {entry['outcome']} verdict for task {args.task_id}")
        return 0

    if args.command == "distill":
        try:
            case = distill_failure(
                archon_dir, args.task_id, args.note, expect_contains=args.expect_contains
            )
        except ValueError as error:
            print(f"demiurge: {error}", file=sys.stderr)
            return 2
        print(f"distilled task {args.task_id} into eval case '{case.id}' (origin: field-failure)")
        return 0

    if args.command == "tenure":
        report = tenure_review(archon_dir, window=args.window)
        print(f"archon '{report.archon_id}': {report.recommendation.upper()}")
        for reason in report.reasons:
            print(f"  - {reason}")
        return 0

    retire(archon_dir, args.reason)
    print(f"archon '{args.archon_id}' retired: {args.reason}")
    return 0


def _cmd_validate(file: Path) -> int:
    try:
        document = yaml.safe_load(file.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        print(f"demiurge: cannot read {file}: {error}", file=sys.stderr)
        return 2
    if not isinstance(document, dict):
        print(f"demiurge: {file}: not a YAML mapping", file=sys.stderr)
        return 2
    errors = validate_document(document)
    if errors:
        print(f"{file}: {len(errors)} schema violation(s):", file=sys.stderr)
        for message in errors:
            print(f"  {message}", file=sys.stderr)
        return 1
    print(f"{file}: valid Agent Format {document.get('schema_version', '?')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
