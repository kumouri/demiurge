import pytest

from demiurge.delegate import (
    DelegationError,
    delegate,
    ledger_path,
    read_ledger,
    record_delegation,
)


def test_delegate_round_trip_over_a2a(echo_endpoint):
    result = delegate(echo_endpoint, "ping", timeout=30)
    assert "echo: ping" in result.text
    assert result.completed, result.state
    assert result.duration_seconds >= 0


def test_delegation_is_recorded_in_the_ledger(tmp_path, echo_endpoint):
    archon_dir = tmp_path / "echo-archon"
    archon_dir.mkdir()
    result = delegate(echo_endpoint, "ledger me", timeout=30)
    entry = record_delegation(archon_dir, "ledger me", result)

    entries = read_ledger(archon_dir)
    assert entries == [entry]
    assert entries[0]["request"] == "ledger me"
    assert "echo: ledger me" in entries[0]["response"]
    assert entries[0]["state"] == "TASK_STATE_COMPLETED"


def test_ledger_of_unknown_archon_is_empty(tmp_path):
    assert read_ledger(tmp_path / "nope") == []


def test_unreachable_archon_raises_delegation_error():
    with pytest.raises(DelegationError, match="cannot reach archon"):
        delegate("http://127.0.0.1:9", "hello", timeout=2)


# --- ledger_dir: keeping append-per-delegation churn out of a tracked stable --------------------


def test_ledger_path_defaults_beside_the_stable_data(tmp_path):
    assert ledger_path(tmp_path / "echo") == tmp_path / "echo" / "ledger.jsonl"


def test_ledger_path_honours_an_override(tmp_path):
    assert ledger_path(tmp_path / "echo", tmp_path / "state") == tmp_path / "state" / "ledger.jsonl"


def test_delegation_records_into_ledger_dir_leaving_the_stable_clean(tmp_path, echo_endpoint):
    archon_dir = tmp_path / "echo-archon"
    archon_dir.mkdir()
    state_dir = tmp_path / "runtime-state"
    result = delegate(echo_endpoint, "ledger me", timeout=30)
    entry = record_delegation(archon_dir, "ledger me", result, ledger_dir=state_dir)

    # The whole point: nothing lands in the stable dir, so a tracked stable stays clean.
    assert not (archon_dir / "ledger.jsonl").exists()
    assert (state_dir / "ledger.jsonl").is_file()
    assert read_ledger(archon_dir, state_dir) == [entry]
    assert read_ledger(archon_dir) == []  # and the default read doesn't see it


def test_ledger_dir_is_created_if_absent(tmp_path, echo_endpoint):
    archon_dir = tmp_path / "echo-archon"
    archon_dir.mkdir()
    result = delegate(echo_endpoint, "ledger me", timeout=30)
    record_delegation(archon_dir, "x", result, ledger_dir=tmp_path / "nested" / "state")
    assert (tmp_path / "nested" / "state" / "ledger.jsonl").is_file()
