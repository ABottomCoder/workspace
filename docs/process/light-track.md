# Light Track (default)

Every business runs this unless its `business/<co>/CLAUDE.md` says `tier: heavy`. Heavy adds steps on
top ([heavy-track.md](heavy-track.md)); it never removes these.

## Always

- **Route first:** identify business → project or ticket; read `business/<co>/CLAUDE.md`, then the
  project `CLAUDE.md` + `DEVDOC.md` or the ticket's `STATE.md` + `HANDOFF.md`. Attach the session
  (`tools/work/attach`).
- **Evidence before conclusions, Ask-Gate** ([evidence-and-ask-gate.md](../principles/evidence-and-ask-gate.md)).
- **Decision Ladder** ([decision-ladder.md](../principles/decision-ladder.md)).
- **Verification before done** ([verification-before-done.md](../principles/verification-before-done.md)).
- **Backups only for irreversible risk** ([backups-and-risk.md](../principles/backups-and-risk.md)).
- **Authority:** outward-facing or irreversible actions wait for the approver
  ([communication.md](../principles/communication.md#authority-and-approval)).

## Plan before build (non-trivial work)

Non-trivial = 3+ steps, an architectural decision, or prod/schema/destructive risk.
- Write the approach **before touching code**: `tickets/<ID>/spec.md` from `templates/ticket/spec.md`
  (spec → plan → tasks, testable acceptance criteria, safety block only for irreversible risk). Durable
  project design goes to the project's `docs/`.
- Obvious one-line fixes: skip the ceremony, just fix them.
- If implementation diverges significantly: stop, re-plan, update `spec.md`.

## Keep state in files (survive compaction and rollover)

- **Ticket work** (finite): `business/<co>/tickets/<ID>/` with `STATE.md`, `LOG.md`, `HANDOFF.md`
  ([ticket-lifecycle.md](ticket-lifecycle.md#the-ticket-directory)).
- **Project work** (long-lived): the project `DEVDOC.md` (state, active work, TODO, newest-first change log).
- **Log as you go** (`tools/work/log`): after each thing a successor (or you after a compaction) must
  know: commits, deploys, files changed, decisions and why, messages sent, failures, findings. Not files
  read or raw output. Test: would someone redo or contradict this, or be unable to tell whether it
  happened, if it weren't written down?
- **Refresh your `handoff/<role>.md` at milestones**, not only at the end (edit in place, then `tools/work/handoff`).
- **Never answer "did I do X?" from memory**: check `LOG.md`, `git log`, or the conversation.
- Small one-shot tasks: skip all of this except the daily log line.
- **Daily log:** after each completed task append one line to `user/logs/YYYYMMDD.log`, prefixed with
  the business (format in [ticket-lifecycle.md](ticket-lifecycle.md#daily-log)).

## Reports

Only when useful (someone will read it, or the result needs evidence that won't fit in a message).
When you write one, it goes in `tickets/<ID>/reports/` and follows [reporting.md](reporting.md).

## Knowledge capture

- After any user correction: add or strengthen a lesson (generic → `lessons/<category>.md`, business →
  `business/<co>/lessons.md`, the user's taste → `user/lessons.md`). Strengthen existing entries rather
  than duplicating; note recurrences.
- After working in a repo: make sure its `CLAUDE.md` exists and append what you learned (build commands,
  architecture, gotchas). Never delete existing content unless asked; flag a workflow step that doesn't
  match reality instead of silently changing it.
