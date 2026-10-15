# Context and memory

Where knowledge is stored, how docs and memory are kept accurate, and how to spend the context window (including when to use subagents).

### Use subagents for wide reads, parallel work and context protection, not for lookups or self-verification
**Mistake:** Two opposite failures: under an "offload everything" rule, reflexive delegation cost more than it saved (each subagent re-establishes context, re-explores and reports, then the report is re-read), and delegated verification produced confident second-hand claims instead of executed evidence; under an older weaker-context model, not offloading filled the window and triggered lossy compaction mid-task.
**Root cause:** A context-management rule tuned for one model's context limits was applied unchanged to another.
**Rule:** Delegate wide multi-file or multi-repo reads, genuinely independent parallel work, and exploration whose raw output would crowd the main context. Do not delegate a lookup you can finish in a few tool calls on a known file or symbol, and never delegate verification of your own work: that stays in the main loop with executed evidence. Brief precisely the first time, send independent subagents in one message, keep counts low (rarely over ~10), do not re-derive a subagent's findings after it reports, and never pull raw transcripts or large outputs back into the main context. Context-management rules depend on the model in use: re-derive them (delegation threshold, context budget, compaction checkpoints) whenever the model changes.
**Seen:** 1

### Route stored knowledge by audience, not importance
**Mistake:** Wrote one project's details into always-loaded memory, then, after correction, into the always-loaded workspace instructions file.
**Root cause:** Bias toward "important, so put it where it's always loaded", with no routing criteria; importance is not universality.
**Rule:** Before writing to an always-loaded file, ask whether a session on an unrelated project would waste context on it. If so, put it in the project-level doc and leave at most a one-line pointer. One fact, one home.
**Seen:** 1

### Quote the document, not its index; correct yourself explicitly
**Mistake:** Told a teammate "memory still says X"; the memory file was correct, only its auto-loaded index line was stale.
**Root cause:** The index is auto-loaded every session while the file must be opened, so "what memory says" silently became "what the index says".
**Rule:** Before citing a doc, open it; indexes, summaries and second-hand accounts are not the doc. Know which file and line a quote came from. When index and file disagree, fix the index first: it has far more readers and none of them can notice. When correcting an earlier message, name which sentence was wrong and say to disregard it, rather than silently re-sending.
**Seen:** 1

### Status docs vs record docs: update one, annotate the other
**Mistake:** Nearly replaced an outdated threshold everywhere, including in a document marked as a historical archive.
**Root cause:** Treated "stale" as an error, but some documents exist to record what was true then.
**Rule:** Ask whether the doc describes now (specs, design docs, repo guides: change it and note "was X, superseded by Y") or records then (logs, archives, minutes, signed SOWs: keep the value and add an inline note with the new value and date). Rewriting history erases the fact that the definition changed, which in client work is often what matters.
**Seen:** 1

### Record gotchas in the repo docs the moment they are confirmed
**Mistake:** A confirmed non-obvious gotcha (an RPC library not supporting method overloading) was documented only after the user asked.
**Root cause:** Documentation was treated as an end-of-task chore.
**Rule:** As soon as a non-obvious behavior or failed assumption is confirmed, append it to the repo's agent-instructions or gotchas file before moving on.
**Seen:** 1

### Review your own past sessions as a detached reviewer
**Mistake:** Error tracking depended only on the user manually marking mistakes, so most of the agent's own errors went uncounted.
**Root cause:** Self-review was left to an optional manual marker instead of a default practice.
**Rule:** Periodically review past conversations as a detached third-party reviewer to find your own errors. Hold the evidence bar high: count only confirmed errors (an explicit fix marker, the user pointing out a mistake, or your own explicit admission) and label inferred ones as inferred.
**Seen:** 1
