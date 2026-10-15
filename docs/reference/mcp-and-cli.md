# MCP Servers, CLI Tools, Plugins

What the framework expects to be wired up, where configuration lives, and the gotchas that transfer
between companies. Which servers a business actually uses, their sites and accounts: `business/<co>/stack.md`.

## Roles

| Role | Purpose | Portable? |
|---|---|---|
| Ticketing | fetch/update tickets, comments, transitions | per business ([ticket adapters](../process/index.md#ticket-system-adapters)) |
| Chat | search and read channels/DMs; sending follows the outward rules | per business |
| Wiki | runbooks, PRDs, design docs | per business |
| Data | warehouse/catalog queries for evidence ([data-verification.md](../process/data-verification.md)) | per business |
| Browser automation | drive and inspect live front-ends ([browser-testing.md](browser-testing.md)) | generic, carry as-is |
| Design tool | local MCP served by the desktop app (`0.0.0.0`), no company token | generic, carry as-is |

## Where configuration lives

- Repo `.mcp.json`: only generic servers (browser automation, design tool), no tokens, no absolute paths.
- Company servers: usually registered at **user scope** (`~/.claude.json`, e.g.
  `claude mcp add --transport http --scope user <name> <url>` then `/mcp` → authenticate) or by an
  external MCP manager. A folder copy of the workspace misses them; record each in `business/<co>/stack.md`
  with its config location.
- Permission allowlists for company MCP tools go in `.claude/settings.local.json` (machine), never in the
  committed settings.

## CLI tools

- Prefer the git host's CLI (`gh`, `glab`, a Bitbucket API wrapper) over the browser for PR review and
  approvals. Outside a repo dir pass the repo explicitly (`--repo <org>/<repo>`) and set the host
  variable for self-hosted instances; otherwise the CLI can hit the public host and 404 a repo you can see.
- CLI auth stored in the OS keychain persists across sessions; record the token's expiry and a one-line
  self-check (the API's "who am I" endpoint) in the business stack file.
- Interactive logins (`--web`, device flows) are completed by the human; tokens go in via `--stdin` /
  `--with-token` from a temp file removed right after, never via chat or a command-line argument.

## Plugins and skills

- Skills trigger from their descriptions; installed state is in `~/.claude/plugins/installed_plugins.json`.
  Before installing, check whether the capability is built in, and what the plugin's descriptions cost
  in context.
- Useful generic categories: office documents (xlsx/docx/pptx/pdf), Claude API reference (read before any
  Claude API coding), frontend design, webapp testing (Playwright), MCP builder, skill creator, static
  analysis (Semgrep, CodeQL, SARIF).
- **Convention:** before shipping changes to auth, billing or secrets, run a static security scan in
  high-confidence mode ("semgrep important only") on the touched repo and triage every finding.
- Record a CLI dependency next to the plugin that needs it (e.g. `semgrep` installed, `codeql` installed
  only when needed) in `user/profile.md` or the business stack file, wherever it varies.

## Gotchas that transfer

**Instances and endpoints**
- One product, several instances: mid-migration companies run legacy and new wiki/ticket instances,
  sometimes on different domains. Record each, which is current, and which server talks to which. When
  reporting that a source has nothing, name the endpoint queried.
- A legacy instance can render through browser SSO while its API returns 401 everywhere; its 404s say
  nothing about the new instance. Find a legacy link's twin by searching the title.
- Search the team's own space first. Prefer the structured query language over a metered AI search.
- Keep a fallback server disabled, not deleted, and note whether it actually works.

**Auth**
- Prefer hosted OAuth servers over static tokens. Remote servers need `type: http` and no stdio wrapper;
  old SSE endpoints get retired, so check the vendor's current URL.
- OAuth codes expire in minutes: if a flow sat across a break, start a new one. A connection-refused page
  on a `localhost` redirect is normal; the address-bar URL is what you paste back.
- Silent grant loss looks like a missing app ("not installed", empty scopes): re-authorise against the
  right site. Each grant is per site.
- Granted scopes may cover only part of a suite (e.g. wiki but not tickets, no delete tool); check before
  concluding a tool is missing. Without a delete tool, create test content as draft/private.
- Self-hosted tokens may not use the public prefix format; use them exactly as issued. Some CLIs reject
  fine-grained tokens that have the right permissions.
- On split-tunnel VPNs a server talking to an internal endpoint may need `HTTPS_PROXY` in its env;
  "connection closed" is a network path issue, not missing access.

**Writing through ticket/chat/wiki servers**
- Write in the format the API renders; re-read the rendered result; edit in place rather than duplicate.
- Wiki HTML bodies are passed raw, not HTML-escaped (escaped markup lands as literal text).
- Chat mentions need the platform user ID; confirm rendering in the real client.
- Tool names differ between server implementations (camelCase vs snake_case, different verbs); record the
  ones in use.

**Browser automation**
- The browser MCP reuses the human's logged-in sessions, which makes internal UIs reachable. Prefer CLI or
  API when both exist. Some APIs reject browser session cookies even when the UI works; then read the
  rendered DOM carefully and distrust aggregate counters.
