import pytest

from demiurge.delegate import DelegationError, delegate, read_ledger, record_delegation


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
