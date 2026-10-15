# Verification Antipatterns — how measurement actually fails

> Read this **before quoting any number, count, rate, or "verified" claim**, and before writing a new assertion in a test.
>
> Seeded, not accumulated. Every item is a real defect that got past a green test suite, de-identified and generalised. Keep them; add new ones as they occur (business-specific instances go to `business/<co>/lessons.md`, the generic pattern here). A rule without its story gets deleted by the next team, so each item keeps the mechanism that made it feel like an observation.

## The headline finding

Over one multi-ticket epic, **nine measuring instruments were wrong at least once, and not one of them was a code defect.** A renderer mistaken for the real application; a file re-saved before being measured, which rewrote the exact bytes under measurement; a fixture that populated every field, so a sparse-data defect was invisible; a `grep` that counted populated cells as blanks; a count that answered "stored" while labelled "user-visible"; **the ticket report itself**, wrong in three places; a status message quoting a commit the branch had already passed; and a number relayed between two sessions and copied into two artifacts unchecked.

**The lesson:** engineers verify code and tests hard, and treat the *measuring apparatus* as neutral. A fixture, a grep, a renderer, a relayed number and the report are all instruments, and each has a blind spot that makes a wrong conclusion feel like a direct observation. Budget scrutiny for the instrument, not just the result.

---

## 1. Assertions that cannot fail

**The mechanism.** A test passes because it matches nothing, not because the code is right.

Real forms this took, all in one ticket:
- A predicate tested for a *missing* element when the defect was a *present but empty* element. It matched nothing, passed on unmodified base, proved zero.
- A malformed expression of the shape `1 == (len([...]) and count)` — always true.
- Two `if x is None: return` early-outs that made a broken extractor indistinguishable from a pass.

**The rule.** For every new assertion, ask "what input makes this fail?" and then **actually produce that input.** Reverse-verification is not a formality at the end: a test that passes on the pre-fix tree is a **defect in the test**, and that result must be read as loudly as a failure. Hunt for assertions that *cannot* fail, not just assertions that are wrong.

## 2. A check's NAME is what tells you how to read its FAIL

**The mechanism.** A check named "requests with and without rows produce the SAME sheet geometry" actually asserted label *text* equality. It failed. Investigating, the baseline failed too, printing 30 rows against 24 — which read as a large pre-existing geometry difference. Both numbers were artifacts of the harness (a mutating setup step had been skipped). Truth after a clean re-run: geometry identical, one label differs, pre-existing.

The harness bug took minutes to fix. The damage came from the **name**: a failing check is read through its own description, so a check named for a property it does not test hands you a wrong hypothesis at exactly the moment you are least able to question it — you're already in "is this a regression?" mode, reaching for a comparison run rather than re-reading the assertion.

**The rule.** The name of a check must be the assertion, restated. If describing it needs an "and", it is two checks — split them, because the whole value of splitting is that the FAIL then names its own cause. A mis-named PASS is harmless; a mis-named FAIL actively misdirects. And when a FAIL sends you to a baseline for comparison, **make the baseline run the real call order** — a harness that skips a mutating step is not measuring the same program.

## 3. A count is only as good as its exclusion rule — and the rule is what nobody checks

**The mechanism.** Three counts in one ticket each needed narrowing, and **none of the corrections came from re-counting.** They came from someone testing the *rule* the count applied. One count included items that were structurally invisible. The next excluded a category on an untested premise, which the reviewer falsified with a minimal reproduction. A third used a `grep` matching only one of three valid serializations, returning 8 where the truth was 9.

Attention goes to the arithmetic and to the conclusion, never to the predicate in between. A filter reads as neutral bookkeeping, so it escapes the scrutiny the claim gets — yet it decides the answer.

**The rule.**
- When quoting a count, **state the exclusion rule explicitly and label each predicate `verified` or `assumed`.**
- If any predicate is assumed, quote the **unfiltered** number too and describe the subset as unmeasured.
- If a predicate is *necessary but not sufficient* for the thing you're counting, no count derived from it is a count of that thing — only an upper bound. Say "stored", not "visible".
- **Two independent corrections to the same number means re-derive the measurement, not patch it.**
- Put the exclusion rule **in the script, not in the prose**, and re-run rather than re-derive when restating a number. If a document quotes the same quantity twice, the second quote must come from the same execution as the first, or say why it differs.

**The silent version: a filter at the extractor's exit.** An intake extractor ended with a one-line `.filter()` keeping only rows with a well-formed identifier, and reported "N rows, 0 failures". "0 failures" meant "nothing threw", not "nothing was dropped" — a few percent of rows were gone, and they were exactly the population the question was about (the requests that *lack* the identifier, which a rarely-exercised code branch exists to serve). Every downstream denominator moved, and one rate was relabelled as a different rate in the report.
- **Before quoting any count, read the exit of the parser that produced it.** Look for `.filter(`, `if not x: continue`, `dropna`, a regex `match` with an `else: pass` — each one redefines the denominator.
- **Drops are classified and counted, never silent.** The right shape prints `total / ok / each kind of non-conforming` together. A metric that only counts exceptions says nothing about completeness.
- **Look at the non-conforming rows first.** Rows that fail a format check are usually the abnormal-path sample, and the abnormal path is usually where the defect is.

## 4. Stopping at "the column exists"

**The mechanism.** A field existed and was reported as available. It was populated on 7% of rows. Reporting existence without coverage would have sent a product owner down a wrong path.

**The rule.** Schema is not data. Always check **fill rate and value distribution**, not just presence.

**Fill rate is not distribution.** A date-of-birth column was mostly non-null and looked usable, so "dates differ" was used as evidence that two records belonged to different people. Most of the non-null values were a single placeholder date. Any group holding one placeholder and one real date "differed", so the criterion was mostly noise, and several already-published figures shrank by half or more; one headline number had to be withdrawn. The tell had been in plain sight: the share of groups with a ≥20-year spread and the share with a ≥40-year spread were almost identical. A natural distribution does not do that.
- **Before any column is used in an equality or inequality test, run `GROUP BY col ORDER BY COUNT(*) DESC LIMIT 10`.** Sentinels (`1900-01-01`, `0`, `'UNKNOWN'`, empty string) show up in the first row.
- **Nested thresholds are a free sanity check.** If `>= 20` and `>= 40` give the same answer, suspect a sentinel before explaining the phenomenon.
- For any number that rests on "these two values differ", ask how many of those values are real.

## 5. Running a number once

**The mechanism.** An average came back 66.7, then 11.4, then 9.9 across three identical runs — a heavy-tailed distribution, plus a sampling method that could not estimate it at all. It was one keystroke from being published as a fact.

**The rule.** **Re-run anything you intend to state.** If the sampling re-randomizes, repetition is free evidence. An unstable number is a finding in itself.

## 6. Sampling the convenient population

**The mechanism.** A rate was measured over "random records" and quoted as an answer about *requests*. It produced a confident directional claim that the real request population **inverted**, because the two populations differ on exactly the variable being measured.

**The rule.** **Name your population before you quote a rate.** And beware `LIMIT` inside a sample — it takes whichever rows arrive first, which correlates with physical storage order. Fine for "give me some seeds", wrong for any distribution statistic.

Two more forms it took:
- **Population tail risk quoted as observed behaviour.** "About 1 in 1,000 requesters sits on a junk address that would pull in hundreds of thousands of records" — both inputs were true *of the whole customer base*. Measured over the actual requesters, it happened zero times; the worst case was a handful of records. The session's own measurement notes already said so ("expected count < 1"). The scarier number was chosen because it supported the conclusion being drafted.
- **A share profiled over the whole table, quoted about one code path.** "nearly all users joined in the last two years" was offered as evidence that a scan would drop history. The table included anonymous device accounts the feature can never match; over the accounts the code path can actually reach, the share was far lower and no longer supported the claim.

So, additionally:
- **Every number travels with its population**, in the sentence: "across all customers…", "across the N real requesters…". A bare percentage does not go into outward text.
- **When both a population figure and a measured-sample figure exist for the same question, lead with the measured one.** The population figure can only appear as "a risk to guard against", immediately followed by "observed N times".
- **Restrict to the rows the code path can reach**, and cross-tab by at least one categorical column (type, source, migration flag) to see what is driving the number.
- **Before giving a conclusion, grep your own measurement notes.** Evidence already written down and not re-read is the same as not measured.

## 7. The fixture that cannot exhibit the bug

**The mechanism (two variants, both shipped).**
- A fixture populated every field, so a sparse-data defect was invisible through 105 passing tests.
- A serialization matcher was validated only against files the local writer produces. That writer emits exactly one of the three forms the format permits; the other two appear in files from other library versions. The same gap had already cost two separate sessions a wrong test result.

**The rule.** When parsing a serialized format, test against **synthetic examples of every form the spec permits**, not only against output from the one writer available locally. Enumerate the variants explicitly, and include a **negative control** (a legitimately-populated value must not match an "is empty" matcher). More generally: ask what property your fixtures share that the real inputs do not. A classifier with N branches will silently mislabel the N+1th form as whichever branch is the fallback.

## 8. Every render used as evidence needs a known-visible control in frame

**The mechanism.** A probe rendered a document to check whether a cell displayed a spurious value. Nothing appeared, which read as "refuted". The probe happened to include a populated control value nearby — and the control was invisible too, revealing that the whole column had been cropped out of the thumbnail. Without the control, a cropped render would have been published as a negative observation.

A render answers "what is in this image", not "what does the file contain". Absence in the image has two explanations — not drawn, or not covered — and nothing in the image distinguishes them.

**The rule.** Every render used as evidence must contain a **known-visible control**. If the control isn't visible, the render is not evidence about anything, including the region you were inspecting. Applies to thumbnails, screenshots and browser captures alike.

**Corollary — never re-save or resize an artifact before rendering it as evidence.** A library re-save can rewrite the exact bytes under measurement (in the original case, empty numeric cells changed representation, and only one of the two representations displays the defect). The file you rendered was not the file you generated.

## 9. Name the instrument in the claim

**The mechanism.** "Empty cells render as `0` in the spreadsheet app" was confirmed by two sessions — both through the same preview utility. The actual application showed those cells blank.

**The rule.** **Corroboration requires a different method, not a second run of the same one.** Two sessions using one tool is n=1. Say "0 in \<named preview tool>", never "0 in \<the real application>" unless you opened the real application.

## 10. One environment treated as representative

**The mechanism.** A suite was reported green on the newest interpreter only. The older interpreter that production actually runs then found a real defect *and* a false pass (a regex overshooting a self-closing element into the next one, so the assertion read the wrong field and passed for the wrong reason).

**The rule.** Report test counts **per interpreter/runtime, with exact dependency versions** — especially where the requirements file pins nothing. Test the runtime production actually uses.

## 11. "N passed" is not evidence that the subtests passed

**The mechanism.** With a subtest plugin, a test whose body doesn't raise is recorded as an item-level **pass** even when every subtest inside it fails; the failures are reported separately. Grepping `PASSED` found the divergence and reported it as a finding.

**The rule.** When a suite uses subtests, **read the subtest lines, not only the pass count** — and never grep `PASSED` as a proxy for "this test cannot fail". Cross-check any reverse-verification figure under a runner that counts subtest failures individually.

## 12. "Verified" is scoped to what you ran, not to the change you made

**The mechanism.** A full suite on two interpreters, every new test reverse-verified, before/after artifacts rendered — and three things the change could plausibly break had **no coverage at all**: the sibling function sharing mutable state, the multi-item case (every probe used one item, while the function is a loop), and a safety property asserted in a **code comment** and never executed. Closing them took one script and found a third real defect.

**The rule.** After a change, **list what it could break before deciding you're done**: the shared state it touches, the loop it sits inside, the neighbouring path, and every safety property you claimed in a comment but did not run. A comment asserting "this would misalign here" is a testable claim; leaving it untested is the same error as reporting a code-read as verified. **Extra runs of the suite you already have do not reduce this risk at all.**

## 13. Fixing a symptom can delete the evidence for the real bug

**The mechanism.** Suppressing literal `None` tokens in a rendered address turned obviously-broken output into clean, plausible, still-wrong output — and the deferred follow-up lost its only reproducer.

**The rule.** When suppressing a visible artifact while deferring the underlying cause, **keep a signal** — a log line, a warning, an explicit note in the follow-up. Never defer a defect *and* remove its symptom in the same change. For a deliverable someone relies on, plausible-and-wrong is worse than obviously broken. A visible artifact is often the only observable of a second, deeper defect: before removing it, ask what it was signalling.

## 14. A lossy transform becomes load-bearing the moment you compare its output

**The mechanism.** Deduplication keyed on a display string that had already been through a character-stripping scrub. Two genuinely different addresses compared equal, and one was silently dropped from a deliverable. The scrub had been harmless for years while purely cosmetic.

**The rule.** Before deduping, grouping, joining or comparing on a value, **trace every transform it has already been through and ask whether any is lossy.** If one is, key on the source value and present the transformed one. A transform's blast radius changes the moment something makes decisions from its output.

## 15. A predicate over stored form cannot answer a question about what a reader sees

**The mechanism.** Counts of "defective cells" were derived from the stored representation, then labelled as what the reader would see. Merged-over, unstyled, out-of-range and hidden rows/columns all break that equivalence, in different directions.

**The rule.** Enumerate every reason a stored item might not reach the reader before quoting a user-facing number — and re-derive the count when the definition tightens. The conclusion may survive, but it has to be re-earned, not assumed.

## 16. Match the evidence type to the claim type

**The mechanism.** Across three documents and several turns, a confident assertion that "these four fields have no ticket covering them" was never verified. One ticket-system query (`parent = <epic>`) refuted it in about ten seconds: three of the four were ticketed, and the ticket cited as evidence was about something else entirely. The *data* half of the same analysis had been measured properly — which is what made the organizational half feel equally solid.

**The rule.** A claim about data needs a query. A claim about runtime needs a run. A claim about **organizational state** — "there's no ticket for this", "nobody owns that", "X is responsible for Y" — needs a **ticket query and a read of the ticket body**. Never let evidence strength earned in one domain underwrite a claim in another.

## 17. A written record outranks the chat message

**The mechanism.** A session reported that a peer had "reaffirmed" a ruling. The peer's written decision record already contained the reversal, timestamped two minutes earlier.

**The rule.** Where a written record exists (a decisions doc, a ticket comment, a report), **that is the state**; chat is a notification about it. Before asserting what someone decided, grep the record — and quote the sha/section you read, so a divergence surfaces instead of propagating.

## 18. A specified string is a requirement, not a suggestion

**The mechanism.** An AC named two column headings verbatim. One was shipped under a different name, on the reasonable ground that the data couldn't support what the specified name implied — defended as caution. But the questionable inference lived in the *selection rule*, not the *label*. Renaming the heading removed no inference; it replaced a stated requirement with private wording and left the actual guess undocumented.

**The rule.** When an AC states a literal string — a label, filename, field name — that string is the requirement. If the data can't support what it implies, **publish the rule and escalate the wording**; do not silently reword the requirement. "Caution" that changes a specified deliverable is a product change without authority. Test both invariants: the specified string is used, and the rule behind it stays documented.

## 19. Don't move the thing under measurement

**The mechanism.** Declaring a freeze and then committing again; moving a frozen sha while a reviewer was verifying it; a report quoting a figure measured at a different sha than the one it named; a full commit sha written from memory instead of read.

**The rule.** Serialise it: freeze at a sha → verify at that sha only → re-declare with `git diff --stat` → re-check only the delta. A post-freeze change is announced as "unfreezing for X", never as a fresh freeze. **Every sha, count and version in a report comes from an execution, pasted — never from memory.**

## 20. Blind bulk edits rewrite history that was correct

**The mechanism.** A `sed` across docs to update a commit reference also rewrote sentences that named *historical* commits, making true statements false. A global string-replace on a shared index overwrote a peer's verdict.

**The rule.** No unreviewed bulk replace on documents or shared indexes. Preview the match set (`grep -n` first), and treat any file another session writes to as append-only unless you've coordinated.

## 21. "I didn't see it" is not "it doesn't exist"

**The mechanism.** Three times in one session, an absence was asserted without a command that could have falsified it — and each was refuted by a ten-second check. "These fields have no ticket" (one epic query: three of four did). "This window has been in the code since the initial commit, and nothing explains it" (both halves false: the initial commit hard-coded a date; the rolling window arrived weeks later, and its **commit message stated the intent**, which traced to a regulatory look-back period). The `git log` that had been run answers "which commits touched this file", not "which commit introduced this line" — the first was read as the second.

Worse than the error was what grew on it: an unverified absence became meeting talking points, document options and repeated explanations. Correcting one sentence is cheap; correcting a narrative costs the attention the user already spent on it.

**The rule.**
- **Any claim of the form "there is no X" (no doc, no ticket, nobody knows, always been this way) needs a command that could falsify it, run before the claim leaves.** If you can't name one, write "I didn't find one (not exhaustive)", never "there isn't one".
- **Provenance of a line needs line-level evidence:** `git log -S '<string>' -- <path>` or `git show <first-commit>:<path> | grep`. And **a commit message is documentation** — read the full message (`git log -1 --format=%B`) before saying nothing documents the intent.
- **Before a document goes out, audit its provenance:** tag each fact measured / checked at source / inferred, and downgrade the wording of every inferred one.
- **Don't let an inference grow into a narrative.** Once an unverified premise starts deciding how a meeting is run or a document is organised, it has outgrown its evidence — stop and verify before building further.

## 22. Many-to-many compared one-to-one

**The mechanism.** "Are these records linked by address?" was answered "no — measured", on a low street-match rate. Re-measured properly it nearly doubled, and the conclusion flipped. Two shortcuts, both "treat a multi-valued side as single-valued": each record was compared with **one arbitrary partner** out of many (if the link is "tight core + loose periphery", an arbitrary pick lands in the periphery), and each person's **latest** address was compared, though people move and two records of one person often hold addresses from different years.

The first report had even stated its own caveat ("one partner per record") — and still presented a definite negative.

**The rule.**
- **If either side of a relationship is multi-valued, ask `EXISTS` / `ANY`** ("does any pair match?"), never compare one representative of each.
- Treat any "pick a representative and compare" metric on a fan-out relationship as a **systematic underestimate** unless you can show the pick is independent of the property measured.
- **A caveat must change the conclusion's wording.** A stated limitation followed by an unqualified conclusion is a caveat in name only — the reader remembers the conclusion.

## 23. The counting key is not an identity

**The mechanism.** "Matching by email pulls in N extra records" became "N strangers" and "N contaminated reports" across four documents. The count was `COUNT(DISTINCT <account_id>)`, which answers *how many ids*, not *how many people*. One person with two accounts under one email is two ids. Checked pair by pair, most of the resolvable pairs had identical first and last names — the same person's second account. It was the third occurrence of one family: different surname → different person (it was marriage); different address → different person (it was moving); different id → different person (it was multiple accounts). All three were surfaced by the user's question, none by the analyst.

**The rule.**
- **`COUNT(DISTINCT id)` supports "N records / N ids", never "N people".** Crossing from records to people needs an explicit identity-resolution check, with the criterion stated.
- **Before saying "someone else" / "another person's data", pass a both-names-differ test** (or your domain's equivalent). Otherwise say "records that can't be attributed to the subject".
- **Assume id → person is one-to-many until measured one-to-one.** That one mapping is one-to-one does not make the reverse one so.
- Match the strength of the word to the strength of the test. "Different records" is a measurement; "different people" is a conclusion. Downgrading the word usually costs the argument nothing.

## 24. Reading back your own write is not verification

**The mechanism.** Story points were written to a custom field; the API returned 2xx; a read-back of that field showed the values; "points set" was reported. The board showed them empty. The board reads a **different** field with an almost identical name (the ticket system ships one for each project type). Reading back the key you wrote, by the same wrong name, is a tautology. The user's first guess — "moving the tickets lost the points" — was also wrong, and would have sent someone hunting a non-existent bug.

**The rule.**
- **After writing anything a consumer reads (a custom field, sprint, label, board column, config key), confirm from the consumer's side.** Ask the consumer what it reads (e.g. the board configuration's estimation field), not your own write.
- **"Different from its neighbours" is the cheapest wrong-field detector.** Compare with a similar object you didn't create: if all of theirs populate field A and yours populate field B, you have your answer.
- **A 2xx proves the write was accepted, not that it went to the right place.**
- Don't adopt the user's causal story for a symptom just because it involves the most recent action. Measure first.

## 25. A count changing is not a characterisation of the change

**The mechanism.** Removing a fan-out join cut a field's distinct values by more than half. The difference was written up as "contaminated" and "exposure" in three outward documents. Asked "did removing it also remove correct data?", the values were finally looked at: nearly all of the added records carried the subject's own full name. The worst case's "distinct names" were one name in different casing, with trailing spaces, two typos and a system suffix. A count rise is equally consistent with "duplicates" and "leak"; the more alarming reading was chosen without looking at a single value. And it was a relapse: after the earlier "different ids ≠ different people" correction, the same claim was rebuilt under a new word.

**The rule.**
- **When a field's value count changes, `SELECT DISTINCT` the actual values before describing what changed.** Wrap them visibly (`'<' || col || '>'`) so whitespace and case show.
- **Every qualitative word in outward text ("contaminated", "exposure", "someone else's") needs value-level evidence**, not just an aggregate. Aggregates prove "more", never "whose".
- **A corrected claim that reappears in new words is the same claim** and needs the same evidence.
- When data supports a conservative and an alarming reading, default to the conservative one and go measure.

## 26. A hand-written predicate is a proxy, even when it looks like a read

**The mechanism.** A per-field coverage table comparing two data sources was produced **before** the code defining the field semantics existed, approximating each field with a one-line predicate. For one field, `len(records) > 1` stood in for "the delivered artifact shows a second, distinct value". The two diverge exactly where de-duplication does work — and de-duplication was being added by the same ticket. The real figure was about a third of the published one. The lead cited the table when voting for one source ("it has the most data"), so a wrong number fed a team decision. With the right number, the other source held *more* of that field, which was on a legal deliverable.

**The rule.**
- **A coverage number is a claim about the delivered artifact, so it must come from the code that produces the artifact.** If that code doesn't exist yet, don't publish the number, or label every cell as an estimate and name its predicate.
- Before putting a comparison table in front of anyone, ask per column: **plain field read, or does it pass through transformation logic (dedup, ranking, join, truncation, formatting)?** The second kind can't be hand-approximated.
- The tell: predicates written *for* the table, which nothing else in the codebase agrees with.

## 27. An artifact diff proves only what the harness's call order runs

**The mechanism.** A change made a shared function drop columns on a copy instead of in place. That leaked internal identifier columns into an existing deliverable that was explicitly not to change. The commit's proof was "every output file identical" — a cross-tree diff produced by a sample harness that **skips** the very production step that had been changed. The columns were present on both sides, so the diff was structurally unable to show the regression. True about what was run, false about production. Compounding it: the downstream consumer concatenated frames positionally without naming columns, so "add a column" was a breaking change — visible only by reading the consumer, not the producer.

**The rule.**
- **Before citing an artifact diff, name the production steps it does not run**, and ask whether the change lives in one of them. If it does, the diff is silent, not green.
- When the requirement is "this output must not change", prefer a proof over the **code** (function-level or AST comparison against the base) to a proof over one run's output, and verify the mutated function's real call order end to end.
- **If a shared structure is consumed by something that doesn't name its fields, adding a field is a breaking change.** Give the new consumer its own copy.

## 28. Tests verify behaviour, not claims about behaviour

**The mechanism.** After switching a deliverable's data source, the review documents were regenerated and nearly sent. Reading them first turned up four false statements, all in narrative and per-row notes, not data: "phone is deliberately blank on all rows" printed directly above a table of phone numbers; "no data returned for this request" on most rows, which were fully populated from the new source; after fixing that, "no previous addresses" on rows that had them; and a difference table reporting a column as "gained" when it had merely been renamed. Separately, a count quoted to the user split a semicolon-joined field on newlines. The code was right every time; the description of it was not. Several hundred green tests could not have caught any of it.

**The rule.**
- **A generated document is a deliverable and gets the evidence bar of a conclusion.** Read it end to end before sending, and check every number in the prose against the table beside it — self-contradiction is the cheapest tell.
- When the source or structure changes, **treat every sentence in the report generator as suspect**, not just the code paths.
- **Never describe artifact A with facts derived from artifact B.** (The notes above were computed from the *old* artifact's "no data" files, built from differently-windowed queries.)
- Comparing across versions by column heading breaks on a rename. Before counting items out of a joined field, check the separator the writer actually used.

## 29. A green suite on the branch says nothing about the merged tree

**The mechanism.** (Caught in QA.) A branch's suite was green against the commit it was cut from. The base then gained a shared test-config file that installs mock stubs for a third-party package across the test directory. On the merge result, the same command still went green — but the two tests carrying the core acceptance evidence now **skipped** via an import-or-skip guard, because the stubbed package was "not a package". No file overlap, so both the merge tool and the hosting platform said "clean".

**The rule.**
- **For any PR whose base moved, run the suite on the merge preview** (`git merge-tree --write-tree base head` → `git commit-tree` → a worktree on it), not only on each side.
- **Always run with the test runner's skip report on, and count skips as loudly as failures.** In QA, "N passed" without "0 skipped" is not a number. An import-or-skip guard turns an environment regression into a silent skip.
- A shared test-config file landing on the base is a change to every test on the branch.

## 30. N files, N−1 hand-offs: mutate the hand-offs, not only the ends

**The mechanism.** (QA, author's suite.) A feature spanned a settings gate and a query switch, each with tests that failed under mutation. The one line connecting them — a keyword argument passing the setting into the query at the call site — had none. Deleting it left every test green; any later refactor of that block would have silently disconnected the feature, with nothing red. Tests were written per file touched, so each component proved itself in isolation. A pass-through argument looks too trivial to test, yet it is the only place the feature exists end to end.

**The rule.**
- **For every value a change threads through a call site, there must be a test that fails when that call site stops passing it** (assert on `mock.call_args.kwargs[...]` at the existing call-site test, or an end-to-end check).
- QA checklist: list the hops in the data path, delete each hop in turn, demand a red test each time.

---

## Practical checklist

Before publishing a number:
1. What population is this over? Name it.
2. What does the filter exclude, and which predicates are **verified** vs **assumed**?
3. Did I run it more than once?
4. Does it come from this execution, or am I restating from memory/prose?
5. What instrument produced it, and what is that instrument blind to?
6. If it's a user-facing claim, did I look at what the user sees, with a control in frame?

Before saying "verified":
1. What did I actually **execute or observe** for this?
2. What could my change break that I did not run? (shared state, the enclosing loop, the neighbour, my own commented invariants)
3. Does each new assertion have a demonstrated failing input?
4. Does the claim's evidence type match the claim's domain — data/runtime/organizational?
5. If it's a write someone else reads, did I confirm it from the consumer's side, not by reading back my own key?
6. If the base moved, did I run the suite on the merged tree, with skips counted?
7. For each hand-off the change threads through, does some test go red when it is removed?

Before sending a generated document:
1. Did I read it end to end, and does every number in the prose agree with the table beside it?
2. Is every claim derived from the artifact it describes?
3. Does every "there is no X", "another person", or qualitative word ("contaminated") have a falsifying command or value-level evidence behind it?
