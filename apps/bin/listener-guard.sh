#!/bin/bash
# Stop hook: an app session may not end its turn while its read end is down.
#
# Why: the read end (wait-event.sh) is one-shot by design — it exits after each event and must be
# re-armed with a new run_in_background task. Remembering is a habit, and the habit fails; when it
# does, the app goes silently deaf for hours. This hook makes forgetting impossible.
#
# How:
#   - Not an app session (no business/*/apps/*/.runtime/.session-id holds this session id)
#     -> exit 0 immediately, no output.
#   - Its read end counts only if a `wait-event.sh <app>` process descends from THIS session's
#     `claude` process (orphans from dead sessions don't count).
#   - Missing -> exit 2 with the re-arm instruction (Claude Code feeds stderr back and keeps the
#     turn going). If the hook already blocked once this turn (stop_hook_active), allow the stop,
#     so a broken environment can never trap the session in a loop.
# Wiring: .claude/settings.json → "Stop": [{"hooks":[{"type":"command",
#   "command":"bash \"$CLAUDE_PROJECT_DIR\"/apps/bin/listener-guard.sh","timeout":10}]}]
set -u
. "$(cd "$(dirname "$0")" && pwd)/lib.sh"
input=$(cat)
sid=$(printf '%s' "$input" | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
[ -n "$sid" ] || exit 0
home=$(app_for_session "$sid") || exit 0
id=$(basename "$home"); co=$(basename "$(dirname "$(dirname "$home")")")
case "$input" in *'"stop_hook_active":true'*|*'"stop_hook_active": true'*) active=true;; *) active=false;; esac

# This session's claude process = nearest ancestor whose command name is "claude".
claude_pid=""; p=$PPID
for _ in 1 2 3 4 5 6 7 8; do
  [ -n "$p" ] && [ "$p" -gt 1 ] 2>/dev/null || break
  if [ "$(basename "$(ps -o comm= -p "$p" 2>/dev/null)" 2>/dev/null)" = "claude" ]; then claude_pid=$p; break; fi
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
for pid in $(pgrep -f "wait-event\.sh ($co/)?$id( |\$)" 2>/dev/null); do
  has_ancestor "$pid" "$claude_pid" && exit 0
done

[ "$active" = true ] && exit 0
echo "APP READ END DOWN: this session runs app '$co/$id' and its read end (wait-event.sh) is not running, so messages are not reaching you. Before ending the turn: (1) re-arm it — Bash run_in_background: $APPS_BIN/wait-event.sh $co/$id ; (2) app read $co/$id <conv> over your conversations and answer anything new." >&2
exit 2
