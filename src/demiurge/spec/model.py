"""Typed model of the Agent Format v1.0 documents Demiurge emits.

Mirrors https://agentformat.org/schema/1.0/agentformat-schema.json (vendored in
``schemas/agentformat-1.0.json``). Demiurge models the subset it emits — every
document is still validated against the full vendored schema before it is
written (see ``demiurge.spec.validate``), so the schema, not this module, is
the final authority.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

AGENTFORMAT_SCHEMA_VERSION = "1.0.0"

_ID_PATTERN = r"^[a-z0-9][a-z0-9_\-]*$"
_ALIAS_PATTERN = r"^[a-zA-Z_][a-zA-Z0-9_]*$"


class _SpecModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Metadata(_SpecModel):
    id: str = Field(pattern=_ID_PATTERN)
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    authors: list[str] | None = None
    license: str | None = None
    labels: dict[str, str] | None = None
    annotations: dict[str, str] | None = None
    namespace: str | None = None


class Interface(_SpecModel):
    """Input/output contracts, each an arbitrary JSON Schema."""

    input: dict[str, Any]
    output: dict[str, Any]


class Budget(_SpecModel):
    max_token_usage: int | None = Field(default=None, ge=0)
    max_duration_seconds: int | None = Field(default=None, ge=1)


class Limits(_SpecModel):
    max_llm_calls: int | None = Field(default=None, ge=0)
    max_tool_calls: int | None = Field(default=None, ge=0)
    max_delegation_depth: int | None = Field(default=None, ge=0)


class Constraints(_SpecModel):
    tighten_only_invariant: bool = True
    budget: Budget | None = None
    limits: Limits | None = None


class LocalTool(_SpecModel):
    alias: str = Field(pattern=_ALIAS_PATTERN)
    name: str | None = None
    description: str | None = None
    approval: bool | dict[str, Any] | None = None


class McpServer(_SpecModel):
    alias: str = Field(pattern=_ALIAS_PATTERN)
    server_ref: str | None = None
    description: str | None = None
    allowed_tools: list[str | dict[str, Any]] | None = None
    approval: bool | dict[str, Any] | None = None


class ActionSpace(_SpecModel):
    local_tools: list[LocalTool] | None = None
    mcp_servers: list[McpServer] | None = None


class ExecutionPolicy(_SpecModel):
    id: str = Field(min_length=1)
    config: dict[str, Any]


class ArchonSpec(_SpecModel):
    """A complete ``.agf.yaml`` document, in emission order."""

    schema_version: str = AGENTFORMAT_SCHEMA_VERSION
    metadata: Metadata
    interface: Interface
    constraints: Constraints | None = None
    action_space: ActionSpace | None = None
    execution_policy: ExecutionPolicy

    def to_document(self) -> dict[str, Any]:
        """Plain-dict form of the document, with unset optionals omitted."""
        return self.model_dump(exclude_none=True)


def react_policy(
    instructions: str,
    model: str,
    *,
    provider: str | None = None,
    max_steps: int = 10,
    tool_choice: str = "auto",
    temperature: float | None = None,
) -> ExecutionPolicy:
    """Build a standard ``agf.react`` execution policy."""
    config: dict[str, Any] = {
        "instructions": instructions,
        "model": model,
        "max_steps": max_steps,
        "tool_choice": tool_choice,
    }
    if provider is not None:
        config["provider"] = provider
    if temperature is not None:
        config["temperature"] = temperature
    return ExecutionPolicy(id="agf.react", config=config)
