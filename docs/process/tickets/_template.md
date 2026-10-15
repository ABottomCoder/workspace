# Ticket-system adapter: <system name>

Copy this file to `<system>.md` (framework, generic) when adding support for a new ticket system.
Instance values (base URL, project keys, custom field ids, tokens) never go here; they go in
`business/<co>/stack.md` (facts) and `business/<co>/.secrets/` (credentials). `business/<co>/stack.md`
names which adapter the business uses.

## Recognise
- ID pattern (e.g. `ABC-123`, `#123`) and URL forms that arrive in chat; how to build the URL from an ID.

## Access
- Preferred route: MCP server / CLI / REST API, in that order of preference, and why.
- Auth: OAuth, API token, session token; where the credential lives (by name); expiry; what a 401/403
  means and the fallback (ask the approver for a fresh credential; never persist short-lived tokens
  outside `.secrets/`, never in docs or memory).

## Fetch (Phase 1)
Command or tool call, and the field mapping:

| Standard field | Field path in this system |
|---|---|
| Title | |
| Description | |
| Status | |
| Assignee (name, email) | |
| Priority | |
| Acceptance criteria | (often in the description or a custom field) |
| Comments | |
| Linked issues / parent / subtasks | |
| Estimate / time logged | |

## Search (context sweep)
- Query language and the queries that find surrounding work (same epic, key nouns, same component).

## Write (only with authorisation)
- Post a comment (format the API actually renders), edit a comment in place, transition status, set
  fields. Re-read the rendered result after writing; confirm consumer-visible fields from the consumer's
  side ([verification-antipatterns.md](../../principles/verification-antipatterns.md) §24).

## Gotchas
- Append-only list of instance-independent traps for this system.
