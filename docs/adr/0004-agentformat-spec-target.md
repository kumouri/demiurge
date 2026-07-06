# ADR 0004 — Archon specs target Agent Format (agentformat.org)

- **Status:** Accepted (2026-07-06)

## Context

Demiurge mints agent *specs* but by charter invents no format. It needs an existing, open,
runtime-neutral standard for minted Archon definitions.

## Decision

Minted Archon definitions are **Agent Format** documents — the open standard at
<https://agentformat.org/> (v1.0): declarative `.agf.yaml` files with `schema_version`,
`metadata`, `interface`, `execution_policy`, and an `action_space` for tool declarations,
validated against the published JSON Schema
(<https://agentformat.org/schema/1.0/agentformat-schema.json>).

Demiurge-specific artifacts that the standard does not cover — the Archon's **charter** and its
**eval criteria / suite** — travel *alongside* the `.agf.yaml` as sibling documents, never as
nonstandard extensions inside it.

## Consequences

- "The same `.agf.yaml` runs on any compliant runtime" aligns exactly with ADR 0003's adapter
  model: adapters consume standard Agent Format specs.
- Validation is mechanical (JSON Schema), which the mint pipeline and CI can both enforce.
- Agent Format is young; if the standard moves, the pinned `schema_version` and thin adapters
  (ADR 0003) contain the blast radius. The A2A Agent Card remains the Archon's *wire-level*
  discovery document at delegation time — Agent Format is the *authoring/spec* layer; they
  coexist rather than compete.
