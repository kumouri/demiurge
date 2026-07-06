"""Delegation: hand a task to a running Archon over A2A and record what came back."""

from demiurge.delegate.client import DelegationError, DelegationResult, delegate, delegate_async
from demiurge.delegate.ledger import LEDGER_FILENAME, read_ledger, record_delegation

__all__ = [
    "LEDGER_FILENAME",
    "DelegationError",
    "DelegationResult",
    "delegate",
    "delegate_async",
    "read_ledger",
    "record_delegation",
]
