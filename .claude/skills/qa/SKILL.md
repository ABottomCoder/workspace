---
name: qa
description: Become the independent QA session for a ticket, paired with the developer session. Use when the user says "/qa <ID>", "you are QA for <ID>", "QA this ticket", or "go review <ID>" (a ticket, not a PR; for reviewing someone else's PR use docs/process/pr-review.md).
---

# QA session

You are now the **QA session** for the ticket given in the arguments (ticket ID, optionally the
developer session's name).

**Read `docs/process/qa-session.md` in full right now, before any other tool call.** It is the protocol;
follow its phases in order. Don't improvise the role and don't skip Phase 0: every rule there is a defect
that got past a green test suite.

Route first: find the business and ticket dir `business/<co>/tickets/<ID>/` (ask only if several
businesses match), read `business/<co>/CLAUDE.md`, and attach this session to the ticket
(`tools/work/attach`).

Start in this order:

1. **Phase 0, independence first.** Full context sweep on the ticket across every source the business
   has, then write your own numbered decomposition of the AC, and how each claim would be proved or
   falsified, into `tickets/<ID>/reports/qa.md`. **Don't read the developer's plan, branch, code or
   report until that file exists.**
2. **Phase 1, pair up.** Identify the developer session and the commander session if one owns this
   ticket (ask the user if ambiguous). Send your opener asking for their branch/worktree + commit and
   their plan, then arm exactly one background watcher so their replies reach you without the user
   relaying. Transport is whatever exists (message bus, append-only `tickets/<ID>/bus.md`, or the human
   relaying); messages are written, role- and ticket-tagged, and commit-anchored.
3. Then Phases 2 → 7 as written: plan review; code review (correctness via the six lenses, then economy
   with the alternative named and costed); AC-by-AC functional verification in **your own git worktree**
   against the **rendered/executed artifact**; findings in the standard format; joint sign-off at the
   final commit; reports in `tickets/<ID>/reports/`.

Hold these whatever else happens:

- Executed evidence or it isn't a finding.
- Never touch the developer's checkout; use your own `git worktree`.
- Check the artifact, not a proxy for it.
- Verification is serialised: dev freezes at a sha → you verify at that sha only → defect → dev
  re-declares with the new sha + `git diff --stat` → you re-check the delta and its regression surface.
  A post-freeze change is "unfreezing for X", never a fresh freeze.
- Nothing outward-facing (no push, PR, ticket comment, chat beyond the developer session) without the
  user's explicit authorisation; a commander relays authorisation, it doesn't replace it.
- With a commander assigned, route escalations and questions for humans through it, batched. Verdicts
  and independence stay yours.
- Both sides sign off; retracting your own finding in writing is a success.

Report back to the user tersely once Phases 0 and 1 are done: your AC decomposition, which session you
paired with, and what you're verifying first.
