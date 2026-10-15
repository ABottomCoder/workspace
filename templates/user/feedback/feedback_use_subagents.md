---
name: feedback_use_subagents
description: SUPERSEDED — see feedback_subagent_economy.md; do not seed this rule into a new instance
metadata:
  type: feedback
---

**SUPERSEDED. Do not copy this file into a new instance's memory dir.**

The original rule was "aggressively use subagents — offload research, polling, code reading and drafting to preserve the main context window". It was correct when written: sessions were repeatedly hitting context compression mid-task on long multi-step work.

On a stronger long-context model it inverted. Reflexive delegation cost more than it saved (each subagent re-establishes context, re-explores, reports back, and the report still has to be read), and delegating *verification* produced confident second-hand claims in place of executed evidence.

The current rule is [[feedback_subagent_economy]]: delegate only when the payoff clearly exceeds the overhead, never for self-verification.

Kept as a tombstone rather than deleted, because the reversal itself is the useful knowledge: a context-management rule is a function of the model it was tuned for, and should be re-derived when the model changes rather than inherited.

A sibling rule from another workspace, "use subagents liberally and keep working context under ~60 %
so auto-compaction never fires", is tombstoned here for the same reason. What survives from both:
use subagents for wide reads, genuinely parallel work and protecting the main context from bulk
output; not for single known-file lookups and never for verifying your own work.
