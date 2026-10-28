#!/bin/bash
# Restricted session for a persona app (apps/RULES.md §12). The session gets NO Bash and no file
# access outside the app's memory dir: Claude Code --restricted, user/project settings ignored,
# file tools confined to the working dir (= <app home>/memory). Its only way to the chat is the
# app MCP server (bin/app-mcp.mjs: wait_event, read, send); it may also search and fetch the web.
# A Stop hook keeps it present: ending the turn is blocked until <runtime>/session/stop exists.
#
#   persona-session.sh <co>/<id> [claude args…]            interactive, watch it in the terminal
#   persona-session.sh --headless <co>/<id>                 no terminal: run it as a run_in_background
#                                                          task of the session that starts the app;
#                                                          transcript in <runtime>/session/out.jsonl
#   persona-session.sh --digest <co>/<id> [YYYY-MM-DD]     headless: write that day's digest and
#                                                          update profiles (default: yesterday)
# Usually via `app session <id>` / `app digest <id>`. If no write end runs (app run / service), the
# session starts one and stops it when it exits. Model: app.yaml `model:` (default sonnet).
set -u
. "$(cd "$(dirname "$0")" && pwd)/lib.sh"
DIGEST=0; HEADLESS=0
case "${1:-}" in --digest) DIGEST=1; shift;; --headless) HEADLESS=1; shift;; esac
resolve_app "${1:?usage: persona-session.sh [--digest] <co>/<id> [args…]}"; shift
command -v claude >/dev/null || die "claude CLI not on PATH"
ensure_node
persona=$(field "$APP_CONF" persona); [ -n "$persona" ] || die "$APP_ID has no persona: in app.yaml (persona apps only)"
case "$persona" in /*) ;; *) persona="$APP_HOME/$persona";; esac
[ -f "$persona" ] || die "persona file missing: $persona"
[ -f "$APP_RUN/.env" ] || die "run app up $APP_ID first"
model=$(field "$APP_CONF" model); model=${model:-sonnet}
MEM="$APP_HOME/memory"; mkdir -p "$MEM"/{raw,days,members}; chmod 700 "$MEM"
S="$APP_RUN/session"; mkdir -p "$S"; chmod 700 "$S"; rm -f "$S/stop"

python3 - "$S" "$APPS_BIN" "$APP_REF" "$APP_RUN" "$APP_CHANNEL" "$DIGEST" <<'EOF'
import json, sys
s, bin_, ref, run, ch, digest = sys.argv[1:7]
json.dump({"mcpServers": {"app": {"command": "node", "args": [f"{bin_}/app-mcp.mjs"],
           "env": {"APP_REF": ref, "APP_RUN": run, "APP_CHANNEL": ch}}}}, open(f"{s}/mcp.json", "w"), indent=1)
allow = ["Read", "Grep", "Glob", "Write", "Edit"] + ([] if digest == "1" else ["WebSearch", "WebFetch", "mcp__app"])
settings = {"permissions": {"allow": allow, "defaultMode": "dontAsk"}}
if digest != "1":
    settings["hooks"] = {"Stop": [{"hooks": [{"type": "command", "command": f"bash '{bin_}/persona-stop-hook.sh' '{run}'", "timeout": 10}]}]}
json.dump(settings, open(f"{s}/settings.json", "w"), indent=1)
EOF

{ cat "$APPS_ROOT/persona-conduct.md"; printf '\n\n# Your persona (from the owner)\n\n'; cat "$persona"
  printf '\n\n# This app\n\n- App: %s · channel %s · listened conversations: %s\n- Owner (the person who runs you): %s\n- Memory dir (your working dir): %s\n' \
    "$APP_REF" "$APP_CHANNEL" "$(field "$APP_CONF" listen_convs)" "$(cat "$APP_RUN/owner" 2>/dev/null)" "$MEM"
} > "$S/prompt.md"

cd "$MEM"
COMMON=(--restricted --strict-mcp-config --settings "$S/settings.json" --permission-mode dontAsk --model "$model"
        --append-system-prompt-file "$S/prompt.md")
if [ "$DIGEST" = 1 ]; then
  d=${1:-$(date -v-1d +%F 2>/dev/null || date -d yesterday +%F)}
  [ -f "raw/$d.jsonl" ] || { echo "no transcript for $d — nothing to digest"; exit 0; }
  # --tools and --mcp-config take several values: "--" ends them, or they swallow the prompt
  exec claude -p "${COMMON[@]}" --tools "Read,Grep,Glob,Write,Edit" -- "$(sed "s/{{DATE}}/$d/g" "$APPS_ROOT/persona-digest.md")" < /dev/null
fi
pgrep -f "claude .*--settings $S/settings.json" >/dev/null && die "a session for $APP_ID is already running (app down $APP_REF stops it)"
# The write end: if none runs, this session owns one for its lifetime (one terminal = the whole app).
GUARD=""
if [ "$(listener_count "$APP_RUN/listener.log")" -eq 0 ]; then
  "$APPS_BIN/guardian.sh" "$APP_RUN" >> "$APP_RUN/guardian.out" 2>&1 & GUARD=$!
  trap '[ -n "$GUARD" ] && kill "$GUARD" 2>/dev/null' EXIT
  for _ in 1 2 3 4 5 6 7 8 9 10; do sleep 1; [ "$(listener_count "$APP_RUN/listener.log")" -gt 0 ] && break; done
  [ "$(listener_count "$APP_RUN/listener.log")" -gt 0 ] || die "write end did not start: see $APP_RUN/listener.log"
fi
export MCP_TOOL_TIMEOUT=900000   # wait_event blocks up to 14 min
[ "$HEADLESS" = 1 ] && { set -- -p --output-format stream-json --verbose "$@"; exec >> "$S/out.jsonl" 2>> "$S/err.log"; }
claude "${COMMON[@]}" --tools "Read,Grep,Glob,Write,Edit,WebSearch,WebFetch" --mcp-config "$S/mcp.json" "$@" -- \
  "Start now: read group.md and the last 14 files in days/ if they exist, then call wait_event and keep handling events."
