# botdock

Shared Slack app bots that any Claude Code session can take on by name.

Pick a free bot and tell Claude (it will ask you for the bot's two tokens):

> start slack app example

Claude reads `CLAUDE.md` here, brings the bot online under its own identity and listens for
messages: DMs from anyone, @mentions, and messages in the channels the bot has been invited to.
It treats you as the owner — only your messages are instructions — and follows `RULES.md`.

Work is organised by ticket, not by app. On your machine, `~/app_bot/work/<ticket>/` holds each
ticket's context, handoffs, data and history, whichever app worked on it; a ticket that builds on an
earlier one reads that one's folder. `~/app_bot/slack/<app>/` holds only the app's identity
(settings, tokens, logs). None of it is committed. This repo holds only what every app and every
task share: tooling, rules, templates.

## What's here

| Path | What |
|------|------|
| `RULES.md` | How every bot behaves |
| `CLAUDE.md` | The step-by-step Claude follows to start, run and stop a bot |
| `bin/botdock` | `list` / `up` / `run` / `status` / `down` / `work` / `log` / `handoff` / `close` |
| `bin/listener.js`, `bin/guardian.sh` | Slack Socket Mode listener and the guardian that keeps it alive |
| `bin/wait-event.sh` | Wakes the Claude session when a message arrives; never loses one between wakes |
| `bin/read-since.mjs`, `bin/inbox.sh`, `bin/send.js` | Read a conversation, see what arrived, reply as the bot |
| `bin/listener-guard.sh` | Optional Stop hook: a bot session can't finish a turn while it isn't listening |
| `bin/context-restore.sh` | Optional SessionStart hook: after a compaction, puts the app identity and the ticket's handoff + log back into context |
| `templates/` | App `bot.yaml`; ticket `ticket.yaml`, `CLAUDE.md`, `LOG.md`, `HANDOFF.md`; Slack app manifest; secrets format |

## Quick start

```bash
npm install
```

Then in Claude Code: "start slack app <name> for ticket <id>". Claude asks for the app's two tokens
and your Slack user id the first time. When you're done: "stop the bot" — Claude writes the ticket's
handoff first.

## Rules for maintainers

- **Nothing app- or task-specific in this repo.** Settings, contacts and context for one task live
  in that user's `~/app_bot/`. Commit only what holds for every app and every task.
- **Never commit a token.** Tokens live in the app home's `.runtime/secrets.env`. `.gitignore`
  blocks `*.env`, but check your diff anyway.
- **One app, one session.** Two listeners on the same app split its messages at random. Until the
  claim registry exists (`TODO.md`), check with colleagues before taking an app.
- Requirements: macOS or Linux, Node 20+, bash, python3, Claude Code.
