#!/bin/bash
# Write end: keeps one channel listener alive for an app, appending every line to
# <runtime>/listener.log (which wait-event.sh reads).
#   - respawns the listener if it crashes
#   - recycles it every ROTATE_SECS (~12 min) so a silently stale connection can't leave the
#     app "connected but receiving nothing"
#   - takes its listener child down with it on any exit (no orphan holding the credentials)
# Started by `app run <id>` (run_in_background) or by the service manager (service.<platform>.sh).
# usage: guardian.sh <runtime-dir>
set -u
RUN="${1:?usage: guardian.sh <runtime-dir>}"
. "$(cd "$(dirname "$0")" && pwd)/lib.sh"
[ -f "$RUN/.env" ] || { echo "[guardian] $RUN/.env missing — run: app up <id>"; exit 2; }
CH=$(sed -n 's/^APP_CHANNEL=//p' "$RUN/.env")
LISTEN=$(channel_cmd "$CH" listen) || { echo "[guardian] channel '$CH' has no listen"; exit 2; }
LOG="$RUN/listener.log"
ROTATE_SECS="${LISTENER_ROTATE_SECS:-720}"
cd "$RUN"   # channel scripts load ./.env
ensure_node

child=""
cleanup() { [ -n "$child" ] && kill "$child" 2>/dev/null; exit 0; }
trap cleanup TERM INT HUP EXIT

# Two listeners on one app's credentials split the event stream between them — refuse.
if [ "$(listener_count "$LOG")" -gt 0 ]; then
  echo "[guardian] a listener is already writing $LOG — not starting a second"
  exit 0
fi

echo "[start] guardian up $(date -u +%FT%TZ) (channel=$CH rotate=${ROTATE_SECS}s)" >> "$LOG"
while true; do
  $LISTEN >> "$LOG" 2>&1 &
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
