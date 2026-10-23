# slack-app-provision

Scripts that create a Slack app from a manifest and read back its tokens by driving the
api.slack.com web UI, for when you need several near-identical bot apps (e.g. one Socket Mode
app per agent) and clicking through the UI each time is the bottleneck.

> **Warning: this drives a real, logged-in browser.** The scripts attach to a Chrome you started
> with `--remote-debugging-port` and act as whoever is signed in there: they create apps in a
> workspace and read secrets off the page. Anyone who can reach the debugging port controls that
> browser session, so bind it to localhost and close it afterwards. Prefer the official
> [App Manifest API](https://api.slack.com/reference/manifests) (`apps.manifest.create` with an
> app configuration token) when it covers your case; this kit is for when it does not.

## Install

Node 18+ and Google Chrome.

```bash
npm install                     # playwright-core only; no browser download (it attaches to your Chrome)
```

Start a separate Chrome profile with a debugging port and sign in to api.slack.com in it:

```bash
# macOS
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-slackauto"
# Linux
google-chrome --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-slackauto"
```

## Usage

```bash
node create-app.mjs MyBot mybot "my workspace"         # prints FINAL-URL with the new app id
node nav.mjs https://api.slack.com/apps/<APP_ID>/general basic-info
#   click "Generate Token and Scopes" (or: node step.mjs s1 click="Generate Token")
node gen-token.mjs --out mybot.xapp.token              # app-level token (connections:write)
#   install the app to the workspace (OAuth & Permissions > Install), approve
node read-xoxb.mjs <APP_ID> --out mybot.xoxb.token     # bot token
```

- `create-app.mjs <AppName> <displayname> <workspace-regex> [--manifest file.json] [--dry-run]`:
  default manifest is a Socket Mode bot receiving `app_mention` and `message.im`, with scopes to
  read mentions/DMs, post, and look up users and channels. Pass `--manifest` for your own.
  `--dry-run` walks to the review step and closes it without creating, to check the selectors.
  Handles both the current create flow (pick "From a manifest" → Continue → editor and workspace
  on one step) and the older one (workspace first, editor after Next).
- `gen-token.mjs [--name socket] [--out file]`: run with the token modal open.
- `read-xoxb.mjs <APP_ID> [--out file]`: the app must be installed.
- `nav.mjs <url|stay> [shot]`: navigate and screenshot, for checking state.
- `step.mjs <shot> <action>...`: generic steps for whatever the scripts above miss:
  `click=<text>`, `clickrole=<role>:<regex>`, `type=<text>`, `file=<path>`, `selectall`, `del`,
  `press=<Key>`, `goto=<url>`, `wait=<ms>`.

Tokens: with `--out` they are written to a mode-600 file and only a prefix is printed; without it
they go to stdout (with a warning). Move them into your secrets store and delete the files.

## Configuration

| Env | Default | Meaning |
|---|---|---|
| `CDP_URL` | `http://localhost:9222` | Chrome debugging endpoint |
| `SLACKAUTO_SHOTS` | `./shots` | screenshot directory (created if missing) |

Screenshots are taken at each step for debugging. They can show workspace names, app ids and, for
`step.mjs`, anything on screen including secrets: keep the directory out of git (`.gitignore`
covers `shots/`) and delete it when done.

## Platform notes

macOS and Linux (only the Chrome launch command differs). Selectors follow the api.slack.com UI
as of when the scripts were written; when Slack changes the page, a step fails with
`STEP-FAILED` and an `ERROR` screenshot. Fix the selector, or finish by hand with `step.mjs`.
