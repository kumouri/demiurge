"""Failure distillation and revision — the rule that fuses the loop.

Every field failure becomes an eval case (``origin: field-failure``) built
from the exact request that failed. A revision regenerates the spec, charter,
and mint-origin eval cases from the updated need, but **keeps every
failure-derived case**: the successor must pass the very case its predecessor
failed, and it re-enters the stable only through the admission gate.
"""

from pathlib import Path

import yaml

from demiurge.curate.evals import EvalCase, load_evals, save_evals
from demiurge.curate.record import append_history, load_record, save_record, set_status
from demiurge.delegate.ledger import is_delegation, read_ledger
from demiurge.mint.need import NeedStatement
from demiurge.mint.pipeline import (
    CHARTER_FILENAME,
    SPEC_FILENAME,
    MintResult,
    build_charter,
    build_spec,
    seed_evals,
)
from demiurge.spec.emit import to_yaml
from demiurge.spec.validate import assert_valid

FIELD_FAILURE_PREFIX = "field-failure-"


def distill_failure(
    archon_dir: Path | str,
    task_id: str,
    note: str,
    *,
    expect_contains: list[str] | None = None,
) -> EvalCase:
    """Turn a failed delegation into a regression eval case the successor must pass."""
    archon_dir = Path(archon_dir)
    delegation = next(
        (
            entry
            for entry in read_ledger(archon_dir)
            if is_delegation(entry) and entry.get("task_id") == task_id
        ),
        None,
    )
    if delegation is None:
        raise ValueError(f"no delegation with task_id '{task_id}' in the ledger")

    suite = load_evals(archon_dir)
    next_index = (
        max(
            (
                int(case.id.removeprefix(FIELD_FAILURE_PREFIX))
                for case in suite.cases
                if case.id.startswith(FIELD_FAILURE_PREFIX)
                and case.id.removeprefix(FIELD_FAILURE_PREFIX).isdigit()
            ),
            default=0,
        )
        + 1
    )
    case = EvalCase(
        id=f"{FIELD_FAILURE_PREFIX}{next_index}",
        origin="field-failure",
        description=note,
        input={"query": delegation["request"]},
        expect=note,
        expect_contains=list(expect_contains or []),
    )
    suite.cases.append(case)
    save_evals(archon_dir, suite)
    append_history(
        archon_dir,
        "failure-distilled",
        f"task {task_id} -> eval case {case.id}: {note}",
    )
    return case


def revise(need: NeedStatement, stable_dir: Path | str) -> MintResult:
    """Re-mint an existing Archon from an updated need, preserving its earned history."""
    archon_dir = Path(stable_dir) / need.id
    if not archon_dir.is_dir():
        raise FileNotFoundError(f"no archon '{need.id}' in {stable_dir} — nothing to revise")

    new_version = _bump_minor(_spec_version(archon_dir))

    spec = build_spec(need, version=new_version)
    document = spec.to_document()
    assert_valid(document)

    # Regenerate mint-origin cases from the new need; keep every earned failure case.
    suite = load_evals(archon_dir)
    field_failure_cases = [case for case in suite.cases if case.origin == "field-failure"]
    reseeded = [EvalCase.model_validate(case) for case in seed_evals(need)["cases"]]
    suite.cases = reseeded + field_failure_cases
    result = MintResult(archon_id=need.id, archon_dir=archon_dir, spec=spec)
    (archon_dir / SPEC_FILENAME).write_text(to_yaml(spec), encoding="utf-8")
    (archon_dir / CHARTER_FILENAME).write_text(build_charter(need), encoding="utf-8")
    save_evals(archon_dir, suite)

    record = load_record(archon_dir)
    record["need"] = need.model_dump(exclude_none=True)
    save_record(archon_dir, record)
    set_status(
        archon_dir,
        "specced",
        "revised",
        f"revised to v{new_version} ({len(field_failure_cases)} failure-derived eval case(s) "
        "retained); must re-pass admission",
    )
    return result


def _spec_version(archon_dir: Path) -> str:
    spec = yaml.safe_load((archon_dir / SPEC_FILENAME).read_text(encoding="utf-8"))
    return str(spec["metadata"]["version"])


def _bump_minor(version: str) -> str:
    parts = version.split(".")
    if len(parts) < 2 or not parts[1].isdigit():
        return f"{version}.post1"
    parts = parts[:3] + ["0"] * (3 - len(parts))
    return f"{parts[0]}.{int(parts[1]) + 1}.0"
