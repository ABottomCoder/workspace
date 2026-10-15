#!/bin/bash
# Stop-hook guard: a bot session may not end its turn while its Slack listener is down.
#
# Why: the read end (wait-event.sh) is one-shot by design — it exits after each event and
# must be re-armed with a new `run_in_background` task. Remembering to re-arm is a habit,
# and the habit failed repeatedly (example 2026-09-30 ~3h deaf, again 2026-10-01 mid go-live:
# Hong's DM went unanswered). This hook makes forgetting impossible instead of unlikely.
#
# How:
#   - Which bot is this session? ~/app_bot/slack/<bot>/.runtime/.session-id holds the Claude session id
#     of the session currently playing that bot (written at bootstrap). No match → not a
#     bot session → allow.
#   - Is ITS listener running? A `wait-event.sh <bot>` process whose ancestor chain contains
#     this session's own `claude` process. Orphaned listeners from other/dead sessions don't
#     count — they would make a plain pgrep pass falsely.
#   - Missing → exit 2 with the re-arm instruction (Claude Code feeds stderr back and keeps
#     the turn going). If the hook already blocked once this turn (stop_hook_active), allow
#     the stop so a broken environment can never trap the session in a loop.
#
# Wiring (workspace .claude/settings.local.json):
#   "Stop": [{"hooks":[{"type":"command","command":"bash <botdock>/bin/listener-guard.sh","timeout":10}]}]
set -u
APPS="${BOTDOCK_HOME:-$HOME/app_bot}/slack"
HERE="$(cd "$(dirname "$0")" && pwd)"
input=$(cat)
sid=$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("session_id",""))' 2>/dev/null)
active=$(printf '%s' "$input" | python3 -c 'import json,sys; print(str(json.load(sys.stdin).get("stop_hook_active",False)).lower())' 2>/dev/null)
[ -n "$sid" ] || exit 0

bot=""
for f in "$APPS"/*/.runtime/.session-id; do
  [ -f "$f" ] || continue
  if [ "$(tr -d '[:space:]' < "$f")" = "$sid" ]; then bot=$(basename "$(dirname "$(dirname "$f")")"); break; fi
done
[ -n "$bot" ] || exit 0

# This session's claude process = nearest ancestor whose command name is "claude".
claude_pid=""; p=$PPID
for _ in 1 2 3 4 5 6 7 8; do
  [ -n "$p" ] && [ "$p" -gt 1 ] 2>/dev/null || break
  if [ "$(ps -o comm= -p "$p" 2>/dev/null | xargs basename 2>/dev/null)" = "claude" ]; then claude_pid=$p; break; fi
  p=$(ps -o ppid= -p "$p" 2>/dev/null | tr -d ' ')
done
[ -n "$claude_pid" ] || exit 0   # can't tell which session we are in: don't block on a guess

has_ancestor() {   # has_ancestor <pid> <ancestor>
  local q=$1
  for _ in 1 2 3 4 5 6 7 8; do
    q=$(ps -o ppid= -p "$q" 2>/dev/null | tr -d ' ')
    [ -n "$q" ] && [ "$q" -gt 1 ] 2>/dev/null || return 1
    [ "$q" = "$2" ] && return 0
  done
  return 1
}
for pid in $(pgrep -f "wait-event.sh $bot( |$)" 2>/dev/null); do
  has_ancestor "$pid" "$claude_pid" && exit 0
done

[ "$active" = "true" ] && exit 0
echo "SLACK LISTENER DOWN: this session is the '$bot' bot and its read end (wait-event.sh) is not running, so Slack messages are not reaching you. Before ending the turn: (1) re-arm it — Bash run_in_background: $HERE/wait-event.sh $bot ; (2) run read-since over your conversations and answer anything new." >&2
exit 2
