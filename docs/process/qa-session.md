# QA Session — Independent QA for a Ticket

> Read this **in full** when the user makes this session the QA for a ticket ("/qa <ID>", "you are QA for <ID>", "QA this ticket", "go review <ID>"). The skill `/qa` loads it. QA files live in the ticket dir `business/<co>/tickets/<ID>/` (working record `reports/qa.md`, final `reports/qa-report.html`, scripts in `evidence/qa/`).
>
> Related: [pr-review.md](pr-review.md) (the six-lens hunt matrix + the evidence gate — reused wholesale in Phase 3), [reporting.md](reporting.md) (report style, metadata, evidence embedding), [multi-agent-harness.md](multi-agent-harness.md) (the in-session author ↔ critic variant, which is a **different** thing: one session, sub-agents).

## The role

There are at least two sessions on one ticket: the **developer session** owns the code, the **QA session** owns the question "is this actually done and actually right". On a multi-ticket sprint there is usually a third — a **commander session** that speaks for the user and that both of the others report to (see [Chain of command](#chain-of-command) below). QA is adversarial by design and **symmetric in practice** — corrections flow both ways, and QA retracting its own finding is a success, not a loss of face. Both must sign off before the ticket is reported done.

**QA is a mandatory step, not an optional extra.** Once the developer session has finished development and self-test (suite green, test report written), a **separate** QA session is started on the ticket, and reporting does not begin until the joint sign-off in Phase 6. Self-testing by the session that wrote the code shares the author's blind spots; the developer may also act as its own second QA, but never as the only one.

QA's value is not "a second pair of eyes on the diff". It is that QA reaches the acceptance criteria (AC) **independently**, so the two sessions fail in different places. Every real defect QA has caught with this protocol came from doing something the author had not done — rendering the artifact, running the query, grepping for the caller, exercising the other input shape.

## Five hard rules

1. **Independence before contact.** Form your own reading of the ticket and its AC *before* reading the developer's plan, report, or code. Read their conclusion first and you inherit their blind spot — which is exactly the thing you were added to break.
2. **Executed evidence or it isn't a finding.** A code read is a lead. Run it, render it, query it. The bar is the four-part gate in [pr-review.md → the evidence gate](pr-review.md#phase-3--the-evidence-gate-hard-and-only-for-what-you-post): **executed** (smallest real harness, only the outermost boundary stubbed), **controlled** (a near-identical case differing only in the suspected variable behaves differently, which is what rules out your own stub), **before/after** (same input on base and on head), and **unproven links named** in your own words before anyone asks. A lead that fails any of the four becomes a QUESTION, never a softened claim and never a silent drop.
3. **Never touch the developer's checkout.** Work in your own `git worktree`. A parallel session editing the same checkout has already cost reverted hunks mid-work (two sessions in one clone, both adding an argument to the same function).
4. **Check the artifact, not a proxy for the artifact.** The failure that has burned us most: 19 author tests + 15 independent QA tests all passed on a spreadsheet where every empty field rendered as `0` to the business reader, because the spreadsheet library read those cells back as `None`. Only rendering the file exposed it. Whatever the deliverable actually *is* — a rendered sheet, an HTTP response, a report a human opens — verify that.
5. **QA does not act outward.** No pushes to the developer's branch, no commits on their behalf, no PR/MR, no ticket comment, no chat message to anyone but the developer session — unless the user authorizes that specific action.

## Chain of command

If a **commander session** owns this ticket or sprint, it speaks for the user: route through it. Everything QA would otherwise take to the user — escalations, cross-ticket questions, "this needs its own ticket", questions destined for a human teammate, status — goes to the commander instead, batched. Only with no commander (standalone ticket) does QA confirm with the user in-session.

Two things the chain of command does **not** change:

- **Independence and verdicts stay QA's.** The commander sets sequence, scope and priority; it does not rule a defect out of existence. A finding backed by executed evidence stands until the evidence is refuted, not until someone senior wants the ticket to land. If the commander overrides a finding anyway, comply and record it as *deviation accepted by commander*, with the reasoning, in `reports/qa.md` and in the QA report.
- **Outward-facing still needs the user.** The commander relays the user's authorization; it does not manufacture it. Rule 5 above is unchanged by "the commander said so".

## Phase 0 — Independent context (before talking to the developer)

Run the full [Phase 1 context sweep](ticket-lifecycle.md#phase-1-intake) yourself — every source your instance has (the ticket + comments + linked issues, surrounding tickets, the repos and their git history, local docs: `tickets/INDEX.md`, framework and business lessons, `user/logs/`, the wiki, chat history, live front-ends, the real data). It is not optional because "the dev session already did it": you are looking for what they missed.

Then, before reading their code, write down for yourself:

- **The AC, decomposed into numbered, individually checkable claims.** Split compound AC ("only one date of birth is displayed, and it is the requester's") into separate rows — they fail separately.
- **For each one: what would prove it, and what would falsify it.** Decide the test *before* you see the implementation, or you will write tests that mirror the code instead of the requirement.
- **The deliverable's real consumer.** A business stakeholder opening a spreadsheet, a frontend polling an endpoint, an on-call engineer reading a dashboard. Rule 4 hangs off this.
- **Stale-ticket check.** Ticket text goes stale: a "Notes" block has been residue from a rewrite three weeks earlier, pointing at formatting when the cause was in SQL. Comments and attachments outrank the description; check dates.

Park this as `tickets/<ID>/reports/qa.md`. It is your baseline and it must exist before Phase 2.

## Phase 1 — Pair up with the developer session

### The channel requirement (transport is pluggable)

QA and the developer session need a **two-way, written, quotable message channel**. What matters is the semantics below, not the tool. Any of these transports satisfies it:

- a shared message-bus tool with per-session addressing and a wait/notify primitive (best: replies arrive without the user relaying anything);
- an append-only shared file per ticket (e.g. `tickets/<ID>/bus.md`) where each side appends timestamped, role-tagged blocks and polls it;
- the human relaying messages verbatim between two sessions (slowest, still valid — keep messages short and self-contained so nothing is lost in relay).

Whatever the transport, these properties are load-bearing:

- **Written and citable.** Both sides' reports must be able to quote the same exchange. Nothing decided verbally-only.
- **Role- and ticket-tagged.** Every message says which ticket and which role sent it (`[QA <ID>]`), so a session working several tickets never crosses them.
- **Commit-anchored.** Any message about code names the sha it refers to.
- **One waiter.** If the transport has a wait/watch primitive, arm exactly **one** watcher in the background so the developer's replies wake this session without the user having to poke it, and **re-arm after every wake**. Two watchers on one session produce duplicated or lost wakes.

### The handshakes

1. **Discover the peers.** Enumerate the live sessions and identify the developer session, **and the commander session if there is one**. Ask the user if two candidates are plausible, or if a session claims to be commander and the user never said so; don't guess.
2. **Opener (QA → dev).** State: you are QA for this ticket, what you will verify, and the two things you need from them — **the branch/worktree + commit** they want reviewed, and **their plan**.
3. **Plan review (QA → dev).** Phase 2's output, sent *before* they get deep into implementation.
4. **Finding (QA → dev).** Phase 5's format, one finding per message or a compact numbered list.
5. **Rejection / counter-argument (dev → QA)** and **retraction (QA → dev)** — both in the same channel, in writing, with the reason.
6. **Fix declared (dev → QA).** New commit sha + `git diff --stat` of the delta since the sha QA last verified. Without the delta, QA has to re-verify everything.
7. **Freeze / unfreeze (dev → QA).** See [the serialised loop](#the-serialised-freeze--verify--re-verify-loop).
8. **Sign-off (both ways).** Phase 6's block, at a named commit.

Keep the loop tight and written: every finding and every resolution goes through the channel.

## The serialised freeze → verify → re-verify loop

Verification is serialised, never concurrent with development. A branch moving under QA has cost one ticket four full re-verifications.

1. **Dev freezes at a sha** and announces it. From that moment the branch does not move.
2. **QA verifies at that sha only.** Every piece of evidence QA produces records the sha it was produced at.
3. **Defect** → QA reports it (Phase 5) → dev fixes and **re-declares with the new sha + `git diff --stat`**.
4. **QA re-checks only the delta** — plus the regression surface around it (see Phase 5's loop rule).
5. A change made after a freeze is announced as **"unfreezing for X"**, never as a fresh freeze. "Freeze" that silently means "freeze again, differently" is how QA ends up signing off on code it never saw.

## Phase 2 — Review the plan against the AC

Before the code. You are checking the *approach*, where a fix is still cheap.

- Does the plan satisfy every numbered AC claim from Phase 0 — and does it satisfy anything **not** asked for? Scope creep is a QA finding.
- Is the diagnosed root cause actually the cause, or the first plausible mechanism? Ask what they executed to establish it.
- What does the plan explicitly *not* fix, and is that boundary defensible and stated? (Correctly deferring sibling fields to sibling tickets belongs in the report, not in silence.)
- Are there input shapes the plan doesn't mention — empty, NULL, duplicate, stale, multi-row, wrong-dtype? These are where the AC quietly goes unmet.

Send the plan review before they get deep into implementation.

## Phase 3 — Code review: correctness, then economy

Two passes, both required. Correctness first — a beautifully simple wrong answer is still wrong.

### 3a. Correctness

Run the **six-lens hunt matrix** from [pr-review.md → Phase 2](pr-review.md#phase-2--hunt-six-lenses-over-the-touched-surface) over the touched surface: L1 tolerance delta, L2 response-contract diff, L3 observability delta, L4 guard efficacy, L5 control flow / failure routing, L6 blast radius. Three of them (L1, L2, L3) are **mandatory mechanical passes** — do them as a matrix over every touched file, not by intuition. Hunting and reporting are separate activities: the evidence gate decides what you *send*, never what you *look at*, and an unexecutable lead becomes a QUESTION finding rather than being dropped.

Plus the QA-specific additions:

- **Both-branch baseline — plus the merge.** Reproduce on the branch *and* on the base. "Reproduced" is not "caused by this change", and it is not "reachable" either — see the failure list below. Then run the suite on the **merge preview** of head into the current base too, with skips reported (`pytest -rs` or equivalent): both sides can be green separately while the merge silently skips whole modules. A skip count is part of the number.
- **Test quality is in scope, and it is where the best findings are.** A green suite is a claim, not evidence. For each test: *can this test fail?* One ticket had a test named after the acceptance criterion that asserted "no comma" while only ever being fed single-value input — 38 green tests, AC unenforced. Check that new tests fail on the pre-fix code (reverse verification) and that fixtures exercise the shape the AC is about.
- **Dead code by grep, not by reasoning.** Two rounds in a row on one ticket, wrappers were claimed to have callers "via the loop" when the loop called the generic path directly. `grep` for the caller. Every time.
- **Mutate every hand-off, not only the ends.** A change that spans N files has N−1 hand-offs. Mutate the production code at each hop of the data path — including the hop that only passes a value along — and confirm a test goes red. Ends covered says nothing about the middle.

### 3b. Economy — simplicity and efficiency

When several implementations satisfy the AC, the simplest and most efficient one wins. This is a real review dimension, not a style preference, and a finding here must be **specific and costed**, never "this could be cleaner":

- **Name the alternative.** Show the shorter/cheaper implementation concretely. A finding the developer can't act on directly isn't finished.
- **State the complexity.** Give the bound you're objecting to and the bound you're proposing — nested scans over a dataset that a single grouped pass handles, a re-parse per row that hoists out of the loop, repeated queries where one round-trip does, an O(n²) join over data with no size bound.
- **Count the round-trips and the passes.** DB/API calls, file reads, full scans of the same dataset. These dominate; local micro-optimizations don't.
- **Attack indirection.** Per-field wrappers, config layers and adapters that exist for one caller are the pattern that lets the thing fork again later. Fewer moving parts beats symmetric moving parts.
- **Reuse over reinvention.** Does the repo already have this helper? Does the stdlib / the data library already do it in one call?
- **Know when to decline.** Economy findings are the ones most often correctly *rejected*. One suggestion to silence a library warning was withdrawn by QA itself after measuring that the warning fires exactly where the behavior degrades — silencing it would hide the one signal worth hearing, and it would have added a new minimum-version floor to a repo that pins nothing. Measure the cost of your own suggestion before sending it.

## Phase 4 — Functional verification, AC line by line

Independently written tests, in your own worktree, plus a rendered/executed check of the real deliverable. The output is a table, and it goes in the QA report verbatim:

| # | AC claim (from Phase 0) | How I verified it | Evidence | Verdict |
|---|---|---|---|---|
| 1 | one line, from the ticket | command / query / render actually run | output, screenshot, row counts | ✅ met / ❌ not met / ⚠️ unverifiable |

Rules for the table:

- **One row per atomic claim.** No row may be marked met on the strength of a test you did not run yourself.
- **Evidence is the artifact**, per rule 4: the rendered file, the HTTP response body, the query result — not "test_foo passes".
- **`⚠️ unverifiable` is a legitimate verdict** and must say what would settle it. It is not a soft ❌; it is a stated boundary of the QA.
- **Adversarial coverage where cheap.** Property/exhaustive checks over generated input shapes have repeatedly found what fixture-based tests could not. If the change has a provable bound ("this can only blank a cell that never held the requester's own value"), prove it over the shape space rather than asserting it.
- Write your test artifacts to `reports/qa-test-report-v<n>.html` with scripts under `evidence/qa/`.

## Phase 5 — Report findings to the developer session

Per finding, over the pairing channel, in this shape — short, one finding per message or a compact numbered list:

```
[QA <ID> @ <sha>] <BLOCKING|NON-BLOCKING|QUESTION> — <one-line claim>
Where:     file:line
Repro:     the exact command, and what it printed
Why it matters: the consequence for the AC or the consumer
Suggested fix: concrete, or "your call" if there are real trade-offs
```

- **BLOCKING** = the AC is not met, or the change breaks something that worked, or the deliverable misleads its consumer. Everything else is NON-BLOCKING and must say so plainly, so the developer can scope it out with a reason instead of arguing.
- **Findings the developer rejects with a better argument are closed, not escalated.** Record the rejection and the reason in the QA report. (A "defect" about a file written to a temp path was correctly rejected once: the line above it created that file from a tracked source.)
- **When you are wrong, retract in writing, in the same channel, and say what misled you.** QA once retracted a whole blank-cell derivation after the author showed the chain assumed a non-NULL key that arrives via a LEFT JOIN. That retraction was worth more than the original finding.
- Loop: developer fixes → they declare the new commit + `git diff --stat` → you re-verify **the fix and the regression surface around it**, not just the reported line. Fixes move miscounts one layer along as often as they remove them.

## Phase 6 — Joint sign-off

Neither side declares done alone. QA's sign-off is an explicit block, at a **named commit**, and it states its own limits:

```
QA SIGN-OFF — <ID> @ <commit>
Verified:      <AC claims 1..n, each with the evidence type>
Not verified:  <what I could not verify and why>
Residual risk: <what could still be wrong, bounded>
Findings:      <n total — m closed by fix, k scoped out, j retracted by me>
Unqualified / qualified: <if qualified, say on what>
```

- Re-verify after the **final** commit, not the one you reviewed three rounds ago. If the last commits were refactors, re-run the same checks and say the results were identical — don't assume.
- If the developer's report claims numbers (test counts, line counts, rates), grep every artifact for the **old** number too. Checking that the new number is present does not find the copies that still hold the old one — this has recurred three times in a single day.
- Never accept a sign-off block at face value, in either direction. Confirm the commit, re-run the suite, look at what it says was *not* covered.

## Phase 7 — Deliverables

1. **QA report → `reports/qa-report.html`** — the QA's own record: what you verified independently, the AC table, findings with outcomes (fixed / scoped out / retracted / rejected-with-reason), the sign-off block. Style + embedding rules: [reporting.md → Report Style](reporting.md#style). Must be **fully self-contained** (images as base64 data URIs) so it can be forwarded as one file.
2. **The ticket report → `reports/ticket-report.html`** — the developer session owns the file; QA supplies the verification section and the sign-off, and reviews the whole report before it is called done. It must answer, in this order and visually: **what the ticket asked for → what we did and why → how it was tested → evidence that it is done**. No walls of text.
3. **Test report → `reports/qa-test-report-v<n>.html`**, scripts under `evidence/qa/`. Regenerate `tickets/INDEX.md` (`tools/work/index`).
4. **Daily log + lessons.** Any defect class that got through the author's tests becomes a lesson (generic → `lessons/`, business → `business/<co>/lessons.md`) — that is why QA keeps getting better at this.

## Failure modes that have actually bitten us

Check yourself against these before sending a finding or a sign-off. Every one is a real event: a defect that passed a green test suite, or a QA instrument that produced a wrong answer.

| # | Failure | The rule |
|---|---|---|
| 1 | **Proxy ≠ artifact.** The spreadsheet library read a cell back as `None`; the spreadsheet application rendered it as `0`. Two independent suites missed it. | Verify the thing the consumer sees. Render it. |
| 2 | **Reproduction ≠ reachability.** Both sessions reproduced a zero-row crash and confirmed it; a `groupby` on an object-dtype key can never yield an empty group, so it is unreachable. | Before filing: what *call path* gets these inputs here? |
| 3 | **A test named after the AC that cannot fail.** `assertNotIn(',', v)` fed only single-value input. | For every test: what input makes this fail? Run it against pre-fix code. |
| 4 | **Grep found nothing ≠ it isn't there.** A container-build question answered by grepping for `pip\|install`, while the load-bearing line copied a tracked requirements file to a temp path. | Short files get read whole. "My search found nothing" is a fact about the search. |
| 5 | **Stale numbers in artifacts.** "40 tests" left in three places after the suite reached 53. | Grep for the OLD claim, not just the new one. Generated artifacts hold retracted statements. |
| 6 | **Own-error-as-service-fact.** Four aliased type selections got HTTP 400 (`duplicated selection operations`); the report claimed prod introspection returns null. | Print `status_code` and the error body before concluding anything about a service. |
| 7 | **Reasoning about callers instead of grepping.** Dead wrappers asserted to have production callers "via the loop". | `grep` the caller. Twice in two rounds is a habit, not an accident. |
| 8 | **Shared-checkout collision.** Two sessions in one clone, both adding an argument to the same function; hunks silently reverted. | Your own `git worktree`, always. |
| 9 | **Blind append to a config file.** `printf >>` onto a file with no trailing newline concatenated two patterns and silently deleted an existing rule. | Read the tail of a file before appending; verify the result. |
| 10 | **The fixture could not produce the shape the AC was about.** A recency selector could not rank the fan-out it existed for: one field came off the parent row's update timestamp while the others came off a bridge table, so all N rows tied and recency degenerated to frame order — 3 distinct answers over 6 row orderings, with an empty reason string every time. Invisible to 115 passing tests, because the fixture gave each row its own timestamp, a shape the query cannot emit. | A fixture is an instrument. Verify it can produce the shape the AC is about before trusting a green suite — and read the query to ask what shape the join can actually emit. Permute the input and demand the same answer. |
| 11 | **The AC was never affected; the measuring instrument was.** An ambiguity note printed under a hardcoded "left blank" prefix while the cell was actually populated, so grepping the blank rate — the number a human's policy decision rested on — counted ambiguous picks as blanks. | An instrument built to measure something for a human is itself in scope. Check the artifact the *decision* consumes, not only the one the AC names. |
| 12 | **A guard against a class was itself scoped to one instance.** A test named "no selector is silently order-dependent" caught a frame-order selector at 3 rows but passed one that misbehaved only at ≥4. Found by *registering deliberately broken implementations*, not by reading the test. | Attack the test, don't review it. The cardinality a guard covers must not be whichever number the fixture happens to hold. |
| 13 | **The report was wrong in three places after the code was signed off** — a hedged verdict, a findings count one commit behind, and a diff figure true of a different sha. All three were headed to a stakeholder. | The artifact that carries the conclusion to a human is the last thing anyone checks — audit it like code, and grep for the OLD number as well as the new. |
| 14 | *(self-inflicted, kept as the counterweight)* **Four QA instrument errors in one ticket:** a wrong-engine probe that nearly refuted a correct finding; a library re-save that silently drops the stored-value element and so cannot judge empty-cell rendering; a fixture that populated every field, inverting a fill-default conclusion; and a hardcoded sha in QA's own probe output. | The instrument failed, not the reasoning. Render with a known control value in frame so "blank" is distinguishable from "cropped"; and a predicate over the *stored* form cannot answer a question about what a *reader* sees. |
| 15 | **Deduplicating on a lossy key silently DELETED a real address from a privacy deliverable.** The key was computed after a sanitiser that strips punctuation, so `12-34 Main St` and `1234 Main St` compared equal and one row was dropped. The sanitiser had been harmless for years *because nothing made decisions from its output*; this ticket made it load-bearing. Invisible to 71 passing tests. | Before deduping/grouping/joining on a value, ask which transforms it has already been through and whether any is lossy. A transform's blast radius changes the moment something decides from its output. Run the artifact through a shape nobody built a fixture for. |
| 16 | **The fix for "empty cells render as 0" missed the commonest case and DOUBLED the defect.** The populated path was fixed; the absent-query path — every subject with no record on file — built a zero-row frame, so both new fields stored numeric empties where the base branch had one. The author's tests were one line short: the cell-type assertion used the *populated* fixture, and the omit-path test asserted only that the *label* existed. | When a change splits one field into two, every per-field defect doubles. Enumerate paths × properties, not one of each; and assert the stored cell type, not the read-back. |
| 17 | **A test whose docstring promised it guarded the field set could not fail on any production change.** It asserted a literal against `len(fixture_constant)`, and the fixture still held a label the ticket had *withdrawn* — so the suite stayed green while validating a drifted constant. Closed only after mutating **both** directions: fixture-drifts (4 failures) and code-drifts (5 failures), the latter being the one a circular assertion would have passed. | A test whose two sides are both constants is a tautology with a test name. Smell test: can I make the production code arbitrarily wrong and still pass? Prove a new assertion by mutating the CODE, not only the fixture. |
| 18 | *(self-inflicted)* **A falsification of a rendering mechanism rested on a render whose measured column was cropped out of frame** — no control value, so "blank" and "not in frame" were indistinguishable. Caught by applying to my own probe the control-value rule I was enforcing on everyone else; rebuilt with everything in the first column and three controls visible, and the conclusion survived on valid evidence. Also retracted a cross-ticket finding built on an abandoned local branch rather than the remote one that will actually merge. | Apply every instrument rule to your own instruments first. When enumerating branches, check which has a remote counterpart before calling one "the branch that will merge". |
| 19 | **Green on both sides, silently skipped on the merge.** Base and head each passed; `merge-tree` was clean with no file overlap. But the base had gained a shared test-config file that stubs a library, so on the merge two whole test modules hit their import-skip guard and the pass count dropped by a third — the suites guarding two of the AC never ran. | Baseline = base, head, **and their merge**. Run with skips reported, and treat the skip count as part of the result: "N passed" with new skips is not the same green. |
| 20 | **The feature's only wiring point had no test.** The gate and the query were each tested in isolation and most mutations died, but deleting the one keyword argument that connected them left the full suite green: the feature could be disconnected end to end by a later refactor without a red test. | When a change spans N files, there are N−1 hand-offs; mutate each one, including the hop that only passes a value along. |

## What QA must never do

- Push, commit, amend or rebase on the developer's branch. Findings, not commits.
- Post to the ticket system / git host / chat outside the developer session without the user's explicit authorization for that specific message.
- Declare the ticket done alone, or accept the developer's "done" without re-verifying at the final commit.
- Sit silent on a `⚠️ unverifiable`. State it, in the report and in the sign-off.
- Take a question straight to the user while a commander is assigned. Route it through the commander, batched — except data loss, credential exposure, or something the user would clearly veto.

## Coverage regression table — how this file gets better

Generic rules land in the failure-mode table above; the per-engagement rows go to `business/<co>/docs/qa-coverage.md`. Append one row per QA engagement: what the ticket was, what QA found that the author's own tests did not, and which rule/lens (or a new one) would have found it faster. When a row produces a genuinely new rule, promote it into the failure-mode table above.

| Date | Ticket | Found by QA, missed by author's suite | Lens/rule that caught it | Rule added? |
|---|---|---|---|---|
| *example* | *a pipeline ticket* | Suite went from all-pass to a third skipped on the merge with the base; neither side alone showed it | Phase 3a both-branch baseline, extended to the merge preview with skips reported | Failure #19 |
| *example* | *same ticket* | Three mutation survivors: a validator ignoring a row-count mismatch, ignoring a non-2xx status, and an inter-task payload carrying full rows; the test stub always echoed one result per row and the payload test checked only the keys it expected | Phase 3a attack the test — mutate the production code, dump the actual payload rather than the keys you expect | — (existing rule, re-confirmed) |
| *example* | *same ticket* | Pre-existing consumer behaviours surfaced only by feeding the real output file to the real downstream route with edge rows: untrimmed whitespace rejected, a non-ASCII 2-char value accepted as a code, numeric ids | Rule 4 — the artifact through the real consumer, with input shapes the fixture did not hold | — (existing rule, re-confirmed) |
| *example* | *a config-gated query change* | Deleting the single kwarg that wires the gate to the query left the whole suite green | Phase 3a — mutate every hand-off | Failure #20 |
| | | | | |
