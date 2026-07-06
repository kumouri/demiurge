"""Mint: turn a justified need into a specced Archon on disk.

Output layout, one directory per Archon under the stable:

    stable/<archon-id>/
      archon.agf.yaml   the Agent Format spec (standard; validated before write)
      charter.md        what this Archon is for and what is out of its scope
      evals.yaml        the eval suite seed (admission gate input, Phase 3)
      record.json       lifecycle record (status: specced -> admitted -> retired)

The charter and evals travel *alongside* the .agf.yaml, never inside it —
Demiurge emits standard Agent Format documents only (ADR 0004).
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from demiurge.mint.need import NeedStatement
from demiurge.spec.emit import to_yaml
from demiurge.spec.model import (
    ActionSpace,
    ArchonSpec,
    Constraints,
    Interface,
    McpServer,
    Metadata,
    react_policy,
)
from demiurge.spec.validate import assert_valid

SPEC_FILENAME = "archon.agf.yaml"
CHARTER_FILENAME = "charter.md"
EVALS_FILENAME = "evals.yaml"
RECORD_FILENAME = "record.json"


class MintError(RuntimeError):
    """Minting failed; nothing was written."""


@dataclass(frozen=True)
class MintResult:
    archon_id: str
    archon_dir: Path
    spec: ArchonSpec

    @property
    def spec_path(self) -> Path:
        return self.archon_dir / SPEC_FILENAME

    @property
    def charter_path(self) -> Path:
        return self.archon_dir / CHARTER_FILENAME

    @property
    def evals_path(self) -> Path:
        return self.archon_dir / EVALS_FILENAME

    @property
    def record_path(self) -> Path:
        return self.archon_dir / RECORD_FILENAME


def build_spec(need: NeedStatement) -> ArchonSpec:
    """Assemble the Agent Format document for a need (pure; no I/O)."""
    instructions = _compose_instructions(need)
    action_space = None
    if need.tool_grants:
        action_space = ActionSpace(
            mcp_servers=[
                McpServer(
                    alias=grant.alias,
                    server_ref=grant.server_ref,
                    description=grant.description,
                    allowed_tools=list(grant.allowed_tools) if grant.allowed_tools else None,
                    approval=grant.approval or None,
                )
                for grant in need.tool_grants
            ]
        )
    return ArchonSpec(
        metadata=Metadata(
            id=need.id,
            name=need.title,
            version="0.1.0",
            description=need.task,
            labels={"minted_by": "demiurge", "lifecycle": "specced"},
        ),
        interface=Interface(input=need.input_schema, output=need.output_schema),
        constraints=Constraints(budget=need.budget) if need.budget else None,
        action_space=action_space,
        execution_policy=react_policy(
            instructions,
            need.model,
            provider=need.provider,
            max_steps=need.max_steps,
        ),
    )


def build_charter(need: NeedStatement) -> str:
    """Render the Archon's charter — fixed at mint time, the scope authority."""
    capabilities = "\n".join(f"- {capability}" for capability in need.capabilities)
    tools = (
        "\n".join(
            f"- `{grant.alias}`"
            + (f" — {grant.description}" if grant.description else "")
            + (f" (tools: {', '.join(grant.allowed_tools)})" if grant.allowed_tools else "")
            for grant in need.tool_grants
        )
        or "- none — this Archon works from its instructions alone"
    )
    return f"""# Charter — {need.title} (`{need.id}`)

*Fixed at mint time. This charter, not the conversation that produced it, is the scope
authority: work outside it is out of scope even if the Archon could do it.*

## Task

{need.task}

## Why a persistent Archon

{need.why_persistent}

## Capabilities

{capabilities}

## Tool grants

{tools}

## Tenure

Admission to the stable requires passing `evals.yaml`. Tenure is outcome-based: delegated-task
results decide keep / revise / retire, and every field failure is distilled into a new eval
case that any successor must pass.
"""


def seed_evals(need: NeedStatement) -> dict[str, Any]:
    """Seed the eval suite: one smoke case plus one case per declared capability.

    Every case carries an ``origin``; cases distilled from field failures
    (Phase 3) use ``origin: field-failure`` and accumulate alongside these.
    """
    cases: list[dict[str, Any]] = [
        {
            "id": "smoke-responds",
            "origin": "mint",
            "description": "Produces a non-empty, on-task response to a basic request.",
            "input": {"query": f"Briefly: what do you do? Task context: {need.task}"},
            "expect": "A non-empty response consistent with the charter's task.",
        }
    ]
    for index, capability in enumerate(need.capabilities, start=1):
        cases.append(
            {
                "id": f"capability-{index}",
                "origin": "mint",
                "description": f"Demonstrates: {capability}",
                "input": {
                    "query": f"Demonstrate, on a representative example: {capability}",
                },
                "expect": f"Evidence of the capability: {capability}",
            }
        )
    return {"archon": need.id, "schema": "demiurge-evals/v1", "cases": cases}


def mint(need: NeedStatement, stable_dir: Path | str) -> MintResult:
    """Mint an Archon: validate the spec, then write the archon directory.

    Refuses to overwrite an existing Archon — re-minting is a curation
    decision (Phase 3), not an accident.
    """
    archon_dir = Path(stable_dir) / need.id
    if archon_dir.exists():
        raise MintError(
            f"archon '{need.id}' already exists at {archon_dir} — "
            "revision and re-minting belong to curation, not mint"
        )

    spec = build_spec(need)
    document = spec.to_document()
    assert_valid(document)  # never write an invalid spec

    result = MintResult(archon_id=need.id, archon_dir=archon_dir, spec=spec)
    archon_dir.mkdir(parents=True)
    result.spec_path.write_text(to_yaml(spec), encoding="utf-8")
    result.charter_path.write_text(build_charter(need), encoding="utf-8")
    result.evals_path.write_text(
        yaml.safe_dump(seed_evals(need), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    record = {
        "archon_id": need.id,
        "status": "specced",
        "minted_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "spec_file": SPEC_FILENAME,
        "need": need.model_dump(exclude_none=True),
        "history": [],
    }
    result.record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return result


def _compose_instructions(need: NeedStatement) -> str:
    capabilities = "\n".join(f"- {capability}" for capability in need.capabilities)
    return f"""You are {need.title}, a specialized Archon agent minted by Demiurge.

Your task:
{need.task}

Your capabilities:
{capabilities}

Operating rules:
- Stay inside your charter: do the task above and nothing else, even if asked.
- Use only the tools you have been granted.
- If a request falls outside your charter, say so and stop rather than improvising.
- Be concise and factual; your outputs are recorded and evaluated.
"""
