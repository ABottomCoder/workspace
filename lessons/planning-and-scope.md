# Planning and scope

Sizing, sequencing and bounding work: estimates, plans, what is in and out of scope, and when to stop.

### Anchor estimates on measured active build time and on what the ticket really carries
**Mistake:** Features were estimated at conventional per-item sizes, which the client found inflated, and the recalibration used a past project's calendar time (mostly waiting). Separately, a scaffolding ticket was sized large and high-risk because it depended on hard sibling tickets, had five acceptance criteria and the target repo was not cloned locally; the team sized it at the minimum.
**Root cause:** Took high per-item values, under-counted reuse, read dependencies and AC count as size, read "not cloned locally" as "doesn't exist", and did not anchor on own delivery data.
**Rule:** Every estimate cites a calibration anchor from past work, using active build time from commit timestamps, in hours, with realistic values plus one explicit reserve line and external waits (feedback, keys, approvals) listed separately. Before sizing: (1) subtract complexity sibling tickets already carry; (2) grade each AC as engineering work vs a confirmation, one-line config or decision; (3) establish who owns the system and who writes the code (a ticket on another team's platform is often a thin validation shell); (4) if a load-bearing fact is unverified, give a range ("1 if CI exists, 3 if greenfield") and raise it as the first refinement question.
**Seen:** 2

### Priority labels need an action; advice that could be structure must be proposed as structure
**Mistake:** Priority data (stars, frequencies, tiers) sat in a study document for weeks before anyone turned it into a minimal-coverage plan; separately, verbal advice ("walk through each failure case after every design") was given but never proposed as a document step, and the user added it the next day.
**Root cause:** Initiative stopped at the content layer (fixing errors, answering) and left the shape of the material or process to the user.
**Rule:** Any priority label you produce comes with the action it implies. Any advice you give that could be fixed as structure (a checklist, a document step, a mechanism) must be proposed as that structure. The proposal can be declined; it cannot be skipped.
**Seen:** 2

### The named deliverable sets the scope; coupling does not widen it
**Mistake:** The brief was one new output. In one evening a second ticket was opened for half of it, a neighbouring ticket was explored deeply because shared code made it look coupled, and "don't touch the original output" had to be said three times.
**Root cause:** Sized the work by the codebase's coupling instead of the deliverable the user named.
**Rule:** When the user names the deliverable, everything else is out unless it blocks it, and "blocks" means it cannot be produced, not "the code is entangled". Ask in one line before creating any ticket, branch or investigation outside it; default to not creating it. Told the same constraint twice: stop proposing alternatives that bend it. Solve structural coupling by separating the new path (derive a query, add a module), not by widening the ticket.
**Seen:** 1

### Every concrete identifier in a plan is a claim with a one-command check
**Mistake:** A plan said two files "should work unchanged" without opening them (one held a warning comment addressed to exactly this change), and used a path that exists only in other containers.
**Root cause:** Predictions were written in the confident register of findings.
**Rule:** Never write "X should work unchanged" about an unopened file; write "unverified". Grep touched files for the change's own vocabulary. Check paths with `ls` in the context that uses them, hostnames with `dig`/`curl -sI`, env and mounts on the running thing. When a reviewer confirms a finding, check the consequence is the one they stated.
**Seen:** 1

### Apply a correction to every sibling case
**Mistake:** Fixed only the one field the user named while identical fields had the same issue.
**Root cause:** Treated the correction as literally scoped instead of as a pattern.
**Rule:** When corrected on one instance, audit all similar items ("what else follows this pattern?") and fix them in the same pass.
**Seen:** 1

### Start independent work in parallel; announce any deliberate sequencing
**Mistake:** Silently held an independent task until another was pushed; the lead assumed it had started long ago.
**Root cause:** Chose a conservative serial order without telling anyone, though the parts were independent.
**Rule:** When several tasks are approved, start independent parts in parallel (e.g. separate worktrees) right away. If you deliberately sequence something, say so in the status message with the reason.
**Seen:** 1

### When building to last, choose the sound design over the cheap patch
**Mistake:** Risk of repeating demo-grade shortcuts in a rebuild meant to be durable, after the last shortcut-built version had to be rewritten.
**Root cause:** Effort was weighted as heavily as correctness.
**Rule:** When the goal is a reliable product, present both options with real consequences, recommend the sound one and start; effort wins only when the gap is enormous. Example: have a component call your own API with a narrowly scoped credential rather than opening a network path to the database.
**Seen:** 1

### Cap review loops and build the simplest backstop for rare cases
**Mistake:** Ran eleven review-and-fix rounds on a process doc "until no major issues", tripling its length; later a rare code edge case went through three rounds, each adding mechanism.
**Root cause:** The stop condition was left to fresh reviewers with no memory of earlier rounds, every finding was fixed by adding rules, and diminishing returns were not flagged.
**Rule:** Set a round cap (2-3) and a written "must fix" definition before the first review round. Prefer deleting or merging rules over adding. When a round yields only edge cases, stop and tell the decision-maker. For rare cases in code, build the simplest backstop first (hold it and hand it to a human) and automate only on request.
**Seen:** 1

### Design exception flows around the person who knows the answer
**Mistake:** Went through three admin-side designs for a cancellation edge case before the lead asked why the user was not simply asked at the moment of cancelling.
**Root cause:** Anchored on the requirement's wording and optimised the admin side without asking who holds the decision.
**Rule:** For any exception flow, ask first: who knows the answer, are they present when it happens, can the UI ask them then? Design system backstops and manual handling only for cases where nobody is present.
**Seen:** 1

### A caveat repeated three times is a task
**Mistake:** Shipped work for days with the caveat "local build is broken, someone else please click through"; the cause was one dangling symlink in the package store.
**Root cause:** Disclosing a limitation felt like managing it, and it pushed the cost onto teammates.
**Rule:** On the third appearance of the same caveat, spend ten minutes on the cause. If the fix touches shared state (lockfiles, shared stores), diagnose fully, ask before changing, and restore exactly anything you tried.
**Seen:** 1

### Do not reference unconfirmed processes from always-loaded instructions
**Mistake:** Added a pointer in the always-loaded agent instructions to a draft process doc whose process and tooling were still undecided; the lead asked to revert it.
**Root cause:** Treated "draft written" as "adopted".
**Rule:** Draft process docs stay unreferenced until the owner confirms the process and its prerequisites exist; only then add the pointer.
**Seen:** 1

### Enumerate every binding constraint before computing a worst case
**Mistake:** Computed a "worst-case daily loss" by summing per-item budgets; the result broke four explicit limits in the code (per-scan, total positions, margin, per-day caps) and was several times the worst drawdown in a stress-year history.
**Root cause:** Did arithmetic on one constraint before collecting all of them.
**Rule:** For any bounding question (max loss, max exposure, peak load), open every place limits are defined, list them in a table, identify which one binds, compute respecting all simultaneously, then sanity-check against empirical history; a large gap means the computation is wrong.
**Seen:** 1
