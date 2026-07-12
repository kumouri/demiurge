# ADR 0006 — A second adapter targets the Claude Code CLI (subscription-billed)

- **Status:** Accepted (2026-07-12)

## Context

ADR 0003 fixed the runtime-agnostic adapter model and shipped exactly one reference adapter,
resisting a second "until after the bootstrap demo" — that demo has since landed (Archon Zero
minted, admitted 3/3, and delegating). ADR 0005's reference adapter runs Archons on the Claude
Agent SDK, which authenticates only with a metered API key (`ANTHROPIC_API_KEY`, scoped via
`ANTHROPIC_API_KEY_DEMIURGE`).

A real operator profile has emerged that the SDK adapter cannot serve: local-first assistants
(e.g. Margo, the chief-of-staff skill suite that now drives Demiurge to mint her specialized
staff) run everything on the **Claude Code CLI**, billed against a Claude *subscription*, and
deliberately scrub `ANTHROPIC_API_KEY` from every child environment so nothing silently
switches to metered API spend. For that operator, deploying an SDK-billed Archon is the wrong
cost model — the same reason Margo's own SDK-based runner was frozen.

## Decision

Add a second adapter, **`claude-cli`**, alongside `claude-sdk` (which remains the default and
the reference). Same minted spec, same scaffold shape — a standalone uv project whose generic
`server.py` serves the copied `.agf.yaml` over A2A — but the executor shells out to the
`claude` CLI (`claude -p`, one shot per delegated task) instead of importing the SDK:

- **Auth/billing:** the operator's logged-in `claude` account, or a `CLAUDE_CODE_OAUTH_TOKEN`
  minted with `claude setup-token` for unattended service. Both `deploy` and every CLI
  invocation **scrub `ANTHROPIC_API_KEY`** from the child environment — the deliberate
  inversion of claude-sdk's key passthrough.
- **Tool grants:** MCP grants keep the identical runtime-owner contract (`mcp-servers.json`
  next to the scaffold), rendered into the CLI's `--mcp-config` shape and pinned with
  `--strict-mcp-config`; spec `allowed_tools` become `--allowedTools` entries. The spec's
  `action_space.local_tools` maps onto the CLI's built-in tools (a grant's `name` is a Claude
  Code tool name or specifier, e.g. `Bash`, `WebSearch`); to let need statements declare them,
  `NeedStatement` gains an optional `local_tools` list that mint maps straight onto the
  standard Agent Format field.
- **Budgets:** the CLI exposes no turn cap, so `max_steps` is advisory (appended to the system
  prompt); the spec's `constraints.budget.max_duration_seconds` is the hard rail, enforced as
  a subprocess timeout.

## Consequences

- Operators choose the cost model per deployment: `--adapter claude-cli` for
  subscription-billed local Archons, `--adapter claude-sdk` (default) for API-billed ones —
  the same minted spec runs on either, which is ADR 0003's swap working as designed.
- The scaffold gains a non-Python prerequisite: the `claude` binary on PATH (or
  `CLAUDE_CLI_BIN`). The server still boots and serves its agent card without it, so
  health-checking and admission plumbing stay token-free and CLI-free.
- Subscription billing means Archon spend shares the operator's plan limits and cannot be
  isolated on a separate key; heavy stables belong on `claude-sdk`.
- One-shot `claude -p` per delegation means no session continuity between tasks — acceptable
  for charter-scoped Archons, and identical to how the SDK adapter's `query()` behaves today.
- `local_tools` grants widen an Archon's action surface to the CLI's built-ins (notably
  `Bash`); charters and need statements must treat such grants as consciously as MCP grants —
  scoped specifiers (`Bash(python *)`) are supported and preferred.
