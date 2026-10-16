---
name: resume
description: Pick up a work item a previous session saved (ticket HANDOFF/LOG or project state file) and continue seamlessly. Use when the user says "resume X", "continue X", "pick up X", "where were we on X", or when a session starts from a rollover handoff.
argument-hint: "[<business>/<project> | <business>/tickets/<ID> | user/work/<slug>] (lists open work if omitted)"
---

# resume

## 1. Find the item

- `$ARGUMENTS` names it → use it.
- Omitted → `bash tools/work/show` (already bound, e.g. after rollover); else list candidates:
  `business/*/tickets/INDEX.md` rows that are not `closed` (regenerate with `tools/work/index <co>`
  if stale), `user/work/*/STATE.md`, and today's/yesterday's `user/logs/*.log` lines with an open
  status. Ask which one.

## 2. Bind and read

`bash tools/work/attach <target>` (skip if already bound), then read fully: ticket `STATE.md`,
`HANDOFF.md` (resume-here and verified facts first), the `LOG.md` tail; or the project state file (`tools/work/show`)
(and its `## Session handoff` section after a rollover). Read linked reports only if you need that depth.

## 3. Re-establish ground truth

The world may have moved since the handoff: per repo `git status`, `branch --show-current`,
`log --oneline -5`; confirm the branch exists and matches. Spot-check verified facts only where
something looks stale; flag contradictions instead of re-verifying everything.

## 4. Play back, then continue

Tell the user briefly: where it stands, the one thing in flight, the next action you are taking,
and anything that now contradicts the handoff. Then do the next action. Keep logging
(`tools/work/log`) and run the `handoff` skill again at the next milestone or before stopping.
