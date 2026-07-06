"""The demiurge command-line interface.

demiurge mint <need.yaml> [--stable-dir DIR]   mint an Archon from a need statement
demiurge validate <file.agf.yaml>              validate any Agent Format document
"""

import argparse
import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

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

    args = parser.parse_args(argv)
    if args.command == "mint":
        return _cmd_mint(args.need, args.stable_dir)
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
