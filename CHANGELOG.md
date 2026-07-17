# Changelog

All notable changes to Demiurge are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/); versions follow semver.

> Entries are drafted by the **Changelog Scribe**, an Archon minted and
> curated by Demiurge itself, and reviewed before landing.

## [Unreleased]

### Features

- **`--ledger-dir`: decouple where an Archon's ledger lives from which Archon it is.** The ledger is
  the only part of the stable that churns — spec, charter, evals and record are written once at
  mint/revise time, while the ledger appends on every delegation and stores the full request and
  response text. Operators tracking their stable in git therefore hit two problems the rest of the
  stable never causes: a permanently-dirty working tree (which can abort a `pull --ff-only` and, in
  a deploy-on-merge setup, silently stop reloads), and whatever the delegation text contained landing
  in git history permanently. `demiurge delegate|verdict|distill|tenure --ledger-dir <path>` puts it
  with the Archon's runtime state instead. Defaults to the Archon's stable dir, so existing callers
  are unaffected. `archon_dir` still answers *which Archon* (tenure reports still take their id from
  it); `ledger_dir` answers *where its churn goes*.

## [0.1.0] - 2026-07-06

First release of Demiurge. This release delivers the full Archon lifecycle end-to-end — minting typed Agent Format specs, scaffolding and deploying them via the `claude-sdk` adapter, delegating work over A2A, and curating the stable through an eval-gated admission loop with tenure tracking and failure-driven revision. Archon Zero, the first Archon, is admitted into the stable as a self-referential proof of the loop.

### Features

- Typed Agent Format spec models with YAML emission, validated against a vendored schema.
- Need-statement-to-spec mint pipeline, exposed via `demiurge mint` and `demiurge validate`.
- Runtime adapter contract plus the `claude-sdk` reference adapter, exposed via `demiurge scaffold` and `demiurge deploy`.
- MCP `server_ref` grants wired into scaffolded Archons, with scoped API key passthrough.
- A2A delegation client and a per-Archon task ledger, exposed via `demiurge delegate`.
- The fused curation loop — admission gating, tenure heuristics, field-failure distillation into new eval cases, and version-bumped revision — exposed via `demiurge admit`, `verdict`, `distill`, `tenure`, `retire`, and `revise`.
- Optional Claude-judge admission mode that enforces natural-language eval criteria via the Claude API.
- Admitted Archon Zero, the first Archon into the stable.
- Initial Python package scaffold (uv, ruff, pytest, src layout).

### Fixes

- Delegation now reuses a single long-timeout httpx client for the A2A transport instead of creating one per request.

### Docs

- Refined the project goal and added the v1 plan.
- Recorded Phase-0 architecture decisions (license, stack, adapters, Agent Format) as ADRs.
- Added the CLAUDE.md operating guide, kept in sync as the adapter, delegate, curate, and MCP/judge layers landed.
- Added a "why Demiurge" decision note with honest kill criteria.
- Added the Archon Zero example need statement.

### CI

- Added the GitHub Actions workflow running `uv sync`, ruff, and pytest across Python 3.12–3.14.
- Pinned `setup-uv` to v8.3.0 after v5 targeted deprecated Node 20 and no floating v8 tag existed.

### Internal

- Added the Apache-2.0 license, runtime dependencies (pydantic, pyyaml, jsonschema), and the CLI entry point.
- Refactored shared test fixtures, ledger entry types, and the spec version parameter ahead of the curation work.
