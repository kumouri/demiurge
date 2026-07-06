# ADR 0002 — Implementation stack: Python 3.12+ with uv

- **Status:** Accepted (2026-07-06)

## Context

Demiurge needs a stack for the orchestrator itself (minting, delegation, curation). The
candidates were Python and TypeScript. Demiurge's charter has it riding A2A for delegation and
generating eval suites for curation.

## Decision

Python (>= 3.12), managed with **uv**; **ruff** for lint/format, **pytest** for tests,
hatchling as the build backend, `src/` layout.

## Consequences

- The A2A reference SDK (`a2a-sdk`) and the bulk of the agent/eval ecosystem are
  Python-first — the shortest path to the full v1 loop.
- uv gives fast, reproducible, lockfile-based environments; contributors need only
  `uv sync && uv run pytest`.
- TypeScript remains viable for future satellite tooling (e.g. a web UI), but the core loop is
  Python by decision, not drift.
