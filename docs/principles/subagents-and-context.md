# Subagents and Context

## The rule

Use subagents for **wide reads, parallel work, and context protection**. Don't use them for a
single known-file lookup or anything you can finish in a handful of tool calls.

**Delegate:**
- Genuinely independent, parallel work: one subagent per repo of a multi-repo ticket, one per source in
  a context sweep ([evidence-and-ask-gate.md](evidence-and-ask-gate.md#3-gather-context-the-full-sweep)).
- Wide multi-file investigation whose raw output you only need the conclusion of.
- Work whose tool output would flood the main context (large logs, transcript scans, many file dumps).

**Don't delegate:**
- A few file reads, one search, a small edit, a lookup where you already know the file.
- Verification of your own work. It stays in the main loop: delegated verification returns second-hand
  claims in place of executed evidence.

**How:**
- One focused task per subagent; usually one is enough. Never exceed ~10 in parallel unless asked.
- Brief precisely the first time (paths, what to return, what not to touch); launch → wait → re-brief
  costs more than doing it yourself.
- Send independent subagents in one message so they run concurrently.
- Commit to the delegation: don't redo or re-derive a subagent's findings once it reports.
- Never pull raw transcripts or large tool outputs back into the main context.

## Context budget

- Prefer targeted reads (offset/limit, `grep -n`) over loading whole files; save context for reasoning.
- Auto-compaction is lossy. Keep durable state in files (work item `LOG.md`/`HANDOFF.md`, project
  `DEVDOC.md`) so a compaction loses nothing important, and compact at natural checkpoints rather than
  waiting for it to fire mid-task.
- Concrete thresholds (when to compact, how much to delegate) depend on the model's context size:
  [model-tuned-rules.md](../reference/model-tuned-rules.md).

## Structured fan-out: only above the single-context line

Fan out one agent per target (then verification by independent contexts that never saw the work, loop until
done; the exception `verification-before-done.md` allows for audits) only when one task does
not fit in one context window: a 50+ file audit, a migration across hundreds of call sites. Below that
line a single context that reads everything is faster and cheaper. Above it, a single context fails
in three ways that discipline does not fix: laziness (declares 50 items done after 20), self-preference
(see `lessons/verification.md` on independent review), and goal drift (an early "don't do X" fades).
Short, single-purpose contexts fix all three. Fan-out is for read-only exploration and audits or
isolated writes (worktree, paper, dry run); live orders, pushes and database changes stay manual and
never enter an autonomous fan-out path, at any scale. Status: a forward pointer, not yet proven by an incident in
this workspace; promote or revise it when one happens.

## Tombstones (superseded rules, kept so the reversal stays visible)

- ~~"Use subagents aggressively; offload research, polling, code reading and drafting."~~ Correct when
  sessions hit context limits mid-task; on long-context models reflexive delegation cost more than it
  saved, and delegated verification produced unverified claims.
- ~~"Use subagents liberally to keep the main context clean; keep context under ~60%."~~ Kept the useful
  half (context protection, parallel reads); dropped the reflex and the fixed percentage, which belongs to
  a specific model and compaction behaviour.

If the model in use is weak on long context, loosen the rule back toward delegation. Don't loosen it by
default; re-measure when the model changes.
