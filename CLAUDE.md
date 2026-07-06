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
(need statement → spec + charter + evals seed + lifecycle record under `stable/<id>/`), and
`demiurge.cli` (`uv run demiurge mint <need.yaml>` / `demiurge validate <file.agf.yaml>`; example
need in `examples/`).

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
