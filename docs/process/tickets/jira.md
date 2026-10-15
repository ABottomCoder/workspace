# Ticket-system adapter: Jira

Instance values (site, cloud id, project keys, custom field ids) live in `business/<co>/stack.md`.

## Recognise
- ID: `<PROJECT>-<number>` (e.g. `ABC-123`). URL: `https://<site>/browse/<ID>`.

## Access
- **Preferred:** the vendor's hosted OAuth MCP server (no long-lived token on disk, refreshed by the
  client). Remote servers need `type: http` in the client config; register at user scope if every session
  needs it. Each OAuth grant is per site: pick the right site on the consent screen.
- **Fallback:** REST API v3 with an API token (`Authorization: Basic base64(email:token)`) stored in
  `business/<co>/.secrets/`. Some self-hosted instances issue tokens without the public prefix format;
  use the token exactly as issued.
- Granted scopes vary per server: check whether the grant covers Jira, Confluence or both before
  concluding a tool is missing. An expired grant can surface as "app is not installed" with empty
  scopes; re-authorise rather than falling back to a stored token.

## Fetch
- MCP: the get-issue tool with the ID. REST: `GET /rest/api/3/issue/<ID>?expand=renderedFields`.

| Standard field | Jira field |
|---|---|
| Title | `fields.summary` |
| Description | `fields.description` (ADF in v3; `renderedFields.description` for HTML) |
| Status | `fields.status.name` |
| Assignee | `fields.assignee.displayName` / `.emailAddress` |
| Priority | `fields.priority.name` |
| Acceptance criteria | description section or a custom field (`customfield_<n>`, per instance) |
| Comments | `fields.comment.comments[]` |
| Links / parent / subtasks | `fields.issuelinks`, `fields.parent`, `fields.subtasks` |
| Estimate / logged | `fields.timetracking.originalEstimate` / `.timeSpent` |

## Search
- JQL: `parent = <EPIC>`, `text ~ "<key noun>" ORDER BY updated DESC`, `component = <c>`,
  `issue in linkedIssues(<ID>)`. Prefer JQL over a metered "AI search" tool.

## Write (with authorisation)
- Comment through the MCP or `POST /rest/api/3/issue/<ID>/comment`. Write in the format the API actually
  renders: an endpoint that accepts markdown may also accept wiki markup, post it successfully and render
  it literally. Re-read the rendered comment; fix by editing in place, not by posting a duplicate.
- Markdown traps: a leading underscore inside inline code read as italics; literal `[...]` parsed as a
  link; a table cell starting with `1.` turned into a list.
- Transitions: list them first (`GET …/transitions`), then post the id.

## Gotchas
- **Look-alike custom fields.** Jira ships near-identical fields per project type (story points is the
  classic). A 2xx and a read-back of the field you wrote prove nothing; check which field the board's
  configuration reads, or compare with a neighbouring issue you didn't create.
- **Two instances mid-migration.** A legacy site may render through SSO in the browser while its API
  returns 401; IDs differ between instances. Find a pasted legacy link's twin by searching the title on
  the current instance, and name the instance whenever you report "nothing found".
- Confluence via the same vendor MCP: pass HTML bodies raw (don't HTML-escape them); some grants have no
  delete tool, so create test pages as drafts / private.
