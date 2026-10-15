# Browser Testing

Frontend verification and E2E checks. Product-specific selectors, test accounts and login recipes go in
the project `CLAUDE.md`; this is the transferable part. Evidence (screenshots, videos) goes to the
ticket's `evidence/` and is embedded in reports as data URIs ([reporting.md](../process/reporting.md)).

## Choosing a tool

| Tool | Type | Strengths | Weaknesses | Best for |
|---|---|---|---|---|
| Chrome DevTools MCP | MCP server | pre-built tools (~40–90% fewer tokens than generated scripts), live DOM, network/console inspection, can reuse login sessions | Chrome only, no video | quick UI checks, screenshots, debugging, network/console |
| Playwright | library (Node/Python) | multi-browser, auto-wait, video/trace, codegen, headless | install and scripting cost | complex flows (loops, conditionals), video evidence, CI |
| browser-use | AI agent framework | natural-language actions | slow, costly, non-deterministic | open-ended exploration |
| Puppeteer | library (Node) | light, direct CDP | no auto-wait | Chrome scripting, PDFs |
| Cypress | framework | time-travel debugging, retrying assertions | single origin/tab | component and single-app E2E |
| Selenium | framework | widest browser and language support | slow, verbose, flaky without explicit waits | legacy suites |

Default: DevTools MCP for simple interactions, Playwright for complex programmatic flows. Start the
browser yourself when testing needs it; don't ask the user to.

## Chrome DevTools MCP

Repo `.mcp.json` (no absolute paths; if the default Node is older than 20.19, point `command` at a newer
`npx` in the machine-local config instead):

```json
{ "mcpServers": { "chrome-devtools": { "command": "npx", "args": ["-y", "chrome-devtools-mcp@latest", "--autoConnect"] } } }
```

`--autoConnect` looks for `DevToolsActivePort` in the **default** Chrome profile directory. Launching with
a custom `--user-data-dir` writes the port file there instead, and the MCP fails with "Could not find
DevToolsActivePort". Recipe:

### Launch recipe (variant: mac)

```bash
pkill -9 -f "Google Chrome"; sleep 3                       # all Chrome instances must be closed
CH="$HOME/Library/Application Support/Google/Chrome"
rm -f "$CH/SingletonLock" "$CH/DevToolsActivePort"
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug-profile &
sleep 5; curl -s http://localhost:9222/json/version         # port must answer
WS=$(curl -s http://localhost:9222/json/version | python3 -c "import sys,json;print(json.load(sys.stdin)['webSocketDebuggerUrl'].split('/')[-1])")
printf "9222\n/devtools/browser/%s" "$WS" > "$CH/DevToolsActivePort"   # let autoConnect find it
# then: list_pages via the MCP should return the page list
```

Linux variant: not written yet (profile dir `~/.config/google-chrome`, binary `google-chrome`); untested.
See `docs/compatibility.md`.

The temporary profile has no login state: ask the user to log in, or inject a session token with
`evaluate_script` (`localStorage.setItem('<key>', '<token>')`) where the app supports it. Killing all
Chrome closes the user's own windows; say so first if they may be using it.

Tools: `navigate_page`, `click`, `fill`, `fill_form`, `hover`, `type_text`, `press_key`,
`take_screenshot`, `take_snapshot`, `evaluate_script`, `list_network_requests`, `get_network_request`,
`list_console_messages`, `lighthouse_audit`, performance traces.

If the MCP can't attach because a browser already owns its profile, talk to that browser's debugging port
directly; a reused evaluation context keeps top-level `const` bindings, so wrap snippets in an IIFE.

## Playwright

```bash
npm install playwright && npx playwright install chromium     # in the project, not the framework root
```

| Task | How |
|---|---|
| Navigate | `page.goto(url, { waitUntil: 'domcontentloaded' })`; SPAs often never reach `networkidle` |
| Wait for render | an explicit wait for a selector; a fixed `waitForTimeout` only as a last resort |
| Click / fill | `page.click('text=Label')`, `page.locator('input[placeholder="…"]').fill(v)` |
| Rich-text editor | click the editor container with `{ force: true }` (the placeholder element intercepts), then `keyboard.type` |
| Hover to reveal | `page.mouse.move(x, y)` then a short wait |
| Screenshot | `page.screenshot({ path })` into `evidence/` |
| Video | `browser.newContext({ recordVideo: { dir, size } })`; the file is finalised on `context.close()` |
| Session injection | `page.evaluate(() => localStorage.setItem('<key>', '<token>'))` then navigate |

## Gotchas

- After editing any field that has its own Save button, click Save before navigating; audit every edited
  field for unsaved state before finishing.
- Header values must be ASCII; a full-width comma pasted into a token breaks the request with a
  "Failed to read the 'headers' property" style error.
- A screenshot answers "what is in this image", not "what the page contains": keep a known-visible
  control in frame ([verification-antipatterns.md](../principles/verification-antipatterns.md) §8).
- Measure the behaviour in the browser before and after a fix; a new bundle name is not evidence
  ([verification-before-done.md](../principles/verification-before-done.md)).
- Revert every local-testing hack (CORS annotations, URLs pointed at localhost, shortened intervals)
  before committing.

## Test data

- Disposable inboxes for sign-up/deletion flows; check whether sample data already exists before
  creating it; clone existing records for load tests instead of creating from scratch.
