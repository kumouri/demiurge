"""The demiurge command-line interface.

demiurge mint <need.yaml> [--stable-dir DIR]   mint an Archon from a need statement
demiurge validate <file.agf.yaml>              validate any Agent Format document
demiurge scaffold <archon-id>                  generate a runnable project for an Archon
demiurge deploy <archon-id> [--port N]         scaffold (if needed) and serve over A2A
"""

import argparse
import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from demiurge.adapters import DeployError, get_adapter
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

    args = parser.parse_args(argv)
    if args.command == "mint":
        return _cmd_mint(args.need, args.stable_dir)
    if args.command == "scaffold":
        return _cmd_scaffold(args)
    if args.command == "deploy":
        return _cmd_deploy(args)
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
