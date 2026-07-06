"""Outcome-based tenure: verdicts on delegated work, and what they add up to.

Transport state says a task *finished*; only a verdict says it was *right*.
Verdicts are appended to the same per-Archon ledger as delegations
(``type: verdict``) and override the transport heuristic for their task.
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from demiurge.curate.record import set_status
from demiurge.delegate.ledger import LEDGER_FILENAME, is_delegation, read_ledger

VERDICT_OUTCOMES = ("success", "failure")

# Tenure heuristics (v1, deliberately simple and documented):
# - fewer than MIN_SAMPLE delegations -> "keep" (not enough evidence)
# - failure rate >= RETIRE_RATE       -> "retire"
# - failure rate >= REVISE_RATE       -> "revise"
MIN_SAMPLE = 3
REVISE_RATE = 0.3
RETIRE_RATE = 0.8


def record_verdict(
    archon_dir: Path | str,
    task_id: str,
    outcome: str,
    note: str = "",
) -> dict[str, Any]:
    """Record a human/caller judgment on a delegated task."""
    if outcome not in VERDICT_OUTCOMES:
        raise ValueError(f"invalid outcome '{outcome}' (valid: {', '.join(VERDICT_OUTCOMES)})")
    archon_dir = Path(archon_dir)
    delegations = [entry for entry in read_ledger(archon_dir) if is_delegation(entry)]
    if not any(entry.get("task_id") == task_id for entry in delegations):
        raise ValueError(f"no delegation with task_id '{task_id}' in the ledger")
    entry = {
        "type": "verdict",
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "task_id": task_id,
        "outcome": outcome,
        "note": note,
    }
    with (archon_dir / LEDGER_FILENAME).open("a", encoding="utf-8") as ledger:
        ledger.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


@dataclass(frozen=True)
class TenureReport:
    archon_id: str
    delegations: int
    failures: int
    failure_rate: float
    recommendation: str  # "keep" | "revise" | "retire"
    reasons: list[str]


def tenure_review(archon_dir: Path | str, *, window: int = 20) -> TenureReport:
    """Summarize the last ``window`` delegations into a tenure recommendation."""
    archon_dir = Path(archon_dir)
    entries = read_ledger(archon_dir)
    verdicts = {
        entry["task_id"]: entry["outcome"]
        for entry in entries
        if entry.get("type") == "verdict" and entry.get("task_id")
    }
    delegations = [entry for entry in entries if is_delegation(entry)][-window:]

    failures = sum(1 for entry in delegations if _failed(entry, verdicts))
    total = len(delegations)
    rate = (failures / total) if total else 0.0

    reasons = [f"{failures}/{total} recent delegations judged failed"]
    if total < MIN_SAMPLE:
        recommendation = "keep"
        reasons.append(f"fewer than {MIN_SAMPLE} delegations — not enough evidence to act")
    elif rate >= RETIRE_RATE:
        recommendation = "retire"
        reasons.append(f"failure rate {rate:.0%} >= {RETIRE_RATE:.0%}")
    elif rate >= REVISE_RATE:
        recommendation = "revise"
        reasons.append(f"failure rate {rate:.0%} >= {REVISE_RATE:.0%}")
    else:
        recommendation = "keep"
        reasons.append(f"failure rate {rate:.0%} below the revise threshold")
    return TenureReport(
        archon_id=archon_dir.name,
        delegations=total,
        failures=failures,
        failure_rate=round(rate, 3),
        recommendation=recommendation,
        reasons=reasons,
    )


def retire(archon_dir: Path | str, reason: str) -> dict[str, Any]:
    """End an Archon's tenure. The directory, ledger, and evals remain as the record."""
    return set_status(archon_dir, "retired", "retired", reason)


def _failed(entry: dict[str, Any], verdicts: dict[str, str]) -> bool:
    task_id = entry.get("task_id")
    if task_id and task_id in verdicts:
        return verdicts[task_id] == "failure"
    if entry.get("state") != "TASK_STATE_COMPLETED":
        return True
    response = entry.get("response") or ""
    return not response.strip() or response.startswith("Archon runtime error:")
