# apps — chat apps run from a Claude Code session

An **app** is a chat bot (Slack today; other channels are parallel adapters) that a Claude Code
session in the main dir takes over by name. It is a teammate with a name — no persona. Conduct:
**`RULES.md`** (read it before running one). Channel contract: **`channels/README.md`**.

## Where things live

| What | Where |
|------|-------|
| Code, rules, templates (shared by every business) | `apps/` (this dir, in the framework repo) |
| One app's config | `business/<co>/apps/<channel>_<name>/app.yaml` (template: `templates/app.yaml`) |
| Its runtime state: listener log, offsets, cursors, owner, `.session-id`, current ticket | `business/<co>/apps/<id>/.runtime/` |
| Its credentials (mode 600, never printed) | `business/<co>/.secrets/apps/<id>.env` |
| The work: one dir per ticket, whichever app worked on it | `business/<co>/tickets/<ID>/` (shared ticket model, `tools/work/`) |

`<id>` is `<channel>_<name>` (e.g. `slack_helper`). Commands accept the bare name when unique;
pass `--business <co>` when two businesses have an app of that name.

```
apps/
├── bin/        app (CLI) · guardian.sh · wait-event.sh · inbox.sh · listener-guard.sh ·
│               context-restore.sh · lib.sh · service.<platform>.sh
├── channels/   README.md (contract) · slack/ (listen, send, read-since, react, validate-creds, manifest)
├── templates/  app.yaml
├── skill/      SKILL.md (installed as .claude/skills/app/)
└── RULES.md
```

Requirements: Node 20+, bash, python3, `lsof`, `pgrep`. First time: `cd apps && npm install`.

## Take over an app — "use slack_helper to run this session"

1. **Find it.** `apps/bin/app list` — the app must exist under `business/*/apps/`. Several
   matches: ask which business. None: `app new <co> <id>`, then the user supplies credentials
   into `business/<co>/.secrets/apps/<id>.env` (format: `channels/<channel>/secrets.env.example`).
2. **Read** `apps/RULES.md` and the app's `app.yaml`.
3. **Free?** One app = one listener = one session. Two listeners on one app split its messages at
   random. `app up` refuses when another session holds the app with a live read end; across
   machines, ask the user to confirm nobody else runs it.
4. **Up.** `apps/bin/app up <id> [--owner <chat user id>]` — checks credentials with the channel,
   writes `.runtime/`, registers this session (`.session-id`) as the owner session. Owner = whose
   messages are instructions (default: `owner:` in app.yaml).
5. **Write end.** If the service is installed, `up` starts it. Otherwise Bash with
   `run_in_background: true`: `apps/bin/app run <co>/<id>`.
6. **Read end.** Bash with `run_in_background: true`: `apps/bin/wait-event.sh <co>/<id>`. Use the
   tool parameter, never a trailing `&` (the process would leave the session and you'd hear nothing).
7. **Ticket.** Ask which ticket this session is for (ticket-system ID, or a short kebab name), then
   `app work <id> <ticket> [--title "…"] [--depends t1,t2]` and read what it lists.
8. **Name the session** `<Desc>_<channel>_<name>_<n>`: `app name-session <id> <Desc>` (Desc = the
   project or ticket, no underscores; n counts up). If it cannot write the title it prints the
   name for `/rename`.
9. **Verify.** `app status <id>` → listener `1`, heartbeat < ~90 s, reader `ok`, verdict `UP`. Ask
   the owner to DM the app one word to prove the receive path end to end.

## While running — the loop

- `wait-event.sh` exits when something arrives; that exit is what wakes the session. **First action
  of every wake: re-arm it (run_in_background)**, then handle. Nothing is lost in between — it
  resumes from a saved byte offset.
- Exit codes: `0` event or catch-up batch printed · `1`/`2` re-run quietly · `3` the listener's
  heartbeat is stale (the app was deaf): re-run, `app read` your conversations, tell the owner in one line.
- `[catchup …]` lines are messages recovered after a listener reconnect; old batches are flagged —
  check they were not handled already.
- What woke you: `app inbox <id>` (every event, thread replies included, with the thread to answer in).
- Conversation: `app read <id> <conv>` — read before replying; it advances the cursor.
- Reply: `app send <id> --conv <c> --thread <ts> --file msg.txt` (or `--stdin`; `--upload <path>` for
  files). Answer in the thread the message came from.
- Ack before long work, progress, result — `RULES.md` §4.
- Log as you go: `app log <id> "…"` (the current ticket's `LOG.md`); refresh the app's
  handoff at milestones: `handoff/<id>.md` in the ticket (the app is a role; `app handoff <id>` creates it). Durable context goes into the ticket dir, not the app dir.
- Switching ticket mid-session: write the handoff first, then `app work <id> <other>`.

## Stop

1. Update `handoff/<id>.md` in the ticket (done, in progress, waiting on, promised, next step), then `app handoff <id>`.
2. Ticket finished? `app close <id>`, then publish a summary where the team reads it.
3. `app down <id>` (skip when only compacting).

## Hooks (registered in `.claude/settings.json`)

Both exit 0 with no output when the session is not an app session.
- `apps/bin/context-restore.sh` — SessionStart `compact|resume`: re-injects identity, read-end
  reminder, and (when `tools/work/restore` is absent) the ticket's HANDOFF + LOG tail.
- `apps/bin/listener-guard.sh` — Stop: an app session cannot end a turn while its own read end is
  not running.

## Health checks

`app status [--live]`: verdicts `UP`, `DOWN` (no listener), `SPLIT` (two listeners — stop one
now), `STALE` (heartbeat old), `DEAF` (listener fine, no read end — messages pile up unanswered).
Checking is read-only: never stop or restart an app another session owns; tell its owner.

## Service (optional, per app, only on the user's request)

`app install-service <id>` runs the write end under the platform service manager so it survives
session exits, sleep and reboots (`bin/service.mac-launchd.sh`; Linux slot
`bin/service.linux-systemd.sh`). See `docs/compatibility.md`. `app uninstall-service <id>` undoes it.

## New Slack app

Create it from `channels/slack/manifest.yaml` (rename first), generate the app-level token
(`connections:write`), install to the workspace, copy the bot token into the app's `.secrets` file.
Credentials never go into this repo.
