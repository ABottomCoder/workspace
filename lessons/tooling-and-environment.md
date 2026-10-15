# Tooling and environment

Traps in shells, process management, schedulers, deploy tooling, agent harnesses, browsers and connectors that make a command look successful when it was not.

### Send message text from a file, never as a quoted shell argument, and read it back
**Mistake:** Messages passed to a CLI as double-quoted arguments lost inline code spans to backtick and `$()` command substitution (once deleting the key name from a safety warning); a single-quoted long message was cut off at the first apostrophe and the rest ran as shell commands. Every time, the tool reported "sent".
**Root cause:** Double quotes still expand backticks and `$`, single quotes break on ordinary apostrophes, and a remembered rule gave no trigger at send time, so deciding per message whether to "bother" failed repeatedly.
**Rule:** Unconditionally, even for one-liners: write the text with a quoted heredoc (`cat > f <<'EOF'`) and pass it via `--file`, stdin, `"$(cat f)"`, or an `execFile`-style call that skips shell parsing. After sending, read the delivered message back and check length, tail and code spans for missing text. "Sent" and "intact" are different facts.
**Seen:** 8

### Stop processes by known PID or process group, never by a generic command-line pattern
**Mistake:** `pkill -f` / `pgrep -f` loops killed the agent's own remote shell, supervisor wrapper shells, and the identically named services of other projects that shared an `apps/<x>/src/main.ts` layout; a duplicate-run guard kept reporting "already running" because the operator's monitoring command contained the pattern. Separately, killing only a launcher shell left its child alive, holding an exclusive device, so the user's first real run failed.
**Root cause:** `-f` substring-matches every process's full argv (the bracket trick protects only the pattern itself), and "the launcher exited" was taken to mean "the tree is gone".
**Rule:**
- Scripts that stop processes use a pidfile, or filter by cwd (`lsof -a -p PID -d cwd` equals `pwd -P`) or exact executable (`pgrep -x`, `ps -o comm=`, anchored `^node .*index.ts`). Never pattern-kill a generic path on a shared machine.
- Start test processes so you know their PID; kill the process group (`kill -- -PGID`) or the child, not just the wrapper.
- Keep a guard's pattern out of your own compound commands (separate call or `[t]sx`).
- Afterwards verify with `ps`/`pgrep -x` that your tree is gone and every other service is still up; check for leftovers before telling the user a tool works. Warn owners of template clones about inherited ops scripts.
**Seen:** 6

### Assume the working directory has drifted; use absolute paths and isolated calls
**Mistake:** A messaging script failed ("Cannot find module", auth error) after earlier `cd`s for grepping, and when chained after `cd other-repo` its dotenv loaded the wrong `.env`. A `cd service-a && rsync dist/ ... && rsync dist/ ...` chain shipped one service's build into another's target, three times.
**Root cause:** The agent's shell keeps cwd between calls and within a chain; tools also read `.env`, config and lockfiles implicitly from cwd, not from the script's directory.
**Rule:** Invoke scripts and deploy sources by absolute path, or `cd <script dir> && node script.js` in a dedicated call. Never chain two deploys, or repo work plus a send, after a `cd`. Before chaining, ask what each command reads implicitly from cwd. Treat any output other than an explicit success marker as failure; smoke-test each deployed service, and treat identical transfer sizes for different artifacts as a red flag.
**Seen:** 5

### Emit tool calls with exact syntax; a malformed call silently does nothing
**Mistake:** In long sessions, tool calls were emitted with a missing namespace prefix or a bare word in place of the opening wrapper tag; the harness rendered them as text, so messages never sent and commands never ran, including during an incident.
**Root cause:** Syntax drift under long-session load; not tied to payload size or tool type (it also happened on no-argument calls).
**Rule:** Before every call, check the opening wrapper, each parameter tag and the closing tag carry the required prefix. Never put a literal closing-parameter tag string inside a value. Confirm side effects (message landed, output returned) instead of assuming. When the user reports a malformed call, re-issue it correctly with at most one sentence.
**Seen:** 3

### Get the debug browser running yourself, in the mode the DevTools tool expects
**Mistake:** Spent a long time hand-launching a browser whose debugging port never bound; asked the user to open the browser manually; and launched it with a custom profile dir that an attach-mode MCP could not find (`DevToolsActivePort`).
**Root cause:** Auto-connect mode only attaches to an already-running debuggable browser and reads a specific profile path, while recent Chrome may refuse a debugging port on the default profile and says so only on stderr.
**Rule:** Prefer letting the MCP server launch and manage its own browser. If you must attach, do it yourself, never as a user chore: quit all running instances, relaunch with `--remote-debugging-port=9222` using the profile the MCP expects, capture stderr, and verify with `curl localhost:9222/json/version`. If the MCP tools disappear, the browser died; relaunch it.
**Seen:** 3

### Background schedulers run without your PATH or your folder permissions
**Mistake:** A cron "safety net" ran bare `node` and failed every run with output sent to `/dev/null`, piling up orphans during an outage; cron and then launchd jobs failed "Operation not permitted" because the scripts lived under `~/Documents`.
**Root cause:** cron/launchd use a minimal environment without rc-file PATH additions, and on macOS `~/Documents`, `~/Desktop` and `~/Downloads` are privacy-protected folders whose GUI grants background jobs do not inherit.
**Rule:** Resolve interpreters inside the script (`command -v node ||` set PATH) or set `PATH=` in the crontab. Keep anything run outside the interactive session outside protected folders, or grant the interpreter Full Disk Access. Test in a scheduler-like env first (`env -i PATH=/usr/bin:/bin HOME=$HOME ...` or a trivial agent in the target dir), log the output, and check symlinks survive relocation.
**Seen:** 2

### zsh does not word-split unquoted variables
**Mistake:** Monitors built as `R="ssh ..."; $R cmd` or `for s in $LIST` ran the whole string as one command or one loop item; one died silently, another raised a plausible false alarm about production.
**Root cause:** Relied on bash-style word splitting and did not sweep for the same construct after it bit once.
**Rule:** Wrap remote commands in a function (`r() { ssh host "$@"; }`); list loop items literally or iterate with `while read`. Monitors print an "armed" line on start, and alerts name the failing item and its value, not a bare count. When a shell trap bites, grep your other scripts for it. If your check disagrees with a passing manual check, the gap is the bug.
**Seen:** 2

### Quote capacity and cost figures only from measured deltas
**Mistake:** A cleanup was promised to free about twice the space it actually freed, based on a `docker system df` RECLAIMABLE field, and the "correction" re-read the same field.
**Root cause:** For images RECLAIMABLE counts anything not used by a running container, but `image prune -a` keeps images referenced by stopped containers; a summary field was read as a prediction of a command's effect.
**Rule:** Measure the delta (`df -h` before/after) or sum the exact objects to be removed, and trust a metric only for the types you verified. When corrected, drop the claim until re-measured instead of substituting another number. Likewise know whether a cost figure is raw provider cost or marked-up price before it reaches a pricing decision.
**Seen:** 2

### A recreated service must get its full environment; verify a visible configured value
**Mistake:** A container recreated with only the base compose file, and a preview started from a shell that had sourced the dev `.env`, both came up healthy but generated links pointing at localhost.
**Root cause:** Recreating with one `-f` file drops everything the override supplied, and child processes inherit sourced variables, which Node prefers over `--env-file`.
**Rule:** Wrap multi-file compose invocations (`-f a.yml -f b.yml`) in a script. Never start a service from a shell that sourced a dev env file; start scripts unset their env-file variables before launching. After deploy check one externally visible configured value (generated URL host, `docker exec ... printenv`), not just a 200. Restart an nginx that cached an upstream container's old IP.
**Seen:** 2

### Shared or "portable" tooling holds only what is true for every user and machine
**Mistake:** Per-instance task config (listen settings, owner, prompts) was committed into a shared tooling repo, and a plugin meant to be shareable was written with one machine's paths; a suggested restart command would have discarded the running session.
**Root cause:** Treated one instance as a fixed identity, never tested from a second location, and did not check a command's side effects before suggesting it.
**Rule:** Commit to shared tooling only what holds for every user and task; per-user settings, contacts and history stay local. Ask "would a colleague using this for a different task want this?" Verify anything labelled portable from a second path or machine. Before suggesting a command, state side effects, especially ones that end the session or discard state.
**Seen:** 2

### Copy existing alert commands; do not rewrite filters from memory
**Mistake:** A re-armed log monitor used filter terms retyped from memory and missed the most common failure line, so a restart went unnoticed.
**Root cause:** The documented filter was ignored; the improvised one covered imagined failures, not the strings the system prints.
**Rule:** Re-arm monitors by copying the original command. If you change a filter, grep historical logs to confirm it matches real past failure lines. An alert that misses the most common failure is worse than none.
**Seen:** 1

### Never pipe a long-running script into an early-closing consumer
**Mistake:** A 20-iteration watcher started with `| head -3` died of SIGPIPE after two rounds and exited 0.
**Root cause:** head and `grep -m` close the pipe and kill the writer silently; `$?` reflects the last command in the pipe.
**Rule:** Never attach early-closing commands to long-running scripts; redirect to a file and read it to check progress.
**Seen:** 1

### macOS rsync silently ignores GNU-only flags
**Mistake:** A production rsync from a Mac with `--chown` transferred nothing and exited 0.
**Root cause:** macOS ships openrsync (protocol 29), not GNU rsync 3.x; `--chown` is a GNU 3.1+ flag.
**Rule:** Do not use GNU-3.x-only flags from macOS; fix ownership with `chown -R` on the host. Run a checksum dry run (`rsync -azn -c --itemize-changes`) before deploying, and grep a new string in the deployed file before restarting. Exit 0 is not proof of transfer.
**Seen:** 1

### Check the available tools before saying "I can't"
**Mistake:** Told the user a newly spawned agent session could not communicate with the current one.
**Root cause:** Answered from assumption; the tool list included cross-session messaging.
**Rule:** Before saying "I can't do X", check the available tools, including deferred ones.
**Seen:** 1

### Read the directory's own instructions before improvising infra
**Mistake:** Hand-rolled a supervisor loop and a basic history reader when local docs specified a canonical supervisor (with socket rotation) and a cursor-aware reader that includes thread replies; a threaded mention was missed.
**Root cause:** Copied neighbours instead of reading the operating rules; the canonical script was missing, so it looked optional.
**Rule:** Read the directory's instructions file before building helper infra; if a canonical script is missing, recreate it to spec rather than improvising.
**Seen:** 1

### Give long external commands an explicit timeout and judge them by stdout and exit code
**Mistake:** A multi-minute static scan under a sub-agent was killed at the default shell timeout, and harmless stderr was read as failure.
**Root cause:** Default timeout too short; success judged by empty stderr.
**Rule:** Set a generous explicit timeout for long commands; judge success by stdout content and exit code, never by empty stderr; reproduce a failing command manually before diagnosing, since the agent's own narration of the error can be wrong.
**Seen:** 1

### Orchestration scripts run in a sandbox without runtime globals
**Mistake:** An agent-runtime orchestration script used `process.cwd()` and crashed with `process is not defined`.
**Root cause:** The sandbox has standard JS built-ins only; no `process`, `require` or fs, and `Date.now()` / `Math.random()` are banned.
**Rule:** Pass paths, timestamps and env values via args or inline constants. Check the runtime's sandbox rules before writing such a script.
**Seen:** 1

### Long-lived CLI auth: use the final token in the service environment
**Mistake:** All server workers crashed when a shared interactive CLI OAuth credential expired; logging in elsewhere had revoked its refresh token, and the intermediate auth code was pasted instead of the final token.
**Root cause:** Interactive credential files rotate and get kicked out; the setup flow shows two similar-looking strings.
**Rule:** When many sessions crash at once, reproduce one worker spawn by hand to separate auth failure from app failure. Put a long-lived token (e.g. from `claude setup-token`, the final value with the documented prefix) in the service env file, restart, and confirm it is in the process environment. Never paste tokens into chat.
**Seen:** 1

### Hanging package installs: check DNS and egress first, and lock per directory
**Mistake:** Nearly blamed deploy code when every `npm install` hung with an empty `node_modules`.
**Root cause:** A VPN client on the server used a dead exit node and took over DNS, silently dropping all outbound traffic (tx > 0, rx 0); separately, concurrent installs in one directory deadlocked.
**Rule:** When installs hang, run `getent hosts <registry>` and `resolvectl status` and inspect VPN exit-node/DNS settings. Keep exit nodes and DNS overrides off servers that do not need them. Serialize deploys per project with a lock (e.g. `flock`).
**Seen:** 1

### Pre-stage management return routes before enabling a VPN exit node
**Mistake:** Enabling a mesh-VPN exit node on a remote host locked out SSH within seconds.
**Root cause:** Replies to inbound sessions were routed through the tunnel and SNATed, breaking connections that arrived on the public interface.
**Rule:** Before enabling an exit node remotely, mark reply traffic for inbound ports (22, 443, ...) with iptables mangle and add an `ip rule` sending marked packets via the main table. Keep a recovery path: clear the exit node from another peer over the VPN address.
**Seen:** 1

### Chain shell commands on one line
**Mistake:** Multi-line commands in one shell tool call triggered a manual approval prompt every time.
**Root cause:** Permission rules match only the first line, so newline-separated commands cannot be auto-approved.
**Rule:** Join commands with `&&` or `;` on one line, or make separate calls.
**Seen:** 1

### Slack Socket Mode listener gotchas
**Mistake:** Event delivery looked random, the listener connected but emitted nothing, and after network blips it stayed alive but deaf.
**Root cause:** Socket Mode spreads events across all open sockets of one app; the inner event is at `body.event`; a dead WebSocket does not reliably reconnect; the bot sees only its own mentions and DMs; reconnects do not replay missed messages.
**Rule:** Run exactly one listener per app under a supervisor that restarts it periodically, with a heartbeat. Never bare-restart (orphans). Read `body.event`. After any outage fetch missed messages from history. Enable both the Messages tab and "allow users to send messages" in App Home.
**Seen:** 1

### `sed -i` on a live log detaches the writer
**Mistake:** Scrubbing a secret from an actively written log with `sed -i` replaced the file; the running process kept writing to the unlinked inode and its health check saw a stale heartbeat.
**Root cause:** Treated an open, appended log as a plain file.
**Rule:** To scrub a live log, rewrite it in place without changing the inode, or restart the writer and verify fresh lines. Ask people to share secrets via a file, not chat, so they never reach logs.
**Seen:** 1

### Cloud-drive connectors can only share what they created
**Mistake:** Sharing a file uploaded through the local drive sync mount failed with "caller does not have permission".
**Root cause:** The connector's access is limited to files it created, and base64 uploads through a tool call are capped at roughly 100KB.
**Rule:** For large files, create a folder with the connector, drop the file in via the local sync mount, and share the folder. Search by parent ID, since title search lags. Never put client files in anyone-with-link folders.
**Seen:** 1

### macOS virtual audio routing: aggregates and hidden attenuators
**Mistake:** An audio test passed falsely: the conferencing app read only the first sub-device of an aggregate device, and the meter moved while no sound came out.
**Root cause:** Conferencing apps do not fully read aggregate devices, and a virtual device's own volume slider or a muted output silently attenuates audio.
**Rule:** Point the app straight at the virtual device and bridge other inputs into it. Force virtual-device volume and unmute in the launcher and restore previous settings on exit. Verify at the receiving app, not an intermediate tool.
**Seen:** 1
