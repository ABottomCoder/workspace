---
id: <ticket ID or kebab slug>
title: <one line>
status: open            # open | active | review | blocked | closed
project: <project dir name, or none>
tier: light             # inherited from business CLAUDE.md unless overridden
opened: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
closed:
---

# <id>: <title>

> Current facts about this work item. `tools/work/index` reads the front matter to build
> `tickets/INDEX.md`; keep it accurate. History goes in `LOG.md`, resume point in `HANDOFF.md`.

## Links

- Ticket: <URL in the ticket system, or "none">
- Repo(s) @ base branch: <repo @ main>
- Branch: <feature branch>
- PR: <URL, or "not opened">
- Spec: `spec.md` (only for non-trivial work)

## Acceptance criteria

Each one testable (a command, a request, an observable UI state):

- [ ] 
- [ ] 

## Who

- Requested by: <name / role>
- Authorised by: <approver or delegate, with source>
- Reviewer / QA: <name or "self">
