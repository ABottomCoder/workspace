# botdock

Shared Slack app bots that any Claude Code session can take on by name.

Pick a free bot, put its tokens on your machine, and tell Claude:

> start slack app example

Claude reads `CLAUDE.md` here, brings the bot online under its own identity and listens for
messages: DMs from anyone, @mentions, and messages in the channels the bot has been invited to.
It treats you as the owner — only your messages are instructions — and follows `RULES.md`.

## What's here

| Path | What |
|------|------|
| `bots/<name>/bot.yaml` | One file per Slack app: ids, who holds it now, what it listens to. No secrets. |
| `RULES.md` | How every bot behaves |
| `CLAUDE.md` | The step-by-step Claude follows to start, run and stop a bot |
| `bin/botdock` | `list` / `up` / `run` / `status` / `down` |
| `bin/listener.js`, `bin/guardian.sh` | Slack Socket Mode listener and the guardian that keeps it alive |
| `bin/wait-event.sh` | Wakes the Claude session when a message arrives; never loses one between wakes |
| `bin/read-since.mjs`, `bin/inbox.sh`, `bin/send.js` | Read a conversation, see what arrived, reply as the bot |
| `bin/listener-guard.sh` | Optional Stop hook: a bot session can't finish a turn while it isn't listening |
| `templates/` | Slack app manifest, secrets file format |

## Quick start

```bash
npm install
bin/botdock list
mkdir -p ~/.botdock/example && cp templates/secrets.env.example ~/.botdock/example/secrets.env
chmod 600 ~/.botdock/example/secrets.env   # then paste the two tokens in
```

Then in Claude Code: "start slack app example". When you're done: "stop the bot", and set it back
to `idle` in its `bot.yaml`.

## Rules for maintainers

- **Never commit a token.** Tokens live in `~/.botdock/<name>/secrets.env` (or a secret store via
  `secrets: ssm:<prefix>`). `.gitignore` blocks `*.env`, but check your diff anyway.
- **One bot, one session.** Two listeners on the same app split its messages at random. Claim a
  bot by setting `status: in-use` and `holder:` before you start it; release it after.
- Requirements: macOS or Linux, Node 20+, bash, python3, Claude Code.
