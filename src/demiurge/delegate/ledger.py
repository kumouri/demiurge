"""The task ledger: an append-only record of every delegation, per Archon.

One JSONL file per Archon, ``stable/<id>/ledger.jsonl`` by default. This is the
raw material of curation: outcome-based tenure (Phase 3) reads these entries, and
field failures recorded here get distilled into new eval cases.

**The ledger is the one part of the stable that churns.** Everything else there —
spec, charter, evals, record — is written once at mint/revise time, which makes
``stable/`` a natural fit for version control. The ledger appends on every single
delegation, and it stores the full request and response text. An operator who
tracks their stable in git therefore gets two problems the rest of the stable
doesn't have: a permanently-dirty working tree (which can block a
``pull --ff-only``), and whatever the delegation text happened to contain landing
in git history forever.

So the ledger's location is decoupled from the archon's identity: pass
``ledger_dir`` (CLI: ``--ledger-dir``) to keep it with the archon's other runtime
state instead. Defaults to ``archon_dir``, so callers that don't care are
unaffected.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from demiurge.delegate.client import DelegationResult

LEDGER_FILENAME = "ledger.jsonl"


def ledger_path(archon_dir: Path | str, ledger_dir: Path | str | None = None) -> Path:
    """Where this Archon's ledger lives — ``ledger_dir`` if given, else beside its stable data.

    Separating this from ``archon_dir`` is the whole point: ``archon_dir`` answers *which Archon*,
    ``ledger_dir`` answers *where its churn goes*. They were the same path until the ledger's growth
    made that a problem for git-tracked stables.
    """
    return Path(ledger_dir) / LEDGER_FILENAME if ledger_dir else Path(archon_dir) / LEDGER_FILENAME


def record_delegation(
    archon_dir: Path | str,
    request_text: str,
    result: DelegationResult,
    ledger_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Append one delegation to the Archon's ledger and return the entry."""
    archon_dir = Path(archon_dir)
    if not archon_dir.is_dir():
        raise FileNotFoundError(f"no archon directory at {archon_dir}")
    entry = {
        "delegated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "request": request_text,
        "response": result.text,
        "state": result.state,
        "task_id": result.task_id,
        "duration_seconds": result.duration_seconds,
    }
    path = ledger_path(archon_dir, ledger_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as ledger:
        ledger.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def is_delegation(entry: dict[str, Any]) -> bool:
    """True for delegation entries (verdicts and future entry types carry a ``type``)."""
    return entry.get("type", "delegation") == "delegation"


def read_ledger(
    archon_dir: Path | str,
    ledger_dir: Path | str | None = None,
) -> list[dict[str, Any]]:
    """All ledger entries for an Archon, oldest first."""
    path = ledger_path(archon_dir, ledger_dir)
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
