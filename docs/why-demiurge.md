# Why Demiurge exists — and what would kill it

*The honest decision note behind the project. Companion to [PLAN.md](../PLAN.md); goal shaped
2026-07-05/06.*

## The doubt, first

Demiurge nearly got shelved before it had a repo. The obvious objection: modern harnesses
already spawn agents ad hoc — Claude Code mints throwaway subagents on demand, and they're
good. If a capable orchestrator can conjure a competent one-off specialist any time it likes,
what's left to build?

## The answer that kept it alive

What no runtime currently owns is the **judgment loop above the spawning**: deciding when a
recurring need has *earned* a purpose-built, **persisted** specialist rather than the
thousandth throwaway; authoring that specialist as a portable spec; and then treating the
resulting population as something to be **curated** — evaluated, improved, re-specced,
retired — rather than a pile of definitions that only ever grows.

That is Demiurge's entire claim:

1. **Mint** — recognize when a recurring task justifies a persistent Archon vs. a disposable
   subagent, and author it as a portable [Agent Format](https://agentformat.org/) `.agf.yaml`
   spec (never a proprietary one).
2. **Delegate** — hand real work to Archons on any compliant runtime over A2A, tools via MCP.
   Demiurge runs nothing itself.
3. **Curate** — the fused loop: eval-gated admission, outcome-based tenure, field failures
   distilled into new eval cases. Agents that stop earning their place get revised or retired.

Everything else is deliberately ceded to the standards it rides. If a feature doesn't serve
the mint/delegate/curate loop, it's out of scope — see the non-goals in `PLAN.md`.

## Kill criteria

Kept honest and checkable. Demiurge should be shelved — publicly, in this file — if any of
these holds:

1. **Persistence loses to spawning.** In the bootstrap demo (or any fair comparison), a
   curated, persistent Archon performs no better on its recurring task than a throwaway
   subagent minted fresh each time. If curation adds nothing over conjuring, the premise is
   dead.
2. **The curation loop never closes.** If by the end of Phase 3 the failure-distillation rule
   (field failure → new eval case → successor must pass it) can't be demonstrated end-to-end
   on a real task, the "fused loop" is a diagram, not a product.
3. **The rails die under it.** Demiurge owns no runtime, format, or protocol *by charter* —
   which means it dies if its rails do. If Agent Format or A2A stalls or pivots such that
   riding them costs more than owning replacements would, the charter forbids the rescue, so
   the project ends instead.
4. **A runtime absorbs the loop.** If a major harness ships native persistent-agent curation
   (admission evals, tenure, retirement) of comparable depth, Demiurge becomes a feature, not
   a project. Fold and write up what was learned.
