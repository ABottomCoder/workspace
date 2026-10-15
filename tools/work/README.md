# tools/work — work items and session binding

One tool for the two kinds of work (spec §3.3). Run `tools/work/work` with no arguments for usage.

| Kind | Where | Files |
|---|---|---|
| Project (long-lived) | `business/<co>/<project>/` | `DEVDOC.md` (gitignored in the project repo) |
| Ticket (finite) | `business/<co>/tickets/<ID>/` | `STATE.md`, `LOG.md`, `HANDOFF.md`, `history/`, `reports/`, `evidence/` |
| Cross-business item | `user/work/<slug>/` | same as a ticket |

`<ID>` is the ticket-system ID as written (`ABC-18`, `2233`), else a short kebab description.

## Session binding

`work attach <target>` writes `user/sessions/.bindings/<session_id>`:

```
target=business/acme/tickets/ABC-18
attached=2026-10-14T09:30Z
```

Paths are relative to the main dir, so bindings survive a machine move. The session id comes from
`$CLAUDE_CODE_SESSION_ID` (set inside Claude Code Bash calls; `$CLAUDE_SESSION_ID` also accepted),
else the newest transcript in the main dir's transcript dir (with a warning). Rollover copies the
binding to the new session.

`work restore` is the SessionStart hook (`startup|resume|compact|clear`). Bound to a project: injects
`DEVDOC.md`. Bound to a ticket: `STATE.md` (≤ 2.5 KB) + `HANDOFF.md` (≤ 3 KB) + as much of the
`LOG.md` tail as fits. Total ≤ 9.5 KB (the hook output cap is 10 KB). Unbound: a one-line routing
reminder only.

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
- `work handoff [<target>]` (tickets only) archives a filled `HANDOFF.md` to `history/handoff-<stamp>.md`
  and leaves a fresh copy.

## Templates

`work new-ticket` and `work attach` (project without a `DEVDOC.md`) copy from `templates/ticket/`
and `templates/project/DEVDOC.md` when present, replacing `{{ID}} {{TITLE}} {{PROJECT}} {{DATE}}
{{BUSINESS}}`; otherwise they write the minimal files above.

## Portability

bash 3.2+ and python3. `WORK_ROOT` overrides the main dir (tests only); `CC_PROJECTS_BASE` overrides
`~/.claude/projects` (tests only). Claude Code specifics live in `tools/lib/cc-internals.sh`.
