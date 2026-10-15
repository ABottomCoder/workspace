#!/bin/bash
# Read end: block until the next matching line lands in an app's listener log, print it, exit.
# Run it as a `run_in_background: true` Bash task and re-run it after each wake-up. A background
# task that exits only on a real event is silent while nothing happens (a Monitor would need
# re-arming and posts into the session on each re-arm).
#
# No gap between wake-ups: the byte offset just past the last delivered line is saved in
# <runtime>/.wait-offset and the next run resumes from there, so events that land while the
# session is handling the previous one are delivered on the next run.
#
# Recycle catch-up: the guardian recycles the listener every ~12 min and most chat platforms do
# not replay what arrived while disconnected. So on every `[start]` line this script runs the
# channel's `read-since --peek` over the app's direct conversations and wakes the session only if
# someone else wrote in the gap. Conversations = CATCHUP env (space-separated ids), else
# app.yaml `catchup:`, else `read-since --list-direct`. CATCHUP="" turns it off.
#
# Exit codes — READ THIS, the usual "non-event exit -> silently re-run" is WRONG for 3:
#   0  a matching event (or a catch-up batch) was printed. Handle it, then re-run.
#   1  the tail ended unexpectedly. Re-run silently.
#   2  no log file for this app. Re-run silently (or check the write end).
#   3  THE LISTENER'S HEARTBEAT IS STALE — the app was NOT receiving for the printed number of
#      seconds. Messages from that window are not in the log at all. Re-run AND run read-since
#      over the conversations you care about, and tell the owner in one line. (Seen in practice:
#      host-level DNS outages of 10-15 min left every app deaf with zero events in the log — a
#      read end that only watches for events sees that as an ordinary quiet night.)
#      Tuning: POLL_SECS (read timeout, 90), DEAF_SECS (staleness threshold, 200),
#      DEAF_BACKOFF (min seconds between two 3s, 60 — stops a dead listener from becoming a hot
#      respawn loop across every app on the machine).
#
# usage: wait-event.sh <co>/<id> [egrep-pattern]   (default pattern: [chat-event], legacy [slack-event])
set -u
. "$(cd "$(dirname "$0")" && pwd)/lib.sh"
resolve_app "${1:?usage: wait-event.sh <co>/<id> [pattern]}"
BOT="$APP_NAME"
PAT="${2:-^\[(chat|slack)-event\] }"
DIR="$APP_RUN"
LOG="$DIR/listener.log"
STATE="$DIR/.wait-offset"
READ_SINCE=$(channel_cmd "$APP_CHANNEL" read-since)
REACT=$(channel_cmd "$APP_CHANNEL" react)   # optional verb
ensure_node
if [ -z "${CATCHUP+x}" ]; then
  CATCHUP=$(field "$APP_CONF" catchup | tr ',' ' ')
  [ -n "$CATCHUP" ] || CATCHUP=$( [ -n "$READ_SINCE" ] && cd "$DIR" && $READ_SINCE --list-direct 2>/dev/null | paste -sd' ' -)
fi
STALE_SECS="${STALE_SECS:-3600}"   # older offset = previous session; don't replay it
# --- listener liveness -------------------------------------------------------------
# The listener writes one `[heartbeat] <ISO>` per minute (channel contract), so heartbeats
# flow through the loop below; a dead listener means NO lines at all and `read` blocks for
# ever. That silence is indistinguishable from "nobody is talking".
# So: put a timeout on the read, and when it fires, judge liveness by HEARTBEAT AGE.
POLL_SECS="${POLL_SECS:-90}"        # heartbeat cadence is 60s; 90s of silence is already odd
DEAF_SECS="${DEAF_SECS:-200}"       # newest heartbeat older than this = not receiving
DEAF_BACKOFF="${DEAF_BACKOFF:-60}"  # min seconds between two deaf reports for this app
DEAF_STATE="$DIR/.wait-deaf"        # when we last reported deafness
export LC_ALL=C                    # ${#line} must count bytes, not characters

[ -f "$LOG" ] || { echo "[wait-event] no log at $LOG"; exit 2; }

size=$(file_size "$LOG")
off=$size
if [ -f "$STATE" ] && [ $(( $(date +%s) - $(file_mtime "$STATE") )) -lt "$STALE_SECS" ]; then
  off=$(cat "$STATE")
  [[ "$off" =~ ^[0-9]+$ ]] && [ "$off" -le "$size" ] || off=$size   # garbage or rotated log
fi

# tail through a FIFO so we hold its real PID (bash 3.2 has no reliable $! for <(...))
# and can kill it on exit instead of leaving an orphaned `tail -F` behind.
FIFO=$(mktemp -u "${TMPDIR:-/tmp}/wait-event.XXXXXX"); mkfifo "$FIFO"
tail -c +$((off + 1)) -F "$LOG" 2>/dev/null > "$FIFO" &
TAILPID=$!; disown $TAILPID 2>/dev/null   # no "Terminated: 15" noise on exit
trap 'kill $TAILPID 2>/dev/null; rm -f "$FIFO"' EXIT
exec 3< "$FIFO"
while :; do
  # Two traps here, both found by the tests rather than by reading:
  #  1. `if ! read ...` puts the NEGATED status in $?, so a captured rc was always 0.
  #  2. this is bash 3.2 (macOS), where `read -t` returns 1 for BOTH timeout and EOF —
  #     the ">128 means timeout" convention only exists from bash 4. So the exit status
  #     cannot tell the two apart; ask the thing itself instead: is `tail` still alive?
  IFS= read -t "$POLL_SECS" -r line <&3
  rc=$?
  if [ "$rc" -ne 0 ]; then
    kill -0 "$TAILPID" 2>/dev/null || break    # tail is gone = real EOF -> exit below
    # --- timed out: no line for POLL_SECS. Is the listener alive? ---
    age=$(hb_age "$LOG")
    [ -n "$age" ] || continue                       # cannot tell -> stay quiet, keep waiting
    [ "$age" -le "$DEAF_SECS" ] && continue         # still beating -> just a quiet stretch
    # Throttle: the caller re-runs us on every non-event exit, so reporting instantly on
    # each run would turn one dead listener into a hot respawn loop across every app —
    # worse than the outage. Wait out the backoff first, then re-check: if it recovered
    # during the wait we say nothing at all.
    last=0; [ -f "$DEAF_STATE" ] && last=$(cat "$DEAF_STATE" 2>/dev/null)
    [[ "$last" =~ ^[0-9]+$ ]] || last=0
    waited=$(( $(date -u +%s) - last ))
    if [ "$waited" -lt "$DEAF_BACKOFF" ]; then
      sleep $(( DEAF_BACKOFF - waited ))
      age=$(hb_age "$LOG")
      { [ -n "$age" ] && [ "$age" -gt "$DEAF_SECS" ]; } || continue   # recovered: no alarm
    fi
    date -u +%s > "$DEAF_STATE"
    echo "[wait-event] listener heartbeat is ${age}s old (>${DEAF_SECS}s) — $BOT is probably NOT receiving events"
    exit 3
  fi
  # --- a line arrived ---
  off=$((off + ${#line} + 1))
  # Deliver FIRST, mark handled AFTER: if we die in between, the line is replayed
  # (visible) instead of silently skipped. Same rule for the catch-up below.
  if printf '%s\n' "$line" | grep -Eq -- "$PAT"; then
    printf '%s\n' "$line"
    echo "$off" > "$STATE"
    # Tell the sender the session has it (reaction), without delaying the wake-up: detached, best effort.
    [ -n "$REACT" ] && ( cd "$DIR" && printf '%s' "$line" | $REACT >>"$DIR/react.log" 2>&1 & )
    exit 0
  fi
  if [ -n "$CATCHUP" ] && [ -n "$READ_SINCE" ] && [[ "$line" == "[start]"* ]]; then
    sleep 8                          # let the new socket come up first
    found=""
    for ch in $CATCHUP; do
      # drop the app's own replies ("bot" = posted with the app's credentials) so they never wake anyone
      # --peek: never advance the cursor here. The woken session's own read-since advances it after
      # it has actually seen the messages; advancing here once lost a message when this process was
      # killed (OOM) between read-since and printf. Worst case now = a replay, which the age stamp shows.
      out=$(cd "$DIR" && $READ_SINCE "$ch" --peek 2>/dev/null | grep -E '^\[[0-9.]+\]' | grep -viE "^\[[0-9.]+\]( +↳)? (bot|$BOT): ")
      [ -z "$out" ] && continue
      # Catch-up rows can be weeks old (a cursor that never advanced) yet look exactly like a
      # fresh question, so stamp each row with its UTC time and flag old batches loudly.
      out=$(printf '%s\n' "$out" | python3 -c '
import sys, time, re
now = time.time(); oldest = now
rows = []
for l in sys.stdin:
    m = re.match(r"\[(\d+)\.\d+\]", l)
    ts = int(m.group(1)) if m else now
    oldest = min(oldest, ts)
    rows.append(time.strftime("%Y-%m-%d %H:%MZ ", time.gmtime(ts)) + l.rstrip("\n"))
age = (now - oldest) / 3600
tag = f"{age/24:.0f}d" if age >= 24 else f"{age:.0f}h" if age >= 1 else f"{age*60:.0f}m"
print(f"· oldest {tag} old]" + ("  ⚠️ OLD unread backlog, NOT just arrived — check whether it was already handled" if age >= 24 else ""))
print("\n".join(rows))')
      found+="[catchup $ch after listener recycle $out"$'\n'
    done
    [ -n "$found" ] && { printf '%s' "$found"; echo "$off" > "$STATE"; exit 0; }
  fi
  echo "$off" > "$STATE"           # nothing to deliver on this line: safe to move past it
  rm -f "$DEAF_STATE"                # a line arrived: this app is demonstrably receiving
done
echo "[wait-event] tail of $LOG ended unexpectedly"
exit 1
