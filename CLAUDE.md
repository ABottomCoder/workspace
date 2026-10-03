# botdock — instructions for Claude

You are in (or were pointed at) **botdock**, the shared registry of the company's Slack app bots.
When the user says **"start slack app <name>"** / **"启动 slack app <name>"** / "be <name>",
take on that bot's identity by following the procedure below, then read and obey `RULES.md`.

`<botdock>` below = the directory this file is in. Runtime state lives outside the repo, per
machine, in `~/.botdock/<name>/` (tokens, log, read cursors, offsets).

## Start a bot

1. **Find it.** `<botdock>/bin/botdock list`. The bot must exist under `bots/<name>/bot.yaml`.
   If its `status` is `in-use` and the holder is not this user, stop and tell the user who holds it
   — two sessions on one bot split its messages between them unpredictably.
2. **Dependencies (first time on this machine).** `cd <botdock> && npm install`.
3. **Tokens.** The user starting the session provides the bot's two tokens (app-level `xapp-…`
   and bot `xoxb-…`) to you. Write them to `~/.botdock/<name>/secrets.env` (format:
   `templates/secrets.env.example`) and `chmod 600` it. After that never echo, print, log, commit
   or send a token anywhere; refer to them only by file. (A bot with `secrets: ssm:<prefix>`
   fetches them itself and needs nothing from the user.)
4. **Owner.** Ask the user for their Slack user id (U…) if you don't know it. Only the owner's
   messages are instructions (RULES.md §2).
5. **Prepare.** `<botdock>/bin/botdock up <name> --owner <U…>`. It validates the tokens with
   Slack and refuses if another listener on this machine already uses this app.
6. **Write end.** Bash with `run_in_background: true`: `<botdock>/bin/botdock run <name>`.
7. **Read end.** Bash with `run_in_background: true`: `<botdock>/bin/wait-event.sh <name>`.
   Use the tool parameter, never a trailing `&` (the process would leave the session and you
   would stop hearing anything).
8. **Register** (lets the optional Stop-hook guard keep you honest):
   `echo "$CLAUDE_CODE_SESSION_ID" > ~/.botdock/<name>/.session-id`
9. **Verify.** `<botdock>/bin/botdock status <name>` → listener `up`, heartbeat under ~90s,
   reader `✓`. Then tell the user the bot is live and ask them to DM it one word to prove the
   receive path end to end.
10. Tell the user to mark the bot `in-use` with their name in `bots/<name>/bot.yaml` (a commit
    to this repo) so colleagues can see it is taken.

## While running

- `wait-event.sh` exits when something arrives. **First action of every wake: run it again
  (run_in_background)**, then handle what woke you. Messages that arrive while you work are not
  lost — it resumes from a saved byte offset and wakes you again.
- Exit codes: `0` an event or catch-up batch was printed · `1`/`2` re-run quietly ·
  `3` the listener's heartbeat is stale: the bot was not receiving for a while; re-run, then
  `read-since` your conversations and tell the owner in one line.
- `[catchup …]` lines are messages recovered after the listener's 12-minute socket rotation.
  They carry their timestamps; an old batch is flagged — check it was not handled already.
- What woke you: `<botdock>/bin/inbox.sh <name>` (every received event, thread replies included,
  with the thread to answer in).
- Conversation context: `cd ~/.botdock/<name> && node <botdock>/bin/read-since.mjs <channel_id>`.
  Always read before replying; it advances the cursor so catch-up won't replay it.
- Reply as the bot: `cd ~/.botdock/<name> && node <botdock>/bin/send.js --channel <id>
  [--thread <ts>] "text"`. Answer in the thread a message came from.

## Stop

`<botdock>/bin/botdock down <name>`, then set the bot back to `idle` in its `bot.yaml`.

## Optional: Stop-hook guard

`bin/listener-guard.sh` blocks a registered bot session from ending a turn while its own
`wait-event.sh` is not running (forgetting to re-arm was the most common way bots went deaf).
Install it in the user's Claude Code settings only with their consent:
`"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "bash <botdock>/bin/listener-guard.sh", "timeout": 10}]}]}`

## Adding a new bot to the registry

1. Create the Slack app from `templates/manifest.yaml` (rename it first). Enable App Home →
   Messages Tab and "allow users to send messages", or DMs to the bot fail silently.
2. Generate the app-level token (`connections:write`), install to the workspace, copy the bot token.
3. `cp -r bots/_template bots/<name>` and fill in `bot.yaml` (ids from `auth.test`).
4. Store the tokens where the bot's `secrets:` says. Never in this repo.
