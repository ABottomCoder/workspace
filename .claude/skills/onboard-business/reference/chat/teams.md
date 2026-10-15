# Adapter: Microsoft Teams

**Detect:** a Teams / Microsoft 365 MCP server in `claude mcp list`; `az` CLI logged in to the
company tenant (`az account show`); `teams.microsoft.com` links in docs.

**Access:** MCP if configured; else Microsoft Graph `https://graph.microsoft.com/v1.0` with a
delegated token (`az account get-access-token --resource https://graph.microsoft.com`; do not print it).

**Read-only discovery:**
- Me: `GET /me` (display name, mail, id).
- Teams: `GET /me/joinedTeams`.
- Channels: `GET /teams/{id}/channels`.
- Members: `GET /teams/{id}/members` (name, roles: owner/member).
- Org chart hints: `GET /me/manager`, `GET /users/{id}/directReports`.

**Delegated permissions to ask for if missing:** `User.Read`, `Team.ReadBasic.All`,
`Channel.ReadBasic.All`, `TeamMember.Read.All`; `ChannelMessage.Read.All` only if reading history
is needed (usually requires admin consent; ask, don't assume). Posting is outward-facing: approver only.
