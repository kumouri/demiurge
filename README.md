# Demiurge

**Demiurge** is a meta-agent — a *Thrallherd* — that owns the full lifecycle of specialized
**Archon** agents: it **mints** them, **delegates** work to them, and **curates** the resulting
stable over time. That loop is the entire product.

## The loop

```
        need statement
              │
              ▼
   ┌─────── MINT ────────┐    spec → scaffold → deploy; every Archon ships
   │                     │    with a generated eval suite and must pass it
   │                     ▼    to enter the stable (eval-gated admission)
   │                  stable
   │                     │
   │                     ▼
   │               DELEGATE          real tasks, routed over A2A,
   │                     │           every outcome recorded
   │                     ▼
   └────────── CURATE ◄──┘    outcome-based tenure: keep / revise / retire.
                              Every field failure is distilled into a new
                              eval case — the suite grows from reality,
                              and a successor must pass the very case its
                              predecessor failed.
```

Curation is one fused loop, not two systems: **evals answer "can it do the job in principle,"
outcomes answer "is it doing the job in practice,"** and outcomes continuously author the evals.

## What Demiurge is not

Demiurge deliberately does **not** own:

- a **runtime** — Archons run on existing agent runtimes,
- an **agent format** — specs target existing format standards,
- a **protocol** — delegation rides **A2A**, tool access rides **MCP**.

It rides those rails and owns exactly one thing: the judgment layer above them —
*what agent should exist, whether it's any good, and whether it stays.*

## First proof

The bootstrap demo: Demiurge's first mint is **Archon Zero — an agent that helps build
Demiurge**. Minted, eval-gated, delegated to, and curated by the very loop it contributes to.

## Status

Planning — see [PLAN.md](PLAN.md) for the refined goal, v1 definition of done, and the
phased roadmap.
