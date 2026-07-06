# Demiurge — Goal & v1 Plan

*Refined 2026-07-06. Markdown is the canonical source of this plan; anything rendered from it
is a build artifact.*

## The refined goal

> **Demiurge is a public, open-source meta-agent that owns the full Archon lifecycle:**
> it mints specialized agents (spec → scaffold → deploy), delegates real work to them over
> **A2A**, and curates the stable through a **fused loop** — eval-gated admission,
> outcome-based tenure, and every field failure distilled into a new eval case.
> It rides existing standards (agent formats, A2A, MCP) and owns nothing else.

Four decisions define v1:

| Decision | Call |
|---|---|
| **Audience** | Public / portfolio project — built in the open, docs and demos aimed at other builders. |
| **Mint depth** | Full lifecycle in v1: mint → deploy → delegate live, not spec-only. |
| **Curation** | The fused loop (below) — evals gate admission, outcomes decide tenure, failures author new evals. |
| **First proof** | Self-referential bootstrap: **Archon Zero** helps build Demiurge itself. |

### The fused curation loop

1. **Eval-gated admission.** Every minted Archon ships with a generated eval suite and must
   pass it to enter the stable. No exceptions — including Archon Zero.
2. **Outcome-based tenure.** Once admitted, delegated-task outcomes are the record that
   decides keep / revise / retire.
3. **Failure distillation.** Every field failure becomes a new eval case. The suite grows
   from reality, not imagination, and a revised or re-minted Archon must pass the exact case
   its predecessor failed. This rule is Demiurge's central claim: curation is one loop in
   which outcomes continuously author the evals.

## Non-goals (v1)

- No new runtime, agent format, or protocol — ever, by charter.
- No hosted service / SaaS surface; v1 runs locally.
- No multi-tenant stable, auth, or org features.
- No model-provider abstraction layer beyond what the chosen stack gives for free.

## v1 definition of done

A recorded, reproducible demo in which Demiurge:

1. takes a need statement and **mints Archon Zero** (spec → scaffold → deploy, A2A-addressable),
2. **gates** it into the stable via its generated eval suite,
3. **delegates** a real Demiurge-development task to it over A2A,
4. records a **field failure**, distills it into a new eval case, revises the Archon, and
   re-admits it **passing the failure-derived eval**,
5. and lands at least one Archon-Zero-produced change **merged into Demiurge itself**.

## Phases

### Phase 0 — Foundations & decisions

Deliverables: recorded decisions (lightweight ADRs) for **license** (proposal: Apache-2.0),
**implementation stack** (language + agent SDK), **agent-format standard** targeted by minted
specs, and **A2A library/approach**; project scaffold; **CI** from the first source commit.

*Exit: decisions written down, scaffold builds green in CI.*

### Phase 1 — Mint

Need-statement intake → **Archon spec** (charter, capability list, MCP tool grants, seed eval
criteria) → **scaffold generator** (runnable agent project) → **local deploy** (Archon comes up
A2A-addressable with an agent card).

*Exit: one command takes a need statement to a running, addressable Archon.*

### Phase 2 — Delegate

A2A client in Demiurge; task routing into the stable; a **task ledger** recording what was
asked, of whom, and what came back.

*Exit: Demiurge hands a task to a stable Archon and records the outcome.*

### Phase 3 — Curate

Eval-suite generation at mint time; the **admission gate**; the **outcome ledger** driving
tenure (keep / revise / retire); **failure distillation** (field failure → new eval case →
successor must pass it).

*Exit: an Archon is admitted, fails in the field, is revised, and passes the failure-derived
eval.*

### Phase 4 — Bootstrap (the proof)

Mint **Archon Zero** with a charter that serves Demiurge's own development (candidate:
authoring and maintaining Demiurge's eval cases; alternative: scaffolding new Demiurge
modules). Run the full loop on it and document the run end-to-end as the flagship demo in the
README.

*Exit: the v1 definition of done, recorded.*

## Kill criteria

This project nearly got shelved before it started, and that doubt stays on the record: the
honest conditions under which Demiurge should be declared dead — persistence losing to ad-hoc
spawning, the curation loop never closing, the standards it rides dying, or a runtime
absorbing the loop natively — live in [docs/why-demiurge.md](docs/why-demiurge.md).

## Risks

- **Full lifecycle is wide for a v1.** Mitigation: each phase demos standalone; the loop only
  fuses at Phase 4.
- **Self-reference invites scope creep** (building Demiurge features *for* the demo).
  Mitigation: Archon Zero's charter is fixed at mint time; anything outside it is out of scope.
- **A2A and agent-format ecosystems are still moving.** Mitigation: by charter Demiurge owns
  none of them — adapters stay thin and swappable.
