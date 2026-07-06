# ADR 0003 — Archons target runtimes through adapters

- **Status:** Accepted (2026-07-06)

## Context

Minting ends in a deployed, A2A-addressable Archon, so the scaffold generator must produce
something that *runs*. Options were to hard-target one runtime (e.g. the Claude Agent SDK) or
to define a runtime adapter interface from day one.

## Decision

Runtime-agnostic **adapter interface** from day one, with **one reference adapter** shipped in
v1. The adapter contract: given a validated Archon spec, produce a runnable, A2A-addressable
deployment; report health; support teardown.

## Consequences

- This is the purest reading of the charter ("Demiurge owns no runtime") — the spec, not the
  runtime, is the unit Demiurge reasons about.
- Costs more surface area before the loop closes; contained by shipping exactly one reference
  adapter in v1 and resisting a second until after the bootstrap demo.
- The reference adapter's target runtime is deliberately **not** fixed by this ADR; it is
  chosen in Phase 1 with its own ADR, once the spec pipeline exists to inform it.
