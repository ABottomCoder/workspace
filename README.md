# botdock

Shared Slack app bots that any Claude Code session can take on by name.

Pick a free bot and tell Claude (it will ask you for the bot's two tokens):

> start slack app example

Claude reads `CLAUDE.md` here, brings the bot online under its own identity and listens for
messages: DMs from anyone, @mentions, and messages in the channels the bot has been invited to.
It treats you as the owner — only your messages are instructions — and follows `RULES.md`.

Each app you use gets a home on your machine, `~/app_bot/slack/<name>/`: its settings, what you
are using it for, handoffs between sessions, history, tokens and logs. That is yours and is never
committed. This repo holds only what every app and every task share: tooling, rules, templates.

## What's here

| Path | What |
|------|------|
| `RULES.md` | How every bot behaves |
| `CLAUDE.md` | The step-by-step Claude follows to start, run and stop a bot |
| `bin/botdock` | `list` / `up` / `run` / `status` / `down` / `handoff` |
| `bin/listener.js`, `bin/guardian.sh` | Slack Socket Mode listener and the guardian that keeps it alive |
| `bin/wait-event.sh` | Wakes the Claude session when a message arrives; never loses one between wakes |
| `bin/read-since.mjs`, `bin/inbox.sh`, `bin/send.js` | Read a conversation, see what arrived, reply as the bot |
| `bin/listener-guard.sh` | Optional Stop hook: a bot session can't finish a turn while it isn't listening |
| `templates/` | App home files (`bot.yaml`, `CLAUDE.md`, `HANDOFF.md`), Slack app manifest, secrets format |

## Quick start

```bash
npm install
```

Then in Claude Code: "start slack app <name>". Claude asks for the app's two tokens and your Slack
user id the first time. When you're done: "stop the bot" — Claude writes a handoff first.

## Rules for maintainers

- **Nothing app- or task-specific in this repo.** Settings, contacts and context for one app on one
  task live in that user's app home. Commit only what holds for every app and every task.
- **Never commit a token.** Tokens live in the app home's `.runtime/secrets.env`. `.gitignore`
  blocks `*.env`, but check your diff anyway.
- **One app, one session.** Two listeners on the same app split its messages at random. Until the
  claim registry exists (`TODO.md`), check with colleagues before taking an app.
- Requirements: macOS or Linux, Node 20+, bash, python3, Claude Code.
