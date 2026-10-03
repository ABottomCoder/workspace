#!/bin/bash
# Write end: keeps one Slack Socket Mode listener alive for <bot>, appending every line
# to ~/.botdock/<bot>/<bot>-listener.log (which wait-event.sh reads).
#   - respawns the listener if it crashes
#   - recycles it every ROTATE_SECS (~12 min) so a silently stale socket can't leave the
#     bot "connected but receiving nothing"
#   - takes its listener child down with it on any exit (no orphan holding the token)
# Start it through `botdock run <bot>` as a run_in_background task of the session, so the
# session sees it and is notified if it dies.
# usage: guardian.sh <bot>
set -u
BOT="${1:?usage: guardian.sh <bot>}"
BIN="$(cd "$(dirname "$0")" && pwd)"
RUN="${BOTDOCK_RUNTIME:-$HOME/.botdock}/$BOT"
LOG="$RUN/$BOT-listener.log"
ROTATE_SECS="${LISTENER_ROTATE_SECS:-720}"
[ -f "$RUN/.env" ] || { echo "[guardian] $RUN/.env missing — run: botdock up $BOT"; exit 2; }
cd "$RUN"   # listener.js loads ./.env

# node may be missing from PATH in minimal environments (cron, launchd)
if ! command -v node >/dev/null 2>&1; then
  for d in "$HOME"/.nvm/versions/node/*/bin /opt/homebrew/bin /usr/local/bin; do
    [ -x "$d/node" ] && { PATH="$d:$PATH"; break; }
  done
fi

child=""
cleanup() { [ -n "$child" ] && kill "$child" 2>/dev/null; exit 0; }
trap cleanup TERM INT HUP EXIT

# Two listeners on one app token split the event stream between them — refuse.
if lsof "$LOG" 2>/dev/null | grep -q node; then
  echo "[guardian] a listener for $BOT is already writing $LOG — not starting a second"
  exit 0
fi

echo "[start] guardian up $(date -u +%FT%TZ) (bot=$BOT rotate=${ROTATE_SECS}s)" >> "$LOG"
while true; do
  node "$BIN/listener.js" >> "$LOG" 2>&1 &
  child=$!
  for _ in $(seq 1 "$ROTATE_SECS"); do
    kill -0 "$child" 2>/dev/null || break
    sleep 1
  done
  kill "$child" 2>/dev/null
  wait "$child" 2>/dev/null
  echo "[start] recycle $(date -u +%FT%TZ)" >> "$LOG"
  sleep 1
done
