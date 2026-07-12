"""The need statement — Demiurge's intake for a prospective Archon.

Minting is a judgment, not a reflex: a need must argue why the recurring task
has *earned* a persistent, curated Archon instead of a throwaway subagent
(``why_persistent``). That justification is required at the model level —
Demiurge refuses to mint without it. See ``docs/why-demiurge.md``, kill
criterion 1.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from demiurge.spec.model import Budget

DEFAULT_MODEL = "claude-sonnet-5"
DEFAULT_PROVIDER = "anthropic"

_DEFAULT_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"query": {"type": "string", "description": "The task or question."}},
    "required": ["query"],
}
_DEFAULT_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"response": {"type": "string", "description": "The Archon's result."}},
    "required": ["response"],
}


class ToolGrant(BaseModel):
    """An MCP server the Archon may use, optionally narrowed to specific tools."""

    model_config = ConfigDict(extra="forbid")

    alias: str = Field(pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    server_ref: str | None = None
    description: str | None = None
    allowed_tools: list[str] | None = None
    approval: bool = False


class LocalToolGrant(BaseModel):
    """A runtime-builtin tool the Archon may use (Agent Format ``local_tools``).

    ``name`` is the runtime's identifier for the tool — on the claude-cli
    runtime, a Claude Code tool name or specifier (e.g. ``Bash``,
    ``WebSearch``, ``Bash(python *)``). Defaults to the alias.
    """

    model_config = ConfigDict(extra="forbid")

    alias: str = Field(pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    name: str | None = None
    description: str | None = None
    approval: bool = False


class NeedStatement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_\-]*$")
    title: str = Field(min_length=1)
    task: str = Field(description="The recurring task this Archon exists to handle.")
    why_persistent: str = Field(
        description="Why this task has earned a persistent Archon over a throwaway subagent."
    )
    capabilities: list[str] = Field(min_length=1)
    tool_grants: list[ToolGrant] = Field(default_factory=list)
    local_tools: list[LocalToolGrant] = Field(default_factory=list)
    model: str = DEFAULT_MODEL
    provider: str = DEFAULT_PROVIDER
    max_steps: int = Field(default=10, ge=1)
    budget: Budget | None = None
    input_schema: dict[str, Any] = Field(default_factory=lambda: dict(_DEFAULT_INPUT_SCHEMA))
    output_schema: dict[str, Any] = Field(default_factory=lambda: dict(_DEFAULT_OUTPUT_SCHEMA))

    @field_validator("task", "why_persistent")
    @classmethod
    def _must_have_substance(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty — an unjustified need does not get minted")
        return value.strip()


def load_need(path: Path | str) -> NeedStatement:
    """Load a need statement from a YAML file."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: expected a YAML mapping describing the need")
    return NeedStatement.model_validate(raw)
