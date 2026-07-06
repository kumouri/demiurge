"""The Archon lifecycle record (``record.json``): status plus an append-only history.

Statuses: ``specced`` (minted, not yet gated) → ``admitted`` (passed its eval
suite) → ``retired`` (curation ended its tenure). A revision returns an Archon
to ``specced`` until it re-passes admission — including any failure-derived
eval cases its predecessor earned.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RECORD_FILENAME = "record.json"

VALID_STATUSES = ("specced", "admitted", "retired")


def load_record(archon_dir: Path | str) -> dict[str, Any]:
    record_path = Path(archon_dir) / RECORD_FILENAME
    if not record_path.is_file():
        raise FileNotFoundError(f"no {RECORD_FILENAME} in {archon_dir} — mint the Archon first")
    return json.loads(record_path.read_text(encoding="utf-8"))


def save_record(archon_dir: Path | str, record: dict[str, Any]) -> None:
    record_path = Path(archon_dir) / RECORD_FILENAME
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def append_history(archon_dir: Path | str, event: str, detail: str) -> dict[str, Any]:
    """Add a history entry without changing status; returns the record."""
    record = load_record(archon_dir)
    record.setdefault("history", []).append(
        {
            "at": datetime.now(UTC).isoformat(timespec="seconds"),
            "event": event,
            "detail": detail,
        }
    )
    save_record(archon_dir, record)
    return record


def set_status(archon_dir: Path | str, status: str, event: str, detail: str) -> dict[str, Any]:
    """Transition the Archon's status, recording why; returns the record."""
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid status '{status}' (valid: {', '.join(VALID_STATUSES)})")
    record = load_record(archon_dir)
    record["status"] = status
    record.setdefault("history", []).append(
        {
            "at": datetime.now(UTC).isoformat(timespec="seconds"),
            "event": event,
            "detail": detail,
        }
    )
    save_record(archon_dir, record)
    return record
