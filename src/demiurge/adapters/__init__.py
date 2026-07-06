"""Runtime adapters: a validated spec in, a running A2A-addressable Archon out (ADR 0003)."""

from demiurge.adapters.base import DeployError, Deployment, RuntimeAdapter, ScaffoldResult
from demiurge.adapters.claude_sdk import ClaudeAgentSdkAdapter

_ADAPTERS: dict[str, type] = {
    ClaudeAgentSdkAdapter.name: ClaudeAgentSdkAdapter,
}


def get_adapter(name: str) -> RuntimeAdapter:
    """Instantiate a registered adapter by name."""
    try:
        return _ADAPTERS[name]()
    except KeyError:
        available = ", ".join(sorted(_ADAPTERS))
        raise ValueError(f"unknown adapter '{name}' (available: {available})") from None


__all__ = [
    "ClaudeAgentSdkAdapter",
    "DeployError",
    "Deployment",
    "RuntimeAdapter",
    "ScaffoldResult",
    "get_adapter",
]
