---
name: handoff
description: Save this session's working context into the bound work item so a fresh session (after compaction, rollover or a restart) can resume with zero re-discovery. Use when the user says "save context", "save progress", "handoff", "hand off", "I'm closing this session", at milestones, and when the rollover hook fires, or the equivalent in any language.
argument-hint: "[<target>] (default: the work item this session is bound to)"
---

# handoff

The next session reads only the work item (it is re-injected by the SessionStart hook), not this
conversation. Write it so it can carry on as if it never left.

## 1. Target

The bound item (`bash tools/work/show`), or `$ARGUMENTS`. Not attached → attach first (`attach`
skill); if no item fits, create `user/work/<slug>` (`ticket` skill).

## 2. Ground truth first

Don't write from memory. For every involved repo: `git -C <repo> status`, `branch --show-current`,
`log --oneline -10`, `diff --stat`. Re-check every "done" claim (tests pass? PR open? deployed?);
what you cannot verify is marked **UNVERIFIED**. Evidence files go to the ticket's `evidence/`.

Also capture what only this session knows: running background tasks and monitors (task IDs, what each
does), run mode (paper / live, ports, running vs stopped on purpose), where credentials live (the key
name, never the value), open threads and the next step.

## 3. Write

- **Ticket / user work item:** `bash tools/work/handoff` (archives the current `HANDOFF.md` to
  `history/`), then fill the fresh `HANDOFF.md` (template sections: resume-here + immediate next
  action, verified facts with evidence, goal, current state per repo, ordered next steps, waiting on
  and promises, decisions and why, gotchas, references). Keep `STATE.md` (status, links) accurate.
- **Project:** update its state file (`bash tools/work/show`; policy in `tools/work/README.md`):
  current state first, active work, TODO / open decisions, and a change-log line
  (`bash tools/work/log "..."`). For a rollover, also a `## Session handoff` section with what only
  this session knows (replace any older one). The state file is newest-first and not an archive: keep
  the last 3-5 sessions, move older ones to `docs/HANDOFF_ARCHIVE.md` or drop them (git is the archive).
  If the current-state section contradicts what is actually running, fix it before anything else. If start
  commands, success signals or the safety tier changed, refresh the project `CLAUDE.md` ▶ run book.
- Log one line: `bash tools/work/log "handoff: <status>; next: <action>"`.

Restructuring docs while handing off is a **zero-loss move**: content leaves a file only by moving to
another file with a pointer left behind; never shorten by deleting commands, parameters, thresholds,
triggers or reasons. The only true deletions are statements that are now wrong. Do a large
restructure as its own commit so it can be diffed and reverted.

## 4. Commit and push (repos whose state policy is in-repo or orphan branch)

`git status` and `git diff` first; add only the files you mean. The message states any strategic-flag
flip, any production-affecting change and why (`lessons/git-and-release.md`); code not yet validated in
its real runtime is committed only with "UNVERIFIED + how to verify" in the body. Push normally: no
force, no `--no-verify`. No remote → ask before creating one. A push or hook failure is reported, never
bypassed. Orphan-branch policy: commit and push from `.state/` only.

## 5. Daily log

Append to `user/logs/<YYYYMMDD>.log`:

```
[HH:mm] [<business>] <ID or project> | status: <status>
  done: <summary>   blockers: <if any>   next: <immediate next action>
```

## 6. Confirm

One or two lines: where it was saved, the commit hash and whether it was pushed, any inconsistency found
("state file says running, no task is running"), the status, the
immediate next action, and how to resume (`/resume <target>` or "resume <target>"). Rollover cannot
open a new terminal on Windows: tell the user to start a new session and say "resume <target>".
