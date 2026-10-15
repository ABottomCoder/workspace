# mcp-scaffold

A minimal remote MCP server template: Streamable HTTP transport, per-client sessions, a bearer-token
check on every `/mcp` request, and one placeholder tool (`echo`). Copy it, replace the tool, run it.

Before writing one, check whether the vendor already publishes an MCP server; wiring that into
`.mcp.json` beats re-implementing it.

## Install

Node 18+.

```bash
cp -R mcp-scaffold <your-dir> && cd <your-dir>
npm ci                                 # versions pinned in package.json / package-lock.json
cp .env.example .env                   # set MCP_AUTH_TOKEN (e.g. `openssl rand -hex 32`)
npm start                              # http://0.0.0.0:5400/mcp
node index.js --help
```

## Usage

Register with Claude Code:

```bash
claude mcp add --transport http --header "Authorization: Bearer $MCP_AUTH_TOKEN" my-tools http://0.0.0.0:5400/mcp
claude mcp list        # my-tools: ... (HTTP) - Connected
```

Or in `.mcp.json`:

```json
{ "mcpServers": { "my-tools": { "type": "http", "url": "http://0.0.0.0:5400/mcp",
  "headers": { "Authorization": "Bearer ${MCP_AUTH_TOKEN}" } } } }
```

HTTP servers coexist with stdio servers in the same `.mcp.json`.

Add a tool: in `buildServer()` call `server.registerTool(name, { title, description, inputSchema }, handler)`
with a zod schema; return `{ content: [{ type: 'text', text }] }`, or `{ isError: true, content: [...] }`
on failure. Read vendor API keys from the environment, never from tool arguments.

Raw JSON-RPC check (`initialize` returns an `Mcp-Session-Id` header to reuse):

```bash
AUTH="Authorization: Bearer $MCP_AUTH_TOKEN"; H='Accept: application/json, text/event-stream'
SID=$(curl -s -i -X POST http://0.0.0.0:5400/mcp -H "$AUTH" -H "$H" -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}' \
  | grep -i '^mcp-session-id:' | awk '{print $2}' | tr -d '\r')
curl -s -X POST http://0.0.0.0:5400/mcp -H "$AUTH" -H "$H" -H 'Content-Type: application/json' -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'
curl -s -X POST http://0.0.0.0:5400/mcp -H "$AUTH" -H "$H" -H 'Content-Type: application/json' -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"echo","arguments":{"input":"hi"}}}'
```

A request without the right token gets `401`.

## Configuration

| Env | Default | Meaning |
|---|---|---|
| `MCP_AUTH_TOKEN` | (required, 16+ chars) | shared bearer token; server refuses to start without it |
| `PORT` | `5400` | listen port |
| `HOST` | `0.0.0.0` | bind address; use `0.0.0.0` only behind TLS |

`/health` is unauthenticated and returns `{ ok, sessions }`.

## Limitations

- One shared token, no per-client identity or scopes. For multi-tenant use, put OAuth in front
  (the MCP spec's authorization flow) or map tokens to clients.
- Sessions live in memory: a restart drops them and clients re-initialize; not horizontally scalable as is.
- No rate limiting.

## Platform notes

Pure Node; macOS and Linux.
