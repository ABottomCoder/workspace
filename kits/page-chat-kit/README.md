# page-chat-kit

A drop-in **page-mounted chat bot**: a login-gated portal with a folded launcher (bottom-right) that
opens **1:1 chat with an agent** and a **group chat**, backed by a small Node server. The **agent**
(a Claude Code session, a bot, or any backend) receives every message from an event log and replies
in realtime with `reply.js`. Standalone: no dependency on the rest of the workspace.

## Features

- Private chat (each user and the agent) and one group chat (all users and the agent).
- Realtime over SSE; history in SQLite with scroll-up paging; speaker label and timestamp per message.
- @-mentions in the group (member picker, highlighted bubbles, unread @ badge).
- File upload (images, PDF, Office, zip, small audio/video; size cap configurable; auth-gated download).
- Login gate (accounts file) and self-service change-password.
- Optional site wrapping: reverse-proxy an existing site into an iframe behind the login gate.
- Optional outbound DLP: block agent replies containing AI-vendor names or custom terms.
- UI strings in a table (`public/strings.js`); English by default, Chinese included as a second language.

## Install

Requires Node 18+ and a C toolchain (`better-sqlite3` is native).

```bash
rsync -a --exclude node_modules ./ <your-project>/chat-portal/   # never run an instance inside the kit dir
cd <your-project>/chat-portal
cp accounts.example.json accounts.json   # users, passwords, labels, roles
cp .env.example .env                      # AGENT_KEY, AGENT_USER, BRAND, PORT ...
npm install
npm start                                 # http://0.0.0.0:<PORT>
```

Instance state (`accounts.json`, `.env`, `chat.db`, `uploads/`, `*.log`) belongs to the project that
runs it. Keep this directory code plus `*.example.*` only, so the next project does not inherit
someone else's accounts and cleaning the template never takes a live portal down.

## Two-layer login

- **Layer 1, page access (this kit).** Any URL redirects to login; nothing is visible until the
  visitor signs in with an `accounts.json` account. The agent is one of these accounts
  (`role: "agent"`, matching `AGENT_USER`); its `label` is the bot's display name.
- **Layer 2, business login (optional, not this kit).** A site wrapped with `FRONT_TARGET` keeps its
  own login inside the iframe.

## Usage: the agent side

The agent receives user messages by tailing the event log (one JSON line per message):

```bash
tail -n0 -f chat-events.log | grep --line-buffered "chat-event"
```

In Claude Code, arm that as a persistent background monitor. Fields: `id, scope, thread_user, sender,
label, content, ts, attachment, mentions, mentions_me`. A program can instead connect to
`GET /_portal/api/chat/stream` (SSE) as the agent account.

Reply:

```bash
node reply.js --private <user> "text"   # 1:1
node reply.js --group "text"            # group; write @Label to mention someone
```

`reply.js` calls `POST /_portal/api/chat/reply` with header `X-Agent-Key: $AGENT_KEY`. To send a file:
`POST /_portal/api/chat/reply-file {scope, thread_user, path, content}`.

Catch up after downtime (the tail stops when the session ends; re-arm it on resume first):

```bash
sqlite3 chat.db "SELECT id,scope,thread_user,sender,content FROM messages WHERE status='pending' ORDER BY id"
```

A user message flips to `answered` when the agent replies in that thread.

### Translating a request into setup

"Add a chat bot to this page with accounts Owner and Client, bot named Rin, everyone in the group"
means: copy the kit next to the project, put `owner`, `client` and `rin` (`role: "agent"`) in
`accounts.json`, set `AGENT_USER=rin`, and that is all for the group (there is only one, everyone is in it).

## Configuration (`.env`)

| Key | Meaning |
|---|---|
| `PORT` | listen port (default 8790, bound to 0.0.0.0) |
| `SESSION_SECRET` | 32+ random chars; omitted = random per boot (sessions drop on restart) |
| `AGENT_KEY` | shared key the agent uses to post replies; keep secret |
| `AGENT_USER` | agent account username (must exist in `accounts.json`) |
| `BRAND` | name shown on the login page and header |
| `COOKIE_SECURE` | `1` when served over HTTPS |
| `SESSION_MAX_AGE_MS` | absolute session lifetime from login (default 24h; no sliding renewal) |
| `MAX_UPLOAD_MB` | upload cap (default 50) |
| `FRONT_TARGET` | optional site to wrap (e.g. `http://localhost:3000`); empty = standalone |
| `FRAME_PATH` | initial iframe path on the wrapped site |
| `DLP_HIDE_AI_VENDORS` | `1` = block AI-vendor names in agent replies |
| `DLP_EXTRA` | comma-separated extra regex/literals to block in agent replies |

Customisation points: UI strings and default language in `public/strings.js` (copy the `en` block
to add a language); colours in `public/app.html` / `public/login.html` (main colour `#0c7d70`);
allowed upload types in `server.js` (`ALLOWED_EXT`).

## Verify after setup

- `curl http://0.0.0.0:<PORT>/_portal/api/config` returns your brand and agent user.
- A client account can sign in, send private and group messages; `chat-events.log` gets `[chat-event]` lines.
- `node reply.js --private <user> "hi"` appears live in the browser and in history.
- `@<agentLabel>` in the group yields `mentions_me: true`.
- Change-password works; old password stops working.
- With `FRONT_TARGET`: the proxied page loads in the iframe after login.

## Known limitations

- **Plaintext passwords** in `accounts.json` (admin-visible by design for a small gated portal).
  For anything beyond that, store hashes (e.g. `crypto.scrypt` with a per-user salt) and compare
  with `crypto.timingSafeEqual`; change-password writes back to the same file.
- **One global group chat.** Every account is in it; there are no per-group memberships.
- Single process, SQLite, in-memory SSE client list: not horizontally scalable.
- `better-sqlite3` is native: run `npm rebuild` after a Node major upgrade.

## Security notes

- Every chat API and the wrapped site sit behind the login gate.
- Private-thread attachments return 403 to anyone but the thread user and the agent; stored file
  names are server-generated (no path traversal).
- Posting as the agent requires `AGENT_KEY`. `reply-file` copies any local path the server can
  read, so only trusted agents should hold the key.
- Binds 0.0.0.0; expose it through a reverse proxy or tunnel with `COOKIE_SECURE=1`, never 0.0.0.0.
- DLP is a last-resort backstop for agent replies, not a substitute for the agent's own judgement.

## Platform notes

Pure Node; works on macOS and Linux. Run it under any service manager (launchd, systemd, pm2).

## API (brief)

`/_portal/api/`: `config` (public), `login`, `logout`, `me`, `change-password`, `frame`, `roster`,
`chat/history`, `chat/send`, `chat/upload`, `chat/file/:id`, `chat/reply` (agent), `chat/reply-file`
(agent), `chat/stream` (SSE).

Data model: `messages(id, scope['private'|'group'], thread_user, sender, role['user'|'assistant'],
content, attachment(JSON), mentions(JSON), created_at, status['pending'|'answered'])`. A private
thread is `scope=private, thread_user=<the human user>`.
