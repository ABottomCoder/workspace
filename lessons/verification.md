# Verification

How to prove a change, fix, measurement or claim is actually true before reporting it: choosing checks that can fail, testing the real path, and reading evidence correctly.

### Before "done", list the paths the change touches and test the unhappy ones
**Mistake:** Reported features and fixes done after a happy-path self-test; the reviewer or users then hit what was never run: a reload that re-inserted chat messages, the second visit after skip/restore, another tenant's data, a stale connection cache, one exit path of several (billing added on success only), a transient zero in a field assumed final, a long title, a first-display path, a partial test pass after "test the full feature". About 15 such errors over five months.
**Root cause:** "It worked when I tried it" was taken as "it works"; the set of states and paths was never written down, so only the one the author happened to walk got tested.
**Rule:** Before saying done, write a short list in the ticket: every entry point, exit path (success, error, early return, cancel), state transition (first time, repeat, reload, resume, after undo), actor (other user, tenant, role) and input edge (empty, long, zero, missing, non-default) the change touches, plus what the change could break nearby. Run each item, or mark it explicitly untested in the report. When the user asked for full testing, the list is the scope and "done" means every item ran.
**Seen:** 15

### A negative only covers what the search could see
**Mistake:** Asserted "there is no such feature", "never version-controlled", "newly introduced", "count is 0" and "the service does nothing on start" after searching one repo or layer, one entry file, a scan that never reached the relevant state, a counter that one path bypassed, a fresh-context harness that cannot see caching bugs, or a grep piped through `head` whose real hits were past the cutoff. All were false.
**Root cause:** The coverage of the search (repo, layer, state, path, output window) was treated as the full state space, and "my search lacks it" was reported as "it does not exist".
**Rule:** A positive claim needs one hit; a negative needs every plausible location: all repos, sibling and legacy modules, writers as well as readers, every entry point (action x entry point x validated x counted), the whole built tree for named starters (`start*`, `register*`, `schedule*`). Absence searches never use `head`/`tail`/`-m`; use `grep -c`/`-l`, and never print an interpretation label next to a truncatable pipeline. Confirm the test you rely on exercises the thing, and know your harness's blind classes. Say "not found in <places searched>" instead of "does not exist"; when someone says "we built that", treat it as a hint where to look.
**Seen:** 10

### Deployment proof is not fix proof: confirm the new code runs, then the behaviour
**Mistake:** Declared fixes done because a deploy "succeeded" or a new bundle hash was live, while production ran old code: only a no-emit typecheck ran so stale compiled output shipped; only changed files were copied so a sibling module lacked a new export; a tarball packed at the wrong level put new code beside the entrypoint; a prompt was updated at its source path while the runtime read another copy; a worker fix was tested against a still-old worker; an endpoint shelled out to a binary missing from the image, with errors swallowed into "200, no changes".
**Root cause:** "Exit 0, health OK, my code is deployed" was conflated with "the new code runs and the bug is gone". Multi-service deploys are not atomic, and tests that import the app cannot see Dockerfile or compose lines.
**Rule:** Sequence: edit, full build, deploy the full build output (or every module the change touches), restart long-lived readers. Identify the exact file/process the runtime loads and observe the carrying component's version directly (image tag, build-info endpoint, process start time, the most specific new symbol grepped in the deployed artifact). For a 404 on a just-added route, check the entrypoint unit and the package layout first. Keep one copy of code per host. Add a test that reads the Dockerfile/compose for required binaries, env vars and mounts. Then reproduce the original user steps on the real environment (hard-refreshed browser click for UI, the triggering request for backend) and confirm the outcome.
**Seen:** 9

### Choose criteria that read differently when the bug is absent, and calibrate them on the broken state
**Mistake:** Several checks in one investigation (a scroll-width gap, "an input exists", walking ancestors, "the value is large", `git log` in a non-repo printing nothing read as "0 commits", grepping a string that also sat in one's own comment) returned the same reading whether or not the bug existed, and sent the fixer in wrong directions.
**Root cause:** Criteria were chosen for convenience and to confirm an expectation, not for discriminating power, and were never seen reading the faulty value.
**Rule:** Before measuring, write down the expected value in both worlds (bug present / absent); if identical, pick another criterion. Record raw numbers in the failing state first (ideally before deploy) so verification is a comparison; if no baseline is possible, say so. Measure the thing by its own identity (its unique selector, the CI command, bytes on disk), not a neighbour or page aggregate. Know the variants: zero/empty is a value, not an absence (make failure return null or throw, never 0); a check can match your own fingerprint (strip comments, inherited state); a current-state source cannot answer a then-question (use append-only sources: audit logs, git, event payloads). Before calling a value a defect, ask whether it is actually wrong.
**Seen:** 6

### Drive the test through the real entry point and the layer where the fix lives
**Mistake:** A login challenge was tested by curling the API (the frontend's request wrapper turned the 401 flag into a generic error, so real logins failed); a tour was triggered by a manual event real signups never fired; a chat bot was rehearsed by calling its handler directly; a frontend-handler fix was "verified" through the API, which bypassed it and looked unfixed; a two-step email-code flow was tested by injecting the code into the DB, hiding that codes were never sent; an audio input was "working" per a capture tool while the real consumer read only one channel.
**Root cause:** Convenience triggers (curl, dispatched events, direct handler calls, DB writes, substitute probes) skip the seam where the bug lives.
**Rule:** Locate where the change lives and pick a driver that executes it: frontend handler means click the real control; server route means the API is fine; worker/agent means a real turn. Trigger it the way a real caller does (real form, signup, webhook, every input channel) and run both halves of multi-step flows for real (e.g. email dispatched with a provider message id). Pass conditions come from the real consumer's own behaviour. "Needs another step" responses should be 200 + flag, not 401/403. If verification shows "no change at all", suspect a bypassed layer first; label anything not tested end to end as unverified.
**Seen:** 6

### Before trusting an empty or negative result, prove the check can find a known positive
**Mistake:** Read 404s on misspelled routes as "not deployed"; grepped the journal for a service that logs to a file; filtered on a status value absent from the data; reused a DOM node detached by re-render; ran a grep whose glob was expanded before `sudo`; a "down apps" query with a misplaced parenthesis reported 141 instead of 8. Each produced a plausible false bug report.
**Root cause:** A broken instrument's wrong answer looks exactly like a defect in the subject.
**Rule:** Point the same check at something known to exist (positive control) and run detectors on cases whose answer you know; if it flags a known-healthy case, the detector is wrong. `ls` before grepping, expand globs inside `sudo bash -c '...'`, widen context instead of guessing. When a check reports a failure, verify the check before reporting the subject. Reconcilers driven by detectors should be alert-only or reversible.
**Seen:** 4

### Success statuses, silence and zeros are not results
**Mistake:** A watcher's "completed" notice was read as success while its output was empty; a bounded watcher got zero data every poll and still printed a confident verdict; a multi-agent run reported sign-off while one agent had timed out; a dead monitor was "healthy" because quiet; a push from a detached HEAD said "up-to-date"; several metrics showed zero at once and each got its own harmless excuse while an upstream outage dropped all input.
**Root cause:** Exit code 0 and silence describe the process, not the outcome; each zero alone has a harmless story.
**Rule:** Watchers log each poll with timestamp and raw value, count successful samples, and print INCONCLUSIVE with non-zero exit when there are none. Read a finished task's output alone. After a workflow reports success, confirm in its journal that each step got real input and produced real output, and re-run tests independently. Confirm positively: monitors emit an armed line and refuse to arm without data; check pushes by the remote ref. When a second zero appears, look for a shared upstream.
**Seen:** 4

### Establish exists / visible / has content with measurements before fixing layout
**Mistake:** Four rounds of CSS tweak and screenshot; a "white column" fixed twice when the panel was present and sized but had no empty state; fixes applied to a dropdown trigger while the bug was in its options; a missing background explained away as "same colour as the card" when the CSS variables were undefined and a new class name collided.
**Root cause:** Screenshots hide pixel-level facts, and inferences ("not visible") were accepted as observations.
**Rule:** Name the exact element in the screenshot and map it to code. Count it by a unique selector, then read `getBoundingClientRect()` and computed styles for it and its neighbours; gaps under a few px are overlaps. Verify any "unexpected but explainable" spot on the spot: every `var(--x)` defined, new class names unused. If a fix "worked" and the bug returned, the fixed thing may never have been the fault. For rendering reports, ask where the reporter saw it.
**Seen:** 4

### Report only observed evidence; never fabricate or suppress it
**Mistake:** Narrated "sent" and timestamps for tool calls that had not returned; ran a send script with `>/dev/null 2>&1; echo sent` and reported two failed sends as done; filled plausible but invented values (times, a 48h deadline when production uses 36h) into client-facing samples.
**Root cause:** Described expected success or a mental model as fact instead of real output.
**Rule:** After a tool call, wait for the real result; unconfirmed means not done. Keep output and exit code (`... 2>&1; echo "exit=$?"`), require the explicit success line with an id, and read back. Every value in a sample or status claim is pasted from a render/query just run, or an explicit placeholder. Before stating a period or threshold, find where production sets it (runtime overrides beat defaults).
**Seen:** 3

### Verify data is authentic, not just present
**Mistake:** A scraping pipeline was "e2e verified" because rows rendered; every row was a fabricated person (a mapping step dropped real data and an LLM filled in). The first real attachment upload was verified by count and ids, but the images were the sender's own quoted photos.
**Root cause:** Checks confirmed writes existed, not that values were real and new.
**Rule:** Inspect values: real vs placeholder or hallucinated, distinct vs identical, each traceable to a source. Run the source step once directly and compare its raw output with what landed downstream. Open and look at the first real batch of third-party content. Report "pipeline runs" and "data is real" as separate claims.
**Seen:** 3

### Unit tests and mocks prove pieces; a real first-time end-to-end run proves the feature
**Mistake:** 96 green unit tests, yet the feature never fired on a new project's first turn (its state is created during the turn); "thoroughly tested" meant unit tests, and a real run hit filesystem state units never saw; a UI card depended on a field only the mock had.
**Root cause:** Tests encoded the author's assumptions about inputs, state and data shape.
**Rule:** Before calling a behavioural feature done, run the real first-time path (new account, nothing pre-seeded) through API, queue, worker and backend on the deployed shape, with a control run with the fix reverted. Confirm UI-dependent fields exist in a real API response. For client deliveries, "flow works" means a browser pass of every role. Otherwise state exactly what ran ("unit-tested only"). Ask whether the state your code reads can be created during the request.
**Seen:** 3

### Click every control with a non-default input; inventory actions before removing UI
**Mistake:** A Back button was checked as present but did nothing; chips stayed clickable during generation and appended to the send; a picker rendered options but the run path ignored the selection (the e2e used the default); merging two cards moved all data but lost a click-to-filter handler.
**Root cause:** Presence and the happy path were taken as proof of function; handlers live outside any content list.
**Rule:** Click every interactive element and assert the state change, using non-default values so the downstream effect must change. While an operation is in flight, try likely actions (double-send, switch, navigate) and assert they are guarded. Before writing "verified", name the effect and the input that produced it. Before removing UI, list what it shows and what it does (handlers, data hooks, submits, keys) and give both a destination.
**Seen:** 3

### Verify what you removed or silently un-changed, not only what you added
**Mistake:** A refactor script asserted old code was gone while the replacement import matched nothing; a slice-based HTML patch with a non-unique end marker deleted a component and blanked the page; a hand-typed compose restart dropped an override file, so a build-time env var vanished while health checks passed.
**Root cause:** Only the intended change was checked; deletions and dropped settings were not.
**Rule:** Assert both halves of a two-part edit. After bulk/regex edits, use unique anchors, diff against the pre-edit copy, load the page and check console plus a concrete render assertion. Use the deploy script instead of hand-assembled commands, and diff the container's full env before and after a restart: "is everything true before still true?"
**Seen:** 3

### Assert explicit pass conditions and report observed values, not verdicts
**Mistake:** A parity check answered "same" while both paths silently dropped over-limit files; a CORS preflight was read as "204, fine" while its headers showed framework defaults and no allow-origin.
**Root cause:** Compressing observations into a verdict, or skimming a status code, discards the evidence that answers unasked questions.
**Rule:** Assert it or don't print it. Ask "what did each path do?" rather than "did they match?", and report concrete values even for passes. Treat shared absence (both empty, both zero) as suspicious. For CORS, caching, cookies and redirects, headers decide; a library default where your config should be means your config is not in the path. Side effects inside React state updaters may never fire.
**Seen:** 3

### A limit, page or read window is not a total or a boundary
**Mistake:** Reported "20 pending" when 20 was the configured cap (real 25); dated an incident from the first line of a tail-read log when it began two days earlier.
**Root cause:** The sample window's edge was read as the data's edge; precise timestamps looked verified.
**Rule:** A round number in a statistic slot: check config for a matching cap first. Anything through limit/pagination/tail is "first N". For earliest/latest/count, query `min()/max()/count()` on the full data. Label on-screen numbers as cap vs total. Fetch boundary values and totals yourself.
**Seen:** 3

### Try to refute a root-cause claim before acting; audits go to an independent session
**Mistake:** Acted on own root-cause claims that a skeptic with the data would have refuted (a "buggy" order path that was fine; a rewrite declared done on unit tests that failed in the real event-loop thread). A document audited four times by its author still had 83 valid findings for an independent reviewer.
**Root cause:** Self-preference: the author shares the blind spot of the change and cannot see it from inside the same context.
**Rule:** Before acting on a claim that drives a change with real side effects, try to refute it with facts (logs, data, reproduction, the real runtime), defaulting to "refuted" under uncertainty; act only if the claim survives. The fix is structural, not "try harder": the author shares the change's blind spot, so for high-stakes side-effect claims (orders, data, schedulers) hand the refutation to a context that has not seen your reasoning. Audits of documents, batch output and important conclusions go to a separate session that has not seen the reasoning; the author then checks every finding independently and replies accept or reject with a reason. If you cannot run the refutation (no data, wrong runtime), say so and ask.
**Seen:** 3

### Gate on the exact command CI runs; a green build is not verification
**Mistake:** A frontend fix was declared done because the bundler build passed while a handler referenced an out-of-scope identifier; the same trap later broke CI.
**Root cause:** Some bundlers (e.g. Vite) strip types without checking them; knowing the caveat did not change the habit.
**Rule:** Run CI's command (e.g. the typecheck script) before every push. Sign off frontend fixes only on measured behaviour in a real browser, including the "should not happen" branch and old timing windows if a timing hack was removed. When a lesson is about a misleading success signal, replace the command rather than adding a caveat.
**Seen:** 2

### Reading code is a lead, not proof; do all the verification available
**Mistake:** Conclusions were presented from reading code or docs, and verification was paused to ask permission for more checks.
**Root cause:** The worst failure mode is a confidently wrong answer.
**Rule:** For each key finding ask "what did I execute or observe?"; if only read, tag it unverified or go verify (run, curl, query, show output). Do every verification that can be done without asking; prefer two independent methods diffed. Pause only for irreversible or outward-facing actions.
**Seen:** 2

### Verify persisted-state fixes across a reload
**Mistake:** A reset fix used `null` as "empty"; the store wrote it to sessionStorage, the string "null" came back on reload and broke the page.
**Root cause:** Only the in-memory path was tested, and an ad-hoc empty value replaced the store's sentinel.
**Rule:** For fixes touching storage, cookies, DB or URL state, use the existing empty sentinel, check how the setter serialises it, and verify after a reload or fresh mount by inspecting stored values. Run the type checker explicitly when the build does not.
**Seen:** 2

### Test every input value production passes, including the quiet side of thresholds
**Mistake:** 25 green tests for a gate all passed `false`; production passes `true` for every new session, so the real path was never tested. A wrong threshold would raise no error, just fewer alerts.
**Root cause:** Only the design-time path was covered; missing actions leave no trace.
**Rule:** For a boolean/enum gate, read the call sites and test every value production produces. For thresholds, test threshold-ε, threshold, threshold+ε and read the threshold from config. Ask "what does failure look like?"; if "quiet", test it actively. Before adding a key to a registry, check whether the same map is also a lookup keyed by an external namespace.
**Seen:** 2

### Prove a test or gate can fail
**Mistake:** New gate layers returned a boolean but never set the exit code, so failures reported green; source-text assertions that broke on a refactor were dismissed as "pre-existing".
**Root cause:** Copied bodies without the exit line, tested only the passing case; text-matching tests fail for wrong reasons and get ignored.
**Rule:** When adding a case to a harness, break the expectation once and require a red verdict and non-zero exit. Make shared helpers safe by default (they set `process.exitCode` themselves). Before calling a failure pre-existing, `git log -S` what it asserts; mutation-test any repaired test.
**Seen:** 2

### Assert the mechanism at the outermost layer users traverse
**Mistake:** A repo config value was asserted green while a different, unversioned value was in force on the host; passes came from the environment (a system credential helper, another validation rule) rather than the code.
**Root cause:** Config proves intent, not effect; symptoms are costly to stage.
**Rule:** Assert the boundary itself (a `cache-control` header, a permission error for a foreign tenant, row counts after a double deploy) at the public URL, and run it in the deploy pipeline. Move the check outward whenever a CDN/proxy layer is added. For an assertion that alone guards a harm, break the guarded code once and require red; ask what produced the pass.
**Seen:** 2

### Measure the specific thing a number claims to count
**Mistake:** Reported a sub-metric as the headline score from a `(\d+)%` first-match regex; reported bugs from a tool's summary field, from counting `el.onclick` in a React app, from `pgrep -f` matching itself or conflating identical command lines, and from two half-runs that each missed one condition.
**Root cause:** Trusted the number before asking what the probe counts and can see.
**Rule:** Extract the label with any scraped value and match on the metric name. Before acting, answer: what does it count, what can it see, can it match itself, can it distinguish the cases? Treat summary/preview fields as renderings and read the source. To verify "B under condition A", one run must satisfy both. When a number contradicts intuition, suspect the measurement first.
**Seen:** 2

### Suspect your own check and layers before blaming someone else
**Mistake:** Reported a teammate's service ignored a parameter when one's own proxy dropped it; reported apps broken after building hostnames from an assumed pattern the system normalises differently.
**Root cause:** A fault seen through your own middleware or assumptions cannot be attributed.
**Rule:** Re-run directly against the upstream, bypassing every layer you control, and use identifiers the system emits (follow redirects, read config). When a new check disagrees with a system that worked an hour ago, suspect the check. Hold claims about others' components to a higher bar, and say so when correcting.
**Seen:** 2

### Verify the user's state and failure mechanism, not a matching symptom
**Mistake:** Reproduced a dropped connection by stopping a server (instant error and reconnect) while the user's sleeping device left a half-open socket; confirmed fixes via DB after the flow settled while the user saw an earlier screen.
**Root cause:** Matching symptoms were treated as matching mechanisms, and verification happened where it was cheap.
**Rule:** State the failure mechanism and confirm the repro exercises it (a browser offline toggle does not cut an open stream; a reload is not a private window). The last check for anything a user sees is the product in their starting state: fresh login, before the first action, their device and browser. If impossible, say so and name who can verify.
**Seen:** 2

### Assert a repro's preconditions and resolve its target dynamically
**Mistake:** Concluded a fast path did not fire when the trigger had returned 402; declared a regression from a hardcoded old job run while the system acted on the latest one (a repeat of a logged lesson).
**Root cause:** Preconditions were unchecked, and the lesson lived in a note rather than the script.
**Rule:** Every automated repro prints and asserts its preconditions (2xx trigger, row created, right environment); a run whose setup failed is void, say so. Resolve the target to what the system acted on, never a hardcoded id, and encode lessons in the tooling.
**Seen:** 2

### Stop iterating fixes in production
**Mistake:** Two unverified canvas fixes reached production, the second flashing the background on every toggle; four hotfixes in a row chased a smoke-test payload that differed from the real route's.
**Root cause:** Skipped local reproduction; trusted the smoke path over real request bodies.
**Rule:** Reproduce, fix and watch the exact interaction locally before deploying visual changes (keep resize observers driving WebGL `setSize` debounced). After two hotfixes on one surface within an hour, stop and find the structural cause; diff real payloads first. Watch for kill-vs-write races, null-coalescing that hides failure, stale closures. Present "right vs fast" trade-offs to the requester.
**Seen:** 2

### Don't extrapolate a finding beyond what was measured
**Mistake:** Rated a vulnerability inert on a second deployment because the code was identical, though its data made it exploitable; predicted a bug would certainly fire based on a fixture production can never produce.
**Root cause:** Same code was taken as same data; a constructed fixture proved possibility, not occurrence.
**Rule:** Measure data-dependent findings per deployment and re-test claims made while blind once access arrives. After proving a defect with a fixture, check whether production can produce it and state preconditions; keep the fix if logic is wrong but withdraw overstated severity.
**Seen:** 2

### Claim only what a load test reproduced
**Mistake:** Reported a system "validated for N users" from a scripted test; a real simultaneous burst hit a queue race and ~40% of jobs failed.
**Root cause:** Scripted requests stagger differently from simultaneous humans; a known-fragile queue was treated as "usually works".
**Rule:** Assume known-fragile paths race until proven under realistic simultaneity, fix backlog issues on that path before high-concurrency events, and tell stakeholders the untested weak point up front.
**Seen:** 1

### Execute every bullet of a written validation checklist
**Mistake:** The spec said "test every service on the host"; only targeted services were tested and public vhosts broke.
**Root cause:** Writing the risk down created false confidence.
**Rule:** After network/firewall/sysctl changes on a shared host, run every validation item mechanically: enumerate listeners (`ss -tlnp`) and hit every public endpoint.
**Seen:** 1

### Define health metrics by the user-visible symptom
**Mistake:** Nearly escalated "11 users blocked" by counting records with no output; 2 were actually stuck.
**Root cause:** The proxy is also true for users who moved on or made requests with no such output.
**Rule:** Define failure by the symptom (e.g. latest message is an unanswered user message older than normal processing time, with a floor for in-progress work), and check one flagged case in logs before alarming anyone.
**Seen:** 1

### Grep every reader of a changed value and test what the user is told
**Mistake:** A new cap updated one verdict field but not the fields and copy that restate it, so capped users were promised "come back tomorrow"; a SQL replay of a rule missed an ordering bug in code.
**Root cause:** Tests built from the change's own mental model share its blind spots.
**Rule:** After changing a value, grep every reader and confirm each still tells the truth. Assert what the product says, not only what it decides. A rule replay is evidence about the rule, not the code.
**Seen:** 1

### Reconcile one real transaction when money depends on an external number
**Mistake:** Guarded a vendor cost field against being missing, but the vendor returns `0` for seconds after completion; runs were booked free.
**Root cause:** Defended against an imagined failure value instead of the real one.
**Rule:** Reconcile one real transaction against the vendor's records before trusting billing; enumerate every value the source actually emits.
**Seen:** 1

### Verify a startup change by starting it; restore first on failure
**Mistake:** A syntax check passed on a patched entry file; the service crash-looped on an undefined identifier.
**Root cause:** A syntax check parses but does not execute.
**Rule:** Boot a copy on a spare port with a timeout and read the output before restarting the real service. If the restart fails, restore the backup first, diagnose second.
**Seen:** 1

### Compare artefacts by rendering them, not by their text
**Mistake:** A correct template was declared "not the one" and a layout hand-built twice; its distinguishing features were invisible in extracted text.
**Root cause:** Compared through a lossy channel.
**Rule:** Render both and compare side by side (rasterise and compare content boxes); to reproduce, drive the original generator with new data.
**Seen:** 1

### When verifying a remediation, check whether its cause is still present
**Mistake:** A human follow-up reply was verified correct and nearly reported "all good"; the bot had wrongly refused the question minutes earlier, the second time that day.
**Root cause:** Reviewing the fix narrowed the view away from what it fixed.
**Rule:** Read the context before the remediation, ask why it was needed, and report "remediation OK" and "cause not removed" separately.
**Seen:** 1

### Exit conditions for temporary measures must be reachable
**Mistake:** A workaround's revert condition used a monotonic metric (swap usage) that never drops without a reboot.
**Root cause:** The metric reflects the problem but does not recover when it goes away.
**Rule:** Ask "what action makes this true?"; use recovering metrics (free memory) or a direct test.
**Seen:** 1

### Do a reader's pass on UI before handing it over
**Mistake:** A redesign shipped with titles cut from raw input or hostnames, a layout scrolling into blank space, and inconsistent terms.
**Root cause:** Features and screenshots were checked, but the product was never read as a user.
**Rule:** On every touched page: meaningful titles (never ids or raw slices), one term per concept in every language, scroll to the bottom, full-page captures at desktop and phone width, locale copy rules applied.
**Seen:** 1

### Testing pinned agent prompts and streaming pages
**Mistake:** Regression tests ran on old entities whose agent prompt was pinned at creation; browser waits hung on pages with long-lived SSE.
**Root cause:** Prompts are pinned per session/entity; `networkidle` never fires with an open stream.
**Rule:** Verify prompt-side fixes with a freshly created entity. Use `domcontentloaded` plus explicit waits. Don't file a single 502 during a known deploy window; when a race can't be observed reliably, ask the code owner to check.
**Seen:** 1

### Test volume must match the change
**Mistake:** A ~100-line change shipped with over a thousand lines of ported legacy tests, including duplicates, filler, and a test locking in a known bug.
**Root cause:** Quantity read as rigour.
**Rule:** Grade each test: core rule or real-incident regression keep; duplicate, filler, mock-was-called or bug-locking delete; name overpromising fix the assertion. Port legacy suites in their own PR. Prefer one realistic e2e over many shallow unit checks.
**Seen:** 1

### A "not checked" list is for what cannot be run, not for what was skipped
**Mistake:** A PR review closed with "not checked: browser UI, archived-status effect, realistic race rate", all of which could be run locally in under an hour. The user had to send it back.
**Root cause:** Listed checks by effort rather than by reachability.
**Rule:** Before writing a "not checked" item, ask whether a local run, a throwaway DB or a read-only prod count could settle it. If yes, run it first. Only truly unreachable items (no access, needs a third party, needs prod writes) stay on the list.
**Seen:** 1

### "No glitches" in motion needs dense sampling of the delivered take
**Mistake:** A procedural animation change was declared free of a visual defect ("no finger bends backwards") after six staged close-ups; the recipient saw the defect in the delivered recording within seconds, at moments the stills had not covered.
**Root cause:** An absence claim about time-varying output was made from a few hand-picked frames of a different run, not from the artifact that was sent.
**Rule:** For animation or video, check the exact file being delivered, sampled densely across its whole length (a frame every few seconds at minimum, plus the most extreme-motion segments), at the framing the viewer sees. Make the failure state impossible by construction where you can (clamp the range) instead of relying on samples. Without that, say "checked N frames" rather than "none". For a direction question (does it bend the right way?), stills from one angle are ambiguous: measure it against a physical expectation (e.g. a hanging hand's fingertips must move toward the body when it closes) before trusting what a picture seems to show.
**Seen:** 2 (second time a reversed sign survived several visual checks)

### Prove a sandbox by attempting the forbidden act, layer by layer
**Mistake:** Ran an agent eval for hours against hardlinked copies of real project files, trusting a tool-restriction flag. Replays tried Bash, Edit and Write on real files; all failed, but only because the flag happened to hold. Then a probe that asked the model to list its own tools returned 22 tools and was taken as proof the flag was ignored on resume; the list came from tools the model saw in the replayed history.
**Root cause:** Isolation was assumed from configuration and from the agent's self-report, never tested by trying what it must not do. A model's account of its own capabilities reflects its context, not what the harness registered.
**Rule:** Before an agent touches anything that maps to real data, prove each isolation layer alone with a canary: make it attempt the forbidden write (to a harmless file) with only that layer active, and check the canary is absent. Record every tool call's result and stop the run if a forbidden one succeeds. Judge capability by what a call returns, never by what the agent says it has.
**Seen:** 1

### Pilot a batch end to end before running it at scale
**Mistake:** Launched 720 eval runs (about 50 minutes) as the first full pass of a new pipeline; the run step had been tried once per case, but judging, reporting and the slot split had not. Only afterwards did it show that a slot file's Windows line endings made the tool silently skip three cases.
**Root cause:** "Each step works alone" was treated as "the pipeline works"; the first end-to-end pass was the expensive one.
**Rule:** Before any batch of tens or hundreds of runs, push one or two items through the whole chain (run, judge, report, any split or merge step) and check the counts and outputs at every stage. Scale up only after that passes, and still check per-group counts at the start of the full run, not at the end.
**Seen:** 1
