# tools/work — work items and session binding

One tool for the two kinds of work. Run `tools/work/work` with no arguments for usage.

| Kind | Where | Files |
|---|---|---|
| Project (long-lived) | `business/<co>/<project>/` | one state file, per the business's state policy (below) |
| Ticket (finite) | `business/<co>/tickets/<ID>/` | `STATE.md`, `LOG.md`, `handoff/<role>.md`, `HANDOFF.md` (generated index), `history/`, `reports/`, `evidence/` |
| Cross-business item | `user/work/<slug>/` | same as a ticket |

`<ID>` is the ticket-system ID as written (`ABC-18`, `2233`), else a short kebab description.

## Project state policy

Live state (current state, active work, TODO, change log) lives in exactly one file per project. The tool
uses the first that exists: `DEVDOC.md` → `.state/DEVDOC.md` → `docs/HANDOFF.md`. With none, `attach` follows the
business policy line in `stack.md`: in-repo → creates `docs/HANDOFF.md`; orphan branch → stops with setup steps;
unset → creates `DEVDOC.md`. `work log` writes under `## Change log`, creating it right after the H1 if missing
(restore injects the head of the file, so the log must sit near the top). Each business records its policy in `stack.md` → VCS:

| Policy | File | When |
|---|---|---|
| in-repo | `docs/HANDOFF.md`, committed and pushed | personal repos: state should follow the code everywhere |
| orphan branch | `.state/DEVDOC.md` = a worktree of an orphan branch (e.g. `state/<user>`), pushed to the same remote, never merged | company repos that allow personal branches: state backed up remotely, kept out of dev/main |
| local | `DEVDOC.md`, gitignored | company repos that do not allow it; lost with the machine |

Orphan branch setup (once per repo; `.state/` is excluded locally, the main branch's `.gitignore` is untouched):

```bash
git -C <repo> worktree add --orphan -b state/<user> .state     # git >= 2.42; older: git switch --orphan in a temp clone
echo ".state/" >> <repo>/.git/info/exclude
# commit and push from <repo>/.state; never merge state/<user> into another branch
```

Confirm the company allows a personal branch on its remote before choosing it (onboarding asks).

## Session binding

`work attach <target>` writes `user/sessions/.bindings/<session_id>`:

```
target=business/acme/tickets/ABC-18
role=main
attached=2026-10-14T09:30Z
```

`--role <r>` sets the role (lowercase, digits, `_ -`); re-attaching to the same item keeps it, another
item resets it to `main`. Apps attach with their app id as the role.

Paths are relative to the main dir, so bindings survive a machine move. The session id comes from
`$CLAUDE_CODE_SESSION_ID` (set inside Claude Code Bash calls; `$CLAUDE_SESSION_ID` also accepted),
else the newest transcript in the main dir's transcript dir (with a warning). Rollover copies the
binding to the new session.

`work restore` is the SessionStart hook (`startup|resume|compact|clear`). Bound to a project: injects
its state file. Bound to a ticket: `STATE.md` (≤ 2.5 KB) + the status line of each other role + the
session's own `handoff/<role>.md` (≤ 3 KB) + as much of the `LOG.md` tail as fits. Total ≤ 9.5 KB (the hook output cap is 10 KB). Unbound: a one-line routing
reminder only.

### Handoff: one per item, one file per role

A ticket (or `user/work` item) has exactly one handoff, and sessions take it over across compactions
and rollovers. It is split by role so that two lines of work on the same item (developer and QA, or an
app) never overwrite each other:

- `handoff/<role>.md`: that role's resume point (template `templates/ticket/handoff-role.md`, first a
  `**Status:**` line). Only sessions with that role edit it, in place. About 40 lines; detail goes to
  `reports/` or `handoff/<role>/<topic>.md` with a pointer.
- `HANDOFF.md`: **generated** index (each role, its file, last write, status line; sub-items). Never
  edited by hand; rebuilt by `work handoff`, `new-ticket`, `rename`, `close`.
- `work handoff [<target>] [--role <r>]` creates the role file if missing, else copies it to
  `history/handoff-<role>-<stamp>.md` when it changed since the last copy, then rebuilds the index. A
  hand-written legacy `HANDOFF.md` (before roles) is moved to `handoff/main.md` on the first run;
  until then restore injects it as is and says so.
- `work log` tags the lines of a non-main role (`[qa] …`). Restore flags a role file that is missing,
  still the template, over 40 lines, or older than 10+ of that role's LOG entries.
- `attach` warns when another session live on the item (transcript written within
  `WORK_PARALLEL_MIN`, default 120 min) has the same role.

A series of sessions on one theme (`web-fix`: fixing bugs as they come) is a ticket named after the
theme; its handoff points at the tickets it works on, and each rollover hands it to the next session.

- **Sub-items.** `work new-ticket <co> <ID>/<sub> "title"` creates `tickets/<ID>/<sub>/`, a ticket of its
  own that a session attaches to (`<co>/tickets/<ID>/<sub>`); restore points at the parent instead of
  inlining it. One level only; `INDEX.md` lists top-level tickets.
- **Rename.** `work rename <target> <new ID | new target>` moves the dir (also across `user/work` and a
  business) and rebinds every session on it. An unattached session that rolls over gets
  `user/work/s-<sid8>`; rename it once its subject is known.
- **Close / reopen.** `work close <target>` sets `status: closed` and `closed:`, and moves a top-level
  item to `tickets/_archive/<ID>` (or `user/work/_archive/<slug>`), rebinding its sessions; a sub-item
  stays under its parent. `INDEX.md` still lists archived items. `work reopen <archived target>` moves
  it back as `active`.
- **Pre-compaction snapshot.** `work snapshot` is the PreCompact hook: it writes
  `user/sessions/.snapshots/<session_id>.md` (time, trigger, and each worktree of the item's repo:
  branch, HEAD, uncommitted and unpushed counts; repo = the project, or the ticket's `project:` under the
  same business). Restore after a compaction shows it. It records mechanical state only; the narrative
  handoff is still written by the session at milestones.

## STATE.md format

YAML-style front matter, one `key: value` per line, then free Markdown:

```
---
id: ABC-18
title: Fix login redirect
status: active        # open | active | review | closed
project: web          # project dir under business/<co>/, or empty
created: 2026-10-14
updated: 2026-10-14   # bumped by `work log`
---
# ABC-18 — Fix login redirect

## Acceptance criteria
## Links            (ticket URL, branch, PR)
```

Required for the index: `status`. `id` is always the dir name; `title` falls back to the first
`# ` heading; `updated` falls back to the file's mtime. Legacy files without front matter are read
from header lines in the first 40 lines (`Status: closed`, `- **Status:** closed`).

`work index <co>` writes `business/<co>/tickets/INDEX.md` (ID | title | status | project | updated;
active, open, review, then closed; newest first). Never edit it by hand.

## Logs

- Ticket: `work log [<target>] "msg"` appends `<UTC stamp> msg` to `LOG.md`. One line per thing a
  successor must know (change, decision + why, message sent, failure). Past 300 lines
  (`WORK_LOG_LIMIT`), move older lines to `history/` and leave a digest.
- Project: the same command adds `- <date> msg` under `## Change log` in `DEVDOC.md`, newest first.
- `work handoff [<target>] [--role <r>]` (tickets only): see Handoff above.

## Templates

`work new-ticket` and `work attach` (project without a `DEVDOC.md`) copy from `templates/ticket/`
(`handoff-role.md` is used by `work handoff`)
and `templates/project/DEVDOC.md` when present, replacing `{{ID}} {{TITLE}} {{PROJECT}} {{DATE}}
{{BUSINESS}}`; otherwise they write the minimal files above.

## Portability

bash 3.2+ and python3. `WORK_ROOT` overrides the main dir (tests only); `CC_PROJECTS_BASE` overrides
`~/.claude/projects` (tests only). Claude Code specifics live in `tools/lib/cc-internals.sh`.
