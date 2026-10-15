# Adapter: Jira (Cloud)

**Detect:** an Atlassian MCP server in `claude mcp list`; `*.atlassian.net` links in READMEs,
commit messages or branch names (`ABC-123` pattern); `jira`/`acli` CLI installed.

**Access:** Atlassian MCP (preferred: `getAccessibleAtlassianResources` → cloud id, then the Jira
tools), else REST `https://<site>.atlassian.net/rest/api/3` with basic auth `<email>:<api-token>`
from `.secrets/jira-token`.

**Read-only discovery:**
- Sites: MCP `getAccessibleAtlassianResources`.
- Projects and key prefixes: MCP `getVisibleJiraProjects` / `GET /rest/api/3/project/search`.
- Recent activity and people: JQL `project = ABC AND updated >= -30d ORDER BY updated DESC`
  (MCP `searchJiraIssuesUsingJql` / `GET /rest/api/3/search/jql`); collect assignees and reporters.
- Workflow states: MCP `getTransitionsForJiraIssue` on one recent issue.
- The user's own open work: `assignee = currentUser() AND statusCategory != Done`.

**Infer:** ticket URL pattern, prefixes, branch naming (from git branch names containing keys),
who files vs who works tickets.

**Token to ask for if missing:** Atlassian API token for the user's account (read is governed by
the account's Jira permissions); with scoped tokens ask for `read:jira-work`, `read:jira-user`.
Writes (comments, transitions) are outward-facing: approver only.
