# CLAUDE.md

Operating guide for Claude Code in the **demiurge** repo.

## What this is

Demiurge is a public, open-source **meta-agent** that owns the full Archon lifecycle: it
**mints** specialized agents (spec → scaffold → deploy), **delegates** work to them over
**A2A**, and **curates** the stable via a fused loop — eval-gated admission, outcome-based
tenure, and every field failure distilled into a new eval case. By charter it owns **no
runtime, no format, no protocol**: specs target **Agent Format** (agentformat.org), delegation
rides A2A, tools ride MCP. Read `README.md` for the loop and `PLAN.md` for the refined goal,
v1 definition of done, and phases. Decisions are recorded in `docs/adr/` — add a new numbered
ADR for any decision of that weight; never silently reverse one.

## Stack & commands

Python ≥ 3.12, managed with **uv** (`src/` layout, hatchling build backend). Core modules:
`demiurge.spec` (typed Agent Format models + YAML emission + validation against the **vendored**
schema in `src/demiurge/spec/schemas/` — re-vendor deliberately, never hand-edit), `demiurge.mint`
(need statement → spec + charter + evals seed + lifecycle record under `stable/<id>/`),
`demiurge.adapters` (runtime adapter contract + the `claude-sdk` reference adapter, ADR 0005 —
scaffolds a standalone uv project with a generic `server.py` serving the spec over A2A; the spec's
MCP `server_ref` grants map onto `ClaudeAgentOptions.mcp_servers` via a runtime-owner
`mcp-servers.json` (seeded as `mcp-servers.example.json`); deploy passes a set
`ANTHROPIC_API_KEY_DEMIURGE` through to the Archon as `ANTHROPIC_API_KEY`; templates live under
`adapters/templates/`), `demiurge.delegate` (A2A client + the append-only per-Archon
task ledger `stable/<id>/ledger.jsonl` that curation reads), `demiurge.curate` (the fused loop:
eval runner + admission gate with a pluggable judge — `BaselineJudge` is deterministic and treats
natural-language `expect` as advisory; `ClaudeJudge` (`demiurge admit --judge claude`) also
enforces `expect` via the Claude API with structured-output verdicts, failing closed on judge
errors — auth via `ANTHROPIC_API_KEY_DEMIURGE` (preferred) or SDK defaults, optional dep
`demiurge[judge]`; verdicts + tenure heuristics over the ledger;
`distill_failure` turns a failed task into an `origin: field-failure` eval case; `revise`
re-mints with a minor version bump, keeps every failure-derived case, and drops the Archon back
to `specced` until it re-passes the gate), and `demiurge.cli` (`mint` / `validate` / `scaffold` /
`deploy` / `delegate` / `admit` / `verdict` / `distill` / `tenure` / `retire` / `revise`; example
need in `examples/`). Generated `scaffolds/` and `deploy.log` are gitignored. Tests share a real
in-process a2a-sdk echo agent (`tests/conftest.py`).

- `uv sync` — create/refresh the environment (dev group included).
- `uv run pytest` — tests.
- `uv run ruff check .` / `uv run ruff format --check .` — lint / format gate.

CI (`.github/workflows/ci.yml`) runs exactly those three checks on Python 3.12–3.14 for every
push and PR — reproduce locally with the commands above before pushing.

## Conventions

- **Conventional Commits** with a scope (`feat:`, `docs(adr):`, `chore:`, `ci:`); atomic
  commits.
- Trunk-based on `main` (no Git Flow).
- **Markdown is canonical** for documents; rendered formats are build artifacts.
- v1 non-goals (see `PLAN.md`): no new runtime/format/protocol, no hosted service, no
  multi-tenancy. Resist scope creep toward them — especially while building the
  self-referential bootstrap demo (Archon Zero's charter is fixed at mint time).
