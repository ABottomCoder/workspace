---
name: feedback_run_readonly_queries_directly
description: Run read-only investigative queries without asking; only cost needs approval
metadata:
  type: feedback
---

Standing authorization pattern worth establishing with the user early: **do not ask permission to run read-only queries** that cannot affect production and would produce information we actually need. Run them and report what came back.

The only thing that still needs approval is **cost**: a query that would eat enormous compute or run a very long time. Small and bounded, go ahead. "This might chew a big warehouse for half an hour", ask first.

**Why:** the user was explicitly telling me to stop stalling on a query I had already designed and justified. Asking permission to *look* at data is friction with no safety benefit when the operation is read-only, and it delays the evidence a decision is waiting on. It also cuts against [[feedback_evidence_required]]: if I can measure something instead of inferring it, the measurement is the job, not a thing to request.

**How to apply:**
- Read-only and bounded → run it, then report.
- Size it first (row counts, a metadata check) so you know which category you're in, and set a statement timeout as a runaway guard.
- Return **counts, not values**, so the result set isn't itself a PII extract, and keep raw identifiers out of the transcript.
- Run any number you intend to publish **more than once** — sampling re-randomizes, and one unstable metric already nearly shipped as a fact.
- Anything that writes, deletes, alters an object, or is outward-facing is unchanged: it still stops with the user.

**Two rules from the third repeat of this correction:**
- **A dead session is not a blocker, it is a step.** Try the console first. If a login really is needed, ask for it in one line *while already doing everything that doesn't depend on it* — never as a reason to stop, never as a closing note on an answer.
- **Never surface a query as a suggestion.** If I designed it well enough to describe, I designed it well enough to run. Describing a measurement I could have taken in the same turn I could have taken it is the failure.

The pattern across every repeat: I kept converting *my* work into *the user's* decision. Read-only investigation is mine to do; the user owns cost and anything outward-facing.
