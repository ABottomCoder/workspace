# Process: index

How work moves from request to done. The tier (light by default, heavy opt-in) is set in
`business/<co>/CLAUDE.md`.

| File | What | Read when |
|---|---|---|
| [light-track.md](light-track.md) | The default process: route, plan non-trivial work, keep state in files, log as you go | start of any work |
| [heavy-track.md](heavy-track.md) | What heavy tier adds (ticket comments, reports, independent QA, intervention log) | business has `tier: heavy`, or the user asks for a heavy step |
| [ticket-lifecycle.md](ticket-lifecycle.md) | Ticket dir model, intake → development → reporting, rework, handoff/resume, multi-session rules | a ticket number arrives; resuming or handing off a ticket |
| [reporting.md](reporting.md) | Report files, style, inlined evidence, no self-auditing, metadata | writing any test or ticket report |
| [pr-review.md](pr-review.md) | Reviewing someone else's PR: staleness, baselines, six-lens hunt, evidence gate, comment format | asked to review a PR |
| [qa-session.md](qa-session.md) | Being the independent QA session: independence, pairing, AC table, sign-off, 20 failure modes | made QA for a ticket (`/qa <ID>`) |
| [intervention-tracking.md](intervention-tracking.md) | `// fix:[category]` autonomy measurement, taxonomy, scan-based mode | ticket close in heavy tier; periodic self-review |
| [multi-agent-harness.md](multi-agent-harness.md) | Author ↔ critics harness: design, run, verify, scanner interface | the user explicitly asks for the harness |
| [data-verification.md](data-verification.md) | Answer data questions by measuring: access, standing read-only authorisation, PII, query traps | any question about what data contains, or "I'd need prod access" |
| [branching-and-merge.md](branching-and-merge.md) | Git Flow roles, merge method per PR type, writing the PR description, what makes a useful repo row | release/branch/merge questions; choosing a PR base; writing a PR |

## Ticket-system adapters

One file per system in [tickets/](tickets/); `business/<co>/stack.md` names the one in use.
Business-specific systems (an internal platform) get their adapter in `business/<co>/docs/tickets/`.

| File | What |
|---|---|
| [tickets/_template.md](tickets/_template.md) | Adapter contract: recognise, access, fetch + field mapping, search, write, gotchas |
| [tickets/jira.md](tickets/jira.md) | Jira via hosted OAuth MCP or REST v3; JQL; rendering and custom-field traps |
| [tickets/github-issues.md](tickets/github-issues.md) | GitHub Issues via `gh`; host detection; ticket dir naming |
