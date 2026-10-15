# Adapter: Confluence (Cloud)

**Detect:** an Atlassian MCP server; `*.atlassian.net/wiki` links in READMEs or tickets.

**Access:** Atlassian MCP (preferred), else REST `https://<site>.atlassian.net/wiki/api/v2` with
basic auth `<email>:<api-token>` from `.secrets/jira-token` (same Atlassian token).

**Read-only discovery:**
- Spaces: MCP `getConfluenceSpaces` / `GET /wiki/api/v2/spaces?limit=100`.
- Team pages: CQL `type = page AND (title ~ "onboarding" OR title ~ "runbook" OR title ~ "architecture") ORDER BY lastmodified DESC`
  (MCP `searchConfluenceUsingCql`).
- Page tree of the team space: MCP `getPagesInConfluenceSpace` / `getConfluencePageDescendants`.

Record space keys and the handful of pages worth reading first (onboarding, architecture, runbooks,
release process) in `stack.md` → Wiki. Do not copy page content into business files; link it.

**Token scopes if missing:** Atlassian API token; scoped: `read:confluence-content.all`,
`read:confluence-space.summary`, `search:confluence`. Editing pages or commenting: approver only.
