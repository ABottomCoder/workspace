# qq — QQ adapter (OneBot v11)

Talks to a **local OneBot v11 endpoint** that holds the QQ login: NapCat in Docker, managed by
`napcat.sh`. Unofficial protocol: use a dedicated account, never a personal main account. A brand
new account logging in from a server or foreign IP is often frozen at once (seen in practice);
an older, normally used account is far safer. The official QQ bot API would be a separate adapter
(not built: individual registration needs mainland real-name verification, and group use without
@ is unclear).

## Start: "启动qq机器人，使用 <QQ号>" / "start the qq bot with account <n>"

Run from the main dir, in the session that asked. Nothing auto-starts; the bot lives as long as
that session's background tasks.

1. `apps/channels/qq/napcat.sh up <QQ号>`: finds the app by `qq_account:`, starts its NapCat
   container, waits for the login. If it prints "QR login needed", tell the user to scan the
   opened `qrcode.png` with that account's phone QQ and wait (3 min). Don't loop on failures: a
   frozen account must be unlocked by the user on the phone first.
2. `apps/bin/app up <co>/<id>` (owner comes from `app.yaml`).
3. `run_in_background`: `apps/bin/app run <co>/<id>` (write end: listener + transcript).
4. Persona app (`persona:` set): `run_in_background`: `apps/bin/app session <co>/<id> --headless`,
   the restricted session that chats (apps/RULES.md §12). Its transcript:
   `<app dir>/.runtime/session/out.jsonl`. If the user wants to watch it instead, they run
   `apps/bin/app session <co>/<id>` in their own terminal and you skip this step.
   A plain work app (no persona) is run by this session itself: `.claude/skills/app`.
5. Check: `apps/bin/app status <co>/<id>` shows UP; tell the user it is live.

**Stop** ("停止qq机器人"): `apps/bin/app down <co>/<id>` (listener, read end, persona session),
then `apps/channels/qq/napcat.sh down <QQ号>`. The login is kept for next time.

**Test sends** go to the owner in private (`app send <co>/<id> --conv u<owner qq> "…"`), never
to the group unless the user asks.

## New QQ app (once per account)

1. `apps/bin/app new <co> qq_<name>`; in `app.yaml`: `qq_account:`, `owner:` (the user's own QQ),
   `listen_convs: g<group id>` (only that group reaches the app), `listen_types:
   app_mention,channel_message` (no private chats), `ack_reaction:` empty; persona apps also
   `persona: persona.md`, `memory: on`, `trigger_words:` (names that count as addressing it).
2. Credentials `business/<co>/.secrets/apps/qq_<name>.env` (600), keys in `secrets.env.example`:
   pick two free localhost ports (3000 is often taken) and a token (`openssl rand -hex 24`).
3. `napcat.sh up <QQ号>` writes the OneBot config (HTTP + forward WS, token) and creates the
   container (`napcat-<name>`, ports bound to 127.0.0.1, login data in `<app dir>/napcat/`).
4. Add the account to the group from a phone; then start as above.

## Behaviour

- Every message in a listened group goes to the transcript (`<app dir>/memory/raw/YYYY-MM-DD.jsonl`
  with `memory: on`, else `.runtime/transcript/`). Messages from the gap after a reconnect are
  backfilled (no wake).
- The session is woken once per burst (debounce `debounce_ms`, default 3 s): `app_mention` when
  @-mentioned, replied to, or named (`trigger_words`), else `channel_message`, and the persona
  session decides whether to join.
- `send`: quote-reply (`--thread <message id>`), `--at`, `--image <https url>`; capped by
  `send_cap_per_hour` (default 30) as a runaway fuse.
- Memory digests (`days/`, `members/`, `group.md`) are written in the background for past days
  while a persona session runs (`app-mcp.mjs`); `app digest <co>/<id> [date]` does one by hand.

## Files

`onebot.mjs` (HTTP calls, segment rendering, transcript), `listen.js`, `send.js`, `read-since.mjs`,
`validate-creds.mjs` (contract verbs, `../README.md`), `napcat.sh` (endpoint), `secrets.env.example`.
