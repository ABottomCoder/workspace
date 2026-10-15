# Reviewing Someone Else's PR

> The full protocol for reviewing a PR written by someone else: how to frame it, where findings actually live, the evidence gate a finding must pass before it reaches the PR, how to write the comment, and how to re-trigger the static scanner. Read this whenever the user asks you to review a PR. Git host, org and scanner come from `business/<co>/stack.md`; `<angle-bracket>` names below are those slots.
>
> Output goes to the PR's ticket dir, `business/<co>/tickets/<ID>/reports/review-r<n>.md` (no ticket: `tickets/pr-<repo>-<n>/`). Nothing is posted until the user chooses (rule 34).

**Trigger:** the user gives you a PR URL (usually forwarded from chat or the ticket system) and asks for a review.

**Calibration cases used throughout.** Two real reviews validated this ruleset and are cited by neutral label:
- **PR-A** — a Python data-service PR (batch job + SQL generation + spreadsheet output).
- **PR-B** — a Node/TypeScript API PR (auth/SSO, env schema, request validation).

Both are de-identified; only the mechanics are kept, because a rule without its why gets dropped by the next team.

**What this optimizes for.** The static scanner (pluggable, see [multi-agent-harness.md](multi-agent-harness.md#static-scanner-interface)) does a static pass over the diff; a careful human reviewer covers design, naming, and readability. Two things are yours to add: **executing the claim** and **verifying assertions about systems outside the repo** — measured on PR-A and PR-B, every finding you contribute tends to come from one of those and none from reading the diff and forming an opinion.

But depth alone is not enough. Audited against a thorough human review of the same PR, an execute-first approach found 4 of 11 substantive findings; the six lenses in Phase 2 exist to cover the rest, and three of them (L1, L2, L3) are **mechanical passes that do not depend on intuition at all**. Run the matrix first, then go deep on what it surfaces. Track the hit rate in the [coverage regression table](#coverage-regression-table--how-this-file-gets-better) and add a rule for every miss.

**Basis for these rules**
- A tech lead's original guidance: run a second AI pass layered on the static scanner's, additive critique rather than restatement.
- Your company's own peer-review / AI-review policy page, if it has one — that is where the **blocking-comment definition** reused in Phase 4 came from.
- [Google eng-practices](https://google.github.io/eng-practices/review/reviewer/looking-for.html) — `Nit:` prefix, do not block on style alone, state which parts were reviewed.
- [Conventional Comments](https://conventionalcomments.org/) — label + `(blocking)`/`(non-blocking)` decoration vocabulary.
- A senior human reviewer's review on PR-B — severity + lens labels, `Question (High if confirmed)` for out-of-repo dependencies, `suggestion` blocks, explicit severity and causality notes, re-review as a thread→verdict table. Worth copying. The two costs of that style are also instructive: 3,400 words across 18 comments, and pushing the biggest item's verification to the author instead of checking the deploy repo himself.
- Our own runs on PR-A and PR-B, which is where the Phase 3 gate comes from.

---

## Phase 0 — Frame it before reading any code

1. Record `head SHA`, base branch, `state`, `mergedAt`, `reviewDecision`, `mergeStateStatus`. A PR can merge mid-review; if it merges, findings become a follow-up ticket, not a PR comment. For a `hotfix/` or `release` head, also check the base against the [branching model](branching-and-merge.md) and the current drift between the integration branch and the production branch (`git log --oneline main..<integration-branch>`): a hotfix merged into the integration branch only ships with the next release, which decides when the fix actually reaches users. Confirm the PR title/branch carries its ticket key, and search the ticket system when it does not; one hotfix PR had no key while its ticket existed and a precedent PR for the same fix had gone straight to the production branch.
   - **Release PRs:** read the team chat for in-flight fixes to shared libraries, and state in the review which ones this release does and does not carry. One release pinned a shared-library version older than the one a parallel incident fix depended on.
2. **Read every existing review body AND every inline comment, including resolved ones.** Not just the review summaries. On PR-B the reviewer first read only the three review bodies and skipped the 18 inline comments; the single finding that got filed came from a wrong premise inside one of them. Forming your own opinion before reading theirs wastes the whole point.
3. **Compute review staleness.** For each review, compare `commit_id` against head, and list the commits **nobody has reviewed**. Put the effort there.
   Example on a GitHub-compatible host (use your git host's equivalent API):
   ```
   gh api repos/<org>/<repo>/pulls/<n>/reviews --jq '.[]|"\(.user.login) \(.state) \(.submitted_at) \(.commit_id[0:8])"'
   ```
   Real cases: PR-A's newest scanner review was against a commit that had been force-pushed away (`git fetch origin <sha>` still retrieves it, so the delta is diffable). PR-B's scanner review was 4 commits behind head, and the human `CHANGES_REQUESTED` predated the head by one commit. A "No issues found" comment gives no hint of this.
4. Read the ticket's AC **and the author's own stated merge gates.** PR-A's "we also need to give a sample report to legal before merging" was a ticket comment by the author, not in the PR at all. Then check each AC item against the diff: an AC the PR silently drops, with a "follow-up" ticket that turns out to cover only merge and deploy, is a scope cut nobody recorded. Report it as that (with a causality note, rule 25), not as a defect.
5. **Read PR activity for intent before acting on it, and never infer intent from a string match alone.** A comment that happens to match a known bot trigger is usually just English. Check the timeline and the author's own history first: review re-requests (`/issues/<n>/timeline` filtered to `review_requested`), current `reviewRequests`, `@`-mentions, and whether that person has ever used that command in this repo.
   - Miss to avoid (PR-B): the tech lead's `review please!` was read as a misfired scanner trigger. The timeline said otherwise — he had re-requested a human reviewer 1h17m earlier, both reviewers were still requested, there was no mention or scanner syntax, and `review please!` appeared exactly once in the repo's entire comment history while the command actually used in that repo was `@<scanner> review full`. He was nudging his two human reviewers. Telling him his command was wrong would have been both incorrect and condescending; only [rule 34](#phase-5--write-it) (report to the user before posting) kept it off the PR.
   - The staleness of a bot's last review (rule 3) is a separate, still-valid fact regardless of what any comment meant.
6. Check working-directory state of any repo you will touch, and prefer `git worktree add` over switching the user's branch.

## Phase 1 — Baseline, before any hunting

7. **Run the test suite on both the base branch and the PR head.** Report both numbers. Identical results mean the PR introduced nothing; differing results mean a real regression. Without the base run, pre-existing failures get misattributed to the PR (this happened on an earlier PR in the same repo as PR-A: two failures looked like the PR's, were the base branch's, and the true cause was a stale gitignored artifact).
8. Run the stack's type-check / lint on head (`tsc --noEmit`, etc.), and verify the author's own claims about the suite rather than repeating them.

## Phase 2 — Hunt: six lenses over the touched surface

**Hunting and reporting are separate activities.** Phase 3's evidence gate decides what you *post*; it must not decide what you *look at*. Applying it during the hunt is the mistake that cost the most: measured against the senior reviewer's 18 comments on PR-B, an evidence-first hunt would have surfaced 4 of his 11 substantive findings, and 5 of the 6 it missed were exactly the leads you cannot execute up front. Collect leads freely here; filter in Phase 3; unexecutable leads become Phase 4 questions rather than being dropped.

**Do this as a matrix, not from memory.** Build the list of touched files and routes, then walk **every lens over all of them**. Pattern-matching from a list of remembered shapes is what produces a 40% hit rate.

9. **The diff tells you what changed; the findings live in what the change reaches.** For every changed default, constant, signature, schema, or removed branch: grep every call site and ask *is this path still reachable, and what feeds it at runtime?*
10. **Cross-boundary rule.** For a schema or contract change, read the **producer's** code, not only the consumer's — usually in another repo. This is how PR-B's candidate findings got resolved or killed: the upstream service's result serializer really does return `email` (harmless, consumer takes it from params); a sibling service's `pending_reason` can never reach the wire as `null`; the shared library's item-creation module writes `"type"` unconditionally, so a required `tasks[].type` is safe.
    - **Replay the producer's exact code with its own library version, not the contract it declares.** A producer whose API schema said "list of strings" was, in fact, reading a spreadsheet with a CSV reader that inferred `float64` for an all-numeric column with one blank cell, so every phone number arrived as `"<digits>.0"`; the consumer's new parser then emitted a number that never matched the stored form. Only running the producer's real read path with its pinned library showed it.
    - **Read the other side at the version that is live**, not the integration branch. A consumer whose production build still had a strict schema without the new field meant deploying the producer first would turn every affected row into a `400` (deploy-order coupling, also L6).
    - **For infra, "who reads this" is the cross-boundary check.** A bucket policy granting only the writer, with no principal for the stated consumer, is a Question when the consumer lives outside the repo. For a cross-account grant, read the **grantee's** identity policy as well as your resource policy and intersect both with what the consumer's docs require; one KMS key-policy grant was inert because the bucket's default encryption was not KMS, the writer set none, and the grantee role's own policy listed no KMS keys. Follow the trail to the consumer's actual IaC and diff names/ARNs against yours, not against the ticket prose (one ticket dropped a suffix the code kept).
    - **Read the producer of every tag, key, or path a resource filters on**, and diff the literal strings against the chat/ticket agreement. One lifecycle rule filtered on tag `retention` while the writer tagged `retain`: nothing would ever have expired.
11. **Out-of-repo assertion rule.** When the author or a reviewer closes a thread by asserting something about a system outside the repo — deploy manifests, the secret store, upstream response shapes, client behavior — go check that system. Both PRs' largest findings came from here. On PR-B, "every deploy manifest sets these three env vars" was contradicted by the deploy repo, where the only env keys ever committed under `values/` were two unrelated ones (`git log -S <var>` returned 0 commits for all eight claimed vars).
    - **Follow the caller's real identity path end to end.** A principal in a resource policy is only reachable if some identity the caller actually holds can assume it: read the caller's connection config (which role it assumes), that role's trust policy, then the granted role's trust policy. One PR granted access only to a role the job's worker had no trust path to, while the static scanner listed "reusing the existing role" as a strength.
    - **Walk grant hierarchies to the object, do not filter.** In a role-based warehouse, listing a service role's direct grants filtered to the object name proves nothing; access may arrive two parent roles up. Walk each granted parent role (and list who holds each one) until the object's grantee list is reached.
12. **Resolved-thread audit.** Specifically re-check threads closed on a *premise* rather than on a code change. A wrong premise in a resolved thread is the highest-value target precisely because everyone has stopped looking at it.

### L1 — Tolerance delta: what used to be accepted and now is not <!-- MANDATORY mechanical pass -->

13. For **every** validation, guard, enum, type, or required-field added or tightened: enumerate the input set the old code accepted and the new code rejects, then check each rejected shape against a real producer or caller. This is the single highest-yield lens and the one that keeps getting skipped, because the natural instinct is to hunt for inputs that *break* the code rather than inputs that *used to work*.
    - **It is usually executable.** Feed the real old-accepted inputs to the new schema and list which now fail — exactly the env-schema probe that produced PR-B's env finding (`.env.example`, the local compose file, and the deploy chart's env block → 6, 8 and 8 boot failures respectively; `.env.test` was the only passing source, which is why 404 green tests saw none of it). Generalize that probe; do not treat it as a one-off.
    - **For allowlists and enums, enumerate the real member set from the deploy config, not from the code.** An allowlist that omits a live origin silently discards legitimate traffic.
    - **On auth paths this lens is High by default.** The failure mode is locking out valid users or looping them through SSO, and no test can see it. Ask specifically: can the IdP emit this claim as an array, a non-RFC address, or a single string instead of a list?
    - Known members of this class: `.optional()` where the wire value can be `null` (zod `.optional()` rejects `null`; `.nullable()` is needed); an enum replacing a deliberately permissive "anything else → default"; a MIME allowlist newly applied to routes that only checked presence; `.min(1)` on an array that used to accept empty; a config var promoted to required at boot while its in-code fallback is deleted.
    - **For parser swaps, make the two-branch table the default harness.** When a PR replaces a list of formats with a parser (or one validator with another), run every fixture shape plus edge shapes through both worktrees and diff the columns. It is cheap and decisive: one such probe showed the only shapes the new code dropped were leniencies of the old one that no fixture or producer used, so there was no finding and the review could say so with evidence.
    - **Normalization against the real stored member set.** When a PR normalizes input before matching (case, separators, whitespace), enumerate the stored literals from the producer's code, then execute both spellings. One normalizer stripped `-` and `_` but not spaces, so a status written with spaces around a dash never matched (0 rows vs 1).
    - **Enumerate the real input shapes, not the documented ones.** Spreadsheets strip a leading `+`, drop leading zeros, and turn blanks into `NaN`; a number with a country code but no `+` only expands correctly when the side-channel country happens to match.
    - **Blank values on a new optional filter.** For every new optional filter param, execute the blank / empty / whitespace value and ask whether "no filter" is the safe default. On an owner- or tenant-scoping param, a blank that parses to "filter inactive" returns every user's rows with a `200`: a data-exposure lead, not a convenience (blast radius per L6 is every consumer of that scope).

### L2 — Response contract diff: what the caller sees <!-- MANDATORY mechanical pass -->

14. For every touched route, tabulate **status code + body shape + error message** before vs after, and account for every difference. Mechanical starting point: `git diff base...head | grep -E '^-.*(error|message|status\()'` — every deleted user-visible string is either still reachable or it is a contract change.
    - Watch for: actionable messages collapsing into one generic string; a field name or path disappearing from an error so the client can no longer tell *which* input was wrong; a status code flipping (`200 {totalCount: 0}` → `400`); per-item errors becoming a whole-batch rejection.
    - Consumers to check: the web client, scripted/`curl` callers behind API auth, and any other service. "Today's UI ignores the body" makes it a DX regression rather than a user-visible one, which is exactly why it goes unnoticed.

### L3 — Observability delta

15. For every metric tag, log line, or error string that the change touches or makes newly reachable: **is the label still true for every case that now reaches it?** And for every new rejection or throw: does anything get logged so on-call can diagnose it?
    - `reason: 'email_empty'` emitted for inputs that are malformed rather than empty will mislabel a dashboard silently until an incident review.
    - A validation that rejects and returns without logging turns a support case into "users bounce between `/login` and `/saml` with zero signal". Log the failing **paths**, never the values.

### L4 — Guard efficacy: can this check see what it claims to prevent?

16. For every new validation, read what executes **before** it on the same data path and ask whether that earlier code can already neutralize the bad input. Then ask whether the guard's condition can ever be false in production at all.
    - `res.json().catch(() => ({}))` upstream of a new parse: `{}` satisfies an all-optional schema, so the malformed-upstream case the parse was added for still reports as "user not found".
    - PR-A: a skip-guard on `not (phone_numbers or email)` where `email` is always the request email, so the branch is unreachable and the expensive warehouse task runs for every request. The static scanner praised this guard as a strength in three consecutive reviews.
    - Also here: a de-dup or projection key missing the field that distinguishes real rows (a "non-empty projection" helper that omits the row id); hand-rolled escaping where the engine has its own escape character (an `_escape` doubling quotes while the SQL engine treats `\` as an escape); a schema that strips undeclared keys sitting on a payload that gets forwarded.
    - **Body-parsing defaults are the usual neutralizer.** A new "non-object JSON body → `400`" guard never saw `[]`, `0`, `false` or `""` because `get_json(silent=True) or {}` ran first and turned every falsy body into `{}`. Use the PR's own docstring / in-repo docs as the test oracle: execute every shape the claim says it covers.
    - **Library type inference sits upstream of your parse.** A CSV/dataframe reader with no explicit dtype infers `float64` for a numeric column with one blank, so `str()` appends `.0` and drops leading zeros, and `str(NaN)` becomes the literal `'nan'`. A fix commit that handled `isna` still missed the `.0`. Probe any parse of tabular input with a column that has both a value and a blank.
    - **A test is a check, so it gets this lens too.** For every new test that pins a behavior, ask whether its fixture is a state production can actually produce, and whether the test would fail if the code broke. PR-A's three new tests asserted a skip-guard fired, but only because they set `mock_ids.email = ""` on a Mock while constructing the user object with `email="test@example.com"` — a state the real identifier lookup cannot return. Green tests over an impossible fixture are the strongest possible camouflage for an unreachable branch. When the fixture pins a data value (a service name, a status, a country), one `GROUP BY` on the real column usually settles it: one test asserted a per-row label the production column never held (every row carried the parent brand's value). A test that avoids a hazard by omitting the column is the same failure.

### L5 — Control flow and failure routing

17. For every new `throw` / reject / early return, trace where it lands: which `catch`, which status code, and what the client or browser does next.
    - Loops: a rejected token plus `failureRedirect: '/login'` sends the browser to SSO, which reissues the same claims, which fail again.
    - CrashLoops: a parse or read at module load exits the process before it can serve, and no test or CI job can see it.
    - Misrouted errors: a generic `Error` where the caller only swallows one named class becomes a `500` on a path that used to answer `404`.

### L6 — Blast radius and coupling

18. Does a change scoped to feature X take down Y? Look for shared config, shared queues or warehouses, and newly-unconditional calls added to a common path.
    - Requiring a feature-specific token at boot takes the two unrelated features on the same service down with it.
    - `fetch_phone_number=True` on the shared identity lookup makes an upstream round-trip mandatory for every request, including users the feature does not apply to.
    - Reusing an allowlist built for a different decision (the cookie `secure` flag) as a redirect allowlist couples two unrelated concerns and guarantees drift.
    - Deploy-order coupling: a producer and consumer that must ship in a specific order, where the wrong order rejects live traffic (see rule 10, "the version that is live").
    - A second writer: a platform auto-remediation bot that rewrites tags or lifecycle settings on a resource your IaC also manages shows up as permanent drift. Check the plan's drift section before calling a "to change" count noise.

### Surface-specific passes

The six lenses are surface-agnostic. Three PR types have extra mechanics that the lenses alone kept missing:

- **IaC PRs: read the speculative plan, not the diff.** Any destroy or change the diff does not explain is the finding. A "pass" check that says "1 to destroy" is not a pass. Then open the workspace's **current** run list and its last apply log: workspaces get locked by runs pending confirmation for months, and one resource stayed in state across several PRs because every apply errored on it after creating everything else. Do not trust "the author said they'd fix the state"; re-open the run list. A resource can be live and configured while the workspace has never had a green apply. This is deployment risk (rule 23).
- **IaC PRs: map every API call the consumer makes to the permission it needs.** A policy copied from a sibling resource covers the sibling's calls, not this one's. One bucket policy granted `PutObject` while the writer uploaded with tags, which also needs `PutObjectTagging`.
- **Release PRs: for every new image or build artifact, find the deploy definition that consumes it** (deploy repo tree, open PRs, branches). A built-but-undeployed artifact means the feature did not ship; one "companion PR" named in a feature PR pointed at a deploy repo that did not exist. File it as a Question to the feature owner, not as a defect of the release.
- **Matching or validation against a warehouse table: profile the column first.** Shape by length/prefix, null share, candidate validator columns. Count-only aggregates read no PII and take minutes, and one such profile reframed a whole review: the column stored bare national numbers, a "country code" column was empty on every row while another was populated and consistent, so every real hit was a "stripped" match the PR treated as an edge case. Read [data-verification.md](data-verification.md) for the query discipline.
- **Scan-window narrowing using another system's field: profile the field and the target's date range before accepting it.** One PR started a per-year scan at an account's join year taken from a different system; count-only queries showed activity years before most recorded join dates, so a wrong join date would silently truncate a data-subject report. Filed as `Question (High if confirmed)`. The ticket had asked for the full range; the optimisation was the author's. The cost of being wrong (an incomplete regulated response) dwarfs three extra queries.

## Phase 3 — The evidence gate (hard, and only for what you post)

A finding may reach the PR only when **all four** hold. This is [Evidence Before Conclusions](../principles/evidence-and-ask-gate.md) applied to someone else's code, and it is the rule that keeps a correction from being overturned in public. It governs Phase 5 output only — never use it to narrow Phase 2.

19. **Executed.** You ran the smallest harness that demonstrates it. Stub only the outermost boundary (`globalThis.fetch`, the DB cursor, the env dict) and keep everything else real code. Reading the code is a lead, not proof.
20. **Controlled.** You ran a near-identical case differing only in the suspected variable, and it behaves differently. PR-B's finding was not safe until controls `{data:{},errors:[…]}` and `{data:{identity:null}}` both came back unchanged on both branches, which is what ruled out your own stub as the cause.
21. **Before/after.** The same input executed on base and on head. That is what proves the PR caused it, and it is also the most persuasive two lines in the comment.
22. **Unproven links named.** Any step you could not execute goes in the comment in your own words, before anyone asks. On PR-B: "I did not catch the upstream API emitting `data: null` myself, so the trigger is still the one you described."

A finding that fails 19–22 becomes a Phase 4 question. It does not get silently dropped, and it does not get softened into a claim.

## Phase 4 — Classify before writing

23. **Blocking only for these four** (from the internal peer-review policy's definition): functional defect, security concern, deployment risk, compliance violation. Everything else is non-blocking. Do not block on style alone.
24. **Questions are a first-class output, not a fallback.** When a lead depends on knowledge you genuinely cannot reach — what the IdP emits, which clients call a route, what a manifest sets — file it as `Question (High if confirmed)`, state the blast radius if confirmed, and state what would settle it. Prerequisite: you must have tried to answer it yourself first and say what you checked. Pushing unexamined verification to the author is how PR-B's biggest item got closed on a wrong answer with nobody checking.
25. **Causality note on every finding:** did the PR *introduce* this, or does it merely *not fix* it? Never let a pre-existing issue read as a regression.
26. **Low-severity items are allowed, but bounded.** Cap at ~3 per review, and only when the item is (a) in a file this PR introduces — those files are the convention future readers copy, so their header docs, placement, and latent footguns are in scope — and (b) fixable in a line or two. Label them explicitly: `Low · latent by construction — flagging for the next schema, not for this PR`. Consolidate doc/placement/naming nits into **one** comment rather than one thread each.
27. **Still drop:** style preferences, anything already covered by another reviewer, and anything you would honestly label "buys nothing" outside a file this PR introduces. Reviewers who dump every nit get ignored.
28. Escalating or de-escalating someone else's severity is fair game when you have evidence they lacked. PR-A: the scanner filed the inline-SQL escaping as a *suggestion* on the grounds that quote-doubling covers the standard vector; executing it against the real SQL engine showed the predicate matching every row, which makes it blocking. It works the other way too, and for performance claims **measure before you agree**: a scanner "Important" that a type scan before a size cap was an O(n) DoS took one timing run to settle (a million-element body parsed in milliseconds, and no request-size cap existed anyway), so it was de-escalated to a nit.

## Phase 5 — Write it

29. One finding per thread, anchored to **the line that must change** on the current head. When correcting or extending someone's thread, do not reply into it if that thread is outdated: reference it by comment id instead (`follow-up to r654757`) and anchor the new comment where the fix goes.
    - **Check before posting a reply:** an old thread anchored to a line that later commits touched is `isOutdated`, and the git host hides outdated threads behind "Show outdated" in the Files changed tab, so the user may not see the comment at all. This happened on PR-B: a reply landed on `identityClient.ts:44` with `position: null` and had to be re-anchored to `schemas.ts:59`.
      Example on a GitHub-compatible host (use your git host's equivalent API):
      ```
      gh api repos/<org>/<repo>/pulls/comments/<id> --jq '{position, line}'      # null => outdated
      gh api graphql -f query='{repository(owner:"<org>",name:"<repo>"){pullRequest(number:<n>){
        reviewThreads(last:25){nodes{isOutdated isResolved path
        comments(first:1){nodes{databaseId author{login}}}}}}}}'
      ```
    - After posting, confirm `position` is non-null. A published comment is not necessarily a visible one.
30. Shape: **claim in one sentence → mechanism → one-line evidence → fix.** Target under 80 words, hard cap ~120. The standing preference is short; a wall of text buries the finding.
31. Paste the executed before/after as a short code block. Evidence beats adjectives.
32. No em dashes. No "Great catch", no praise padding, no restating the PR description. English, per [communication.md](../principles/communication.md). Tone and message-form rules are shared with every other channel (see [How to ask](../principles/communication.md#how-to-ask)): neutral, colleague-to-colleague, no blame, short enough to read at a glance.
33. Use a ```suggestion block when the fix is a line or two, so the author can apply it directly.
34. **Report to the user first — ranked, with the kill list — and post nothing until they choose.** Never submit `APPROVE` / `REQUEST_CHANGES` without explicit confirmation; that decision is attributed to their account.

## Phase 6 — Efficiency guardrails

35. **Time-box every external dependency to ~5 minutes.** If an MCP call, a remote warehouse, or a CI job has not answered, switch to a local execution route and label the evidence accordingly. On PR-A a remote warehouse statement sat `PENDING` for ~50 minutes while a local engine run answered the same question in three, and the local run was the stronger evidence anyway because it was reproducible.
36. Smallest harness first: real module with a stubbed boundary > booting the app > building a container. Node can run `.ts` directly (`tsx`, or node's type stripping); Python modules can be imported straight from a worktree.
37. Do not re-derive what the static scanner or a human reviewer already established. Verify their conclusion only when a decision depends on it.
38. Clean up at the end: remove worktrees and temp installs, and confirm the user's repos are on their original branch with a clean tree.

## Deliverable to the user

39. Ranked findings, each labelled verified / partially verified / question, with the executed evidence inline.
40. **The kill list is part of the deliverable.** "I checked these six things and they are clean" is what makes the remaining one credible. On PR-B six leads were dropped after checking (a sibling service's field nullability, a missing enum catch-all, a forwarded-list schema strip, a redirect helper's CRLF handling, a serializer stripping `email`, a field that was already required) — none belonged on the PR, all belonged in the report.
41. State plainly what you did **not** check (no deployment, no live upstream, docs unreachable), so the user can judge coverage.

---

## Coverage regression table — how this file gets better

This ruleset is validated against real findings rather than assumed to work. **After every review, add a row per finding — yours, the static scanner's, and every human reviewer's — and name the rule that would have caught it. A finding with no rule is a gap: add or sharpen a rule, then record it here.** This is the maintenance loop; the phases above are only as good as this table.

Generic rules learned here go into the phases above; the accumulated per-business rows go to `business/<co>/docs/pr-review-coverage.md`, not this file. One example row is left in to show the shape: mark with ✚ any finding the ruleset would have **missed** before you added the rule, so the gaps stay visible.

| # | Finding | Lens / rule that catches it |
|---|---------|-----------------------------|
| ✚ | *(example)* strict `email`/`roles` claim schema can reject valid sessions | L1 (auth sub-rule: can the IdP emit this claim as an array?) |
|   |         |                             |

**Known residual gaps** — no rule covers these yet, so they stay on the radar rather than pretending to be solved:
- **Design and architecture.** Deliberately out of scope: a human reviewer covers it better and you would be guessing. If a PR is primarily an architectural change, say so to the user up front instead of pretending the lenses cover it.
- **Concurrency and ordering.** Neither calibration PR exercised it, so there is no calibrated rule. When a PR touches locks, queues, retries, or parallel writes, flag the gap rather than improvising.
- **Performance and cost at scale.** PR-A's "a warehouse query per request for 100% of requests" was reasoned about, not measured. No rule turns that into evidence yet, beyond rule 28's "measure before you agree" for a specific claim.

The L1/L4/L6 sub-rules, the extra cross-boundary bullets under rules 10 and 11, and the [Surface-specific passes](#surface-specific-passes) all came out of ✚ rows in the original table: that is what the loop looks like when it works. Expect your own table to grow rules for whatever surfaces your team ships (IaC, release trains, data pipelines).

## Static-scanner triggers — expect TWO wiring paths, taking DIFFERENT commands

The static scanner is pluggable (see [multi-agent-harness.md](multi-agent-harness.md#static-scanner-interface)). Whatever tool fills the slot, the same trap applies: **the same scanner is often wired into different repos by different mechanisms, and the re-trigger command is not the same on both.** Check which path a repo uses **before** trying to re-trigger. Tell them apart by listing the repo's CI workflow definitions (e.g. `.github/workflows/` on a GitHub-compatible host): a code-review workflow means the CI-workflow path; no workflow but scanner comments present means a forwarded-webhook / hosted-bot path.

**Path A — CI workflow in-repo.** A shared code-review action runs on `pull_request: [opened, reopened]`, `issue_comment: [created]`, `workflow_dispatch`. To re-run manually the PR comment must be **exactly the action's trigger phrase** — the action string-compares and skips anything else. In the reference implementation, the `@<scanner>` mention did NOT work on this path: it fired a run that exited success in ~55s having logged `Comment "@<scanner>" is not equal to the trigger phrase "<phrase>", skipping`. **A green run is therefore not evidence a review happened — confirm a new review comment appeared.**

**Path B — forwarded webhook / hosted bot.** No in-repo workflow and no scanner config file; reviews are posted by a bot account. Here the comment command form (`@<scanner> review full`) is what works, verified by a new review against the current head appearing ~5 min after the comment. So the trigger phrase is Path-A-only and the two paths genuinely take different commands. The rest of the mechanics below are read from the reference scanner's source and are the shapes to re-verify against whatever tool you plug in:

- Reviewable PR actions were `['opened', 'synchronize', 'reopened']`. **`ready_for_review` was absent, so taking a PR out of draft did NOT trigger a review.**
- `synchronize` (i.e. any push) was **skipped unless `reviewOnPush: true`** in the repo's scanner config, and the default was `false`. With no config file, **pushing commits never re-reviews** — the review stays pinned to the commit at PR-open time.
- Comment commands: `review` (incremental if a prior review exists), **`review full`** (force full review from base — the right one when the prior review is many commits stale), `review focus <area>`, `describe`, `feedback <signal> [findingId]`, `help`.

**Always check the review is not stale before trusting it** (Phase 0, rule 3). On one PR the scanner's "No issues found" was submitted against a commit **25 commits and 1,690 insertions behind** the head — it had reviewed none of the PR's actual content.

**Worth proposing per repo:** a scanner config with `reviewOnPush: true` (or the equivalent) removes this failure mode permanently.

Notes: **no git MCP needed** — the git host's CLI or API is enough for everything above; see [mcp-and-cli.md](../reference/mcp-and-cli.md). And skip the "second *model*" framing from the original guidance: if policy forces a single model family and the static scanner runs the same family anyway, what you gain is **failure-mode diversity** (static analysis vs. an agent that executes tests), not model diversity — same rationale as [multi-agent-harness.md](multi-agent-harness.md).

---

## Worked calibration examples

Two findings that passed the Phase 3 gate, as a reference for the bar and the comment length.

**PR-A — a guard that can never fire.** `user.py:115` gated an expensive warehouse task on `not (self.ids.phone_numbers or self.ids.email)`, but the identifiers object's `email` is always the request email. Proof was running the real merged identifier lookup with the upstream returning no phone numbers: guard `False`, task scheduled. The three new unit tests passed only because they set `mock_ids.email = ""` on a Mock while constructing the user with `email="test@example.com"`, a state production cannot produce. The static scanner had praised the guard as a strength in all three of its reviews. Posted as 24 words.

**PR-B — `.optional()` where the wire value is `null`.** The identity response schema's `data` field was `.optional()` but not `.nullable()`, so a GraphQL `{data: null, errors: […]}` response threw instead of degrading. Base returned `404 "User not found"`; head returned `500 "Internal Server Error"`; controls with non-null `data` were unchanged on both branches. The trigger condition was one an existing thread had already contemplated, so the comment corrected that thread's premise and said plainly which link was unobserved. Posted as 62 words.
