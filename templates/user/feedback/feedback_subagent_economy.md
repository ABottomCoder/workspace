---
name: feedback_subagent_economy
description: Delegate to subagents only when the payoff exceeds the context-re-establishment overhead; never for self-verification
metadata:
  type: feedback
---

Subagents multiply cost and time: each one re-establishes context, re-explores, reports back, and then I re-read the report. Delegate when the payoff clearly exceeds that overhead, not by default.

**Do delegate:** genuinely independent, parallelizable work — reading each repo of a multi-repo ticket at once, wide multi-file investigation, a full-context sweep across many sources.

**Do NOT delegate:** anything I can finish in a handful of tool calls (a few reads, one search, a small edit); and never verification or double-checking of my own work — that belongs in the main loop.

**Why this replaced the old rule.** The earlier guidance was "use subagents aggressively" and it was correct for its time: context limits were being hit mid-task. On a stronger long-context model the same habit inverted — reflexive delegation cost more than it saved, and delegating verification produced confident second-hand claims instead of executed evidence. If the model in use is weak on long context, loosen this back; do not loosen it by default.

**How to apply:**
- One subagent is usually enough. Keep spawn counts low; never exceed ~10 parallel unless asked.
- Brief precisely the first time — a launch → wait → re-brief cycle costs more than doing it myself.
- Send independent subagents in one message so they run concurrently.
- Commit to the delegation: don't re-derive a subagent's findings after it reports.
- Never pull raw transcripts or large tool outputs back into the main context.

Supersedes the older "offload everything" rule. See [[feedback_evidence_required]] for why verification stays in the main loop.
