# Adapter: Slack

**Detect:** a Slack MCP server in `claude mcp list`; `slack` CLI installed; `*.slack.com` links in docs.

**Access:** Slack MCP (preferred) for reading; else Web API `https://slack.com/api/<method>` with a
token from `.secrets/slack-token` (`Authorization: Bearer`). Check which identity a token posts as
(`auth.test`): a user token acts as that person, so never use it to send.

**Read-only discovery:**
- Identity: `auth.test` (workspace name, own user ID).
- Members: MCP user search / `users.list` (name, display name, title, timezone, `is_bot`, deleted).
- Channels: MCP channel search / `conversations.list?types=public_channel,private_channel&exclude_archived=true`.
- Channel members for the team's channels: `conversations.members`.
- Who does what: recent history in the team's main channels (`conversations.history`, limit ~100):
  who asks, who answers, who approves deploys.

Record user IDs and channel IDs in `people.md` (business tier only).

**Token scopes if missing:** read-only bot/user token with `users:read`, `channels:read`,
`groups:read`, `channels:history`, `groups:history` (add `users:read.email` only if emails are needed).
Sending, reacting, joining channels or creating apps is outward-facing: approver only. Running a
bot for the business is a separate step (`apps/RULES.md`).
