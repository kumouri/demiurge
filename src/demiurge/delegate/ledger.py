"""The task ledger: an append-only record of every delegation, per Archon.

One JSONL file per Archon (``stable/<id>/ledger.jsonl``). This is the raw
material of curation: outcome-based tenure (Phase 3) reads these entries, and
field failures recorded here get distilled into new eval cases.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from demiurge.delegate.client import DelegationResult

LEDGER_FILENAME = "ledger.jsonl"


def record_delegation(
    archon_dir: Path | str,
    request_text: str,
    result: DelegationResult,
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
    with (archon_dir / LEDGER_FILENAME).open("a", encoding="utf-8") as ledger:
        ledger.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def is_delegation(entry: dict[str, Any]) -> bool:
    """True for delegation entries (verdicts and future entry types carry a ``type``)."""
    return entry.get("type", "delegation") == "delegation"


def read_ledger(archon_dir: Path | str) -> list[dict[str, Any]]:
    """All ledger entries for an Archon, oldest first."""
    ledger_path = Path(archon_dir) / LEDGER_FILENAME
    if not ledger_path.is_file():
        return []
    return [
        json.loads(line)
        for line in ledger_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
