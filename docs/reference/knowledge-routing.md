# Knowledge routing — where to put what

One fact, one home; everywhere else holds a pointer. Before writing anything persistent ask: who needs to
read this, in what situation?

| Content | Home |
|---|---|
| Agent-behaviour truths that hold anywhere | `lessons/<category>.md`, `docs/principles/` |
| This user's preferences, taste, persona | `user/profile.md`, `user/lessons.md`, `user/persona.md` |
| Company people, roles, authority | `business/<co>/people.md` |
| Company systems, environments, MCPs, project state policy | `business/<co>/stack.md` |
| Company-specific lessons | `business/<co>/lessons.md` |
| Repo knowledge (build, architecture, gotchas, run book) | `business/<co>/<project>/CLAUDE.md` |
| Project live state | the project state file: `DEVDOC.md`, `.state/DEVDOC.md` or `docs/HANDOFF.md` (`tools/work/README.md` → Project state policy) |
| Ticket state, spec, reports, evidence | `business/<co>/tickets/<ID>/` (ID as in the ticket system, else short kebab description) |
| Non-ticket deliverables, research, recaps | `business/<co>/docs/<topic>/` |
| Cross-business work items | `user/work/<slug>/` |
| Daily log | `user/logs/YYYYMMDD.log`, lines prefixed with the business |
| Daily journal (what happened each day, written from transcripts) | `user/logs/journal/YYYY-MM.md` (`tools/sessions/journal_catchup.py`) |
| Auto-memory (`user/memory/`) | pointers and what fits nowhere else; never business facts |

A lesson that still holds with the business details removed is promoted to `lessons/` with a pointer left
behind (the business file keeps the dated incident record).
