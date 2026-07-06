# ADR 0005 — The v1 reference adapter targets the Claude Agent SDK

- **Status:** Accepted (2026-07-06)

## Context

ADR 0003 fixed the adapter model (runtime-agnostic interface, exactly one reference adapter in
v1) and deliberately deferred the reference runtime until the spec pipeline existed. It now
does: minted Archons are Agent Format `.agf.yaml` documents with `agf.react` execution
policies and `mcp_servers` tool grants.

## Decision

The reference adapter scaffolds Archons onto the **Claude Agent SDK** (Python
`claude-agent-sdk`), wrapped in an **a2a-sdk** server: the scaffold is a standalone uv project
whose generic `server.py` loads the copied `.agf.yaml` and serves it — agent card at the A2A
well-known path, delegation over A2A JSON-RPC, the `agf.react` policy executed via
`claude_agent_sdk.query()`.

## Consequences

- The spec's `mcp_servers` grants map naturally onto the SDK's native MCP support. In v1 the
  mapping of portable `server_ref` identities to real connection details remains the runtime
  owner's job (exactly as the Agent Format spec assigns it) — documented in each scaffold's
  README rather than auto-wired.
- The scaffold holds **no per-Archon logic**: the spec is the configuration, the server is
  generic. Swapping runtimes (ADR 0003) means swapping the template, not the minted spec.
- Demo runs are API-billed via the operator's own Anthropic auth; the SDK bundles its CLI, so
  a scaffold needs only `uv run python server.py`.
- The server boots and serves its agent card without any LLM auth — health-checking and
  admission plumbing don't burn tokens.
