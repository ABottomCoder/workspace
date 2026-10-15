# Decision Ladder: least code that fully solves it

Default to the **least code that fully solves the task**. The ladder runs *after* you understand the
problem and have traced the real flow end to end, not instead of it. Stop at the first rung that holds:

1. **Does this need to exist at all?** (YAGNI) If the task doesn't require it, don't build it.
2. **Does it already exist in the codebase?** Reuse the helper/util/pattern. Search across repos too
   (`grep` before writing a new util).
3. **Standard library / framework / platform native?** Use it before anything custom.
4. **Already-installed dependency?** Use it; don't add a package for what the manifest already has.
5. **Can it be one line / the shortest working diff?** Prefer deletion over addition, boring over clever.
6. **Only then:** write the minimum code that works.

## Never lazy about these

They are not "extra code", they are the task: input validation at trust boundaries, error handling that
prevents data loss, security, auth/permissions, accessibility. Don't cut them to shorten a diff.

## Root cause, not symptom

When fixing a bug, `grep` every caller of the touched function and fix once at the shared level. One
guard there beats per-caller patches and prevents sibling bugs. No temporary fixes. If a shared helper
can be misused by omission (a caller must remember to handle its return value), fix it so the default
is safe.

## Autonomous problem-solving

- Given a bug report: investigate and fix it. Read logs, trace errors, find the root cause. Don't ask
  the user to diagnose.
- Still follow commit/test/report conventions; skip heavy planning for straightforward bugs.

## Calibrate to task size

- Simple, obvious fixes: just make them. Don't over-engineer and don't recite the ladder out loud.
- Non-trivial changes (3+ steps or an architectural decision): plan first
  ([light-track.md](../process/light-track.md)), walk the ladder, and ask "is there a more elegant way?"
- If a fix feels hacky, step back and do the clean version.
- When intentionally taking a shortcut, say so and name the upgrade path.
- If implementation diverges significantly from the plan, **stop and re-plan**; update the spec.

## Rules that change behaviour

A rule's value is how much it changes a concrete action, not how true it is. "Be careful with
security" changes nothing; "touched auth, billing or secrets → run a static security scan and triage
before shipping" does. When writing a rule, name the action it changes.
