# Verification Before Done

Never mark a task complete without demonstrating it works: run the tests, check the logs, show the
before/after behaviour difference for bug fixes, diff behaviour against the base branch when relevant.
Self-check: *would this pass code review from the tech lead?*

## Scope: verify once, for real

This rule is about **evidence for claims made to people** ([evidence-and-ask-gate.md](evidence-and-ask-gate.md)).
It is not a mandate for redundant self-verification passes: extra "double-check" scaffolding causes
over-verification with no accuracy gain (see [model-tuned-rules.md](../reference/model-tuned-rules.md)).
Verify once, for real, in the main loop; don't spawn a verifier subagent for your own work.

"For real" means coverage, not volume. Extra runs of the suite you already have do not reduce risk.
Before declaring done, **list what the change could break**: shared state it touches, the loop it sits
inside, the neighbouring code path, and every safety property you asserted in a comment but never
executed. Then cover those.

## What counts as "it works"

- **Measured behaviour, not a success signal.** "It builds", "the bundle hash changed", "it deployed",
  "N tests green" are all compatible with broken code. Sign-off on a user-facing fix rests on the
  behaviour measured in the real surface (browser, endpoint, rendered file), before and after.
- **Run the command CI runs, not a proxy for it.** A build step that skips type-checking prints success
  over type errors. When a lesson is about a misleading success signal, the fix is to replace the
  command, not to add a caveat to it.
- **Unit tests prove the parts; end to end proves the feature happens.** For behavioural features run
  the true first-time path on the deployed thing (new account, new project, nothing pre-seeded) and read
  the resulting state, not the exit code. Any code that reads state at the start of a turn to decide what
  to do must answer: can that state be created during this turn?
- **Every real input path, on the real path.** For a conversational or multi-channel system (group
  mention, DM, email, webhook), each input path has its own format traps. Verify each end to end, or
  mark it explicitly "not verified on the real path".
- **Reproduce twice, not once.** State-dependent, one-shot and de-duplication logic means the happy path
  often works the first time and breaks on repeat.

## Measure the broken world first

- **Take a baseline in the broken state, ideally before the fix is deployed**, and keep the raw numbers.
  Verification then becomes a comparison, not an assertion, and the baseline proves your instrument can
  read a bad value at all.
- If a baseline is impossible (already deployed, can't reproduce), say so; an after-only "clean" reading
  cannot distinguish "fixed" from "the instrument was blind all along".
- Before trusting a negative result ask: *if the bug existed right now, would this reading change?* If
  you can't name the value that would change, the test proves nothing. When the location of a symptom is
  unknown, prefer broad discovery (scan every element for the property) over a targeted assertion on the
  two places you guessed.
- When fixing a timing issue, sample across the old timing window, not only at t=0.

## Tests and gates

- For every new assertion, ask "what input makes this fail?" and produce that input. A test that passes
  on the pre-fix tree is a defect in the test.
- When adding a case to a test gate or harness, verify **the gate fails**: break an expectation once and
  confirm a non-zero exit / red verdict. Harness bugs read like good news.
- Test the runtime production actually uses; report counts per runtime with exact dependency versions.

## Test scope (from QA practice)

- **Side effects are in scope.** Any delete/modify (a credential, a user, a URL) needs tests that the
  dependents still behave: references to a deleted resource report the right error or fallback.
- **Changed URLs: test the old path** returns the right redirect, 404 or deprecation response.
- **Cross-check test cases against the AC line by line.** A test that contradicts the AC is worse than
  none. Every AC item needs an explicit, measurable pass/fail condition; clarify ambiguous AC before
  testing, not after. A false pass is more damaging than a false fail.
- **Scan for dependent components before writing tests** and include integration checks for them.

| Pitfall | Mitigation |
|---|---|
| Test passes but the AC was not actually met | spot-check each pass against the AC |
| Resource deleted, dependents not re-tested | mandatory dependency scan in test planning |
| Generated test opposes the requirement | AC cross-check before execution |
| URL deprecation untested | change-type → required-test checklist |
| Agent unaware of dependent components | give full codebase access and the dependency picture |

## Before saying "done"

Run the "before saying verified" checklist at the end of
[verification-antipatterns.md](verification-antipatterns.md). For heavy-tier work, done also requires the
independent QA sign-off ([qa-session.md](../process/qa-session.md)).
