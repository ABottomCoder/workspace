#!/bin/bash
# Fleet read end: block until the next matching line lands in a bot's listener log,
# print it, exit. Run it as a `run_in_background: true` Bash task and re-run it after
# each wake-up.
#
# Why not a Monitor: the Monitor tool now expires after 30 min max (no persistent
# mode), so a Monitor read end has to be re-armed every half hour and every re-arm
# posts into the session. A background task that exits only on a real event is silent
# while nothing happens.
#
# No gap between wake-ups: the byte offset just past the last delivered line is saved
# in <botdir>/.wait-offset and the next run resumes from there, so events that land
# while the session is handling the previous one are delivered on the next run.
#
# Recycle catch-up: the listener drops and reconnects its socket every ~12 min
# (start.sh ROTATE_SECS) and Socket Mode never replays what arrived in that window.
# So on every `[start]` line this script runs read-since --peek over the bot's
# DM conversations and wakes the session only if it found messages from someone else.
# Conversations = CATCHUP env (space-separated ids) or, by default, every D… id in the
# bot's .read-cursors.json. CATCHUP="" turns it off.
#
# Exit codes — READ THIS, the usual "non-event exit → silently re-run" is WRONG for 3:
#   0  a matching event (or a catch-up batch) was printed. Handle it, then re-run.
#   1  the tail ended unexpectedly. Re-run silently.
#   2  no log file for this bot. Re-run silently (or check the write end).
#   3  THE LISTENER'S HEARTBEAT IS STALE — this bot was NOT receiving Slack events for
#      the printed number of seconds. Re-running silently is not enough: messages that
#      arrived in that window are not in the log at all, so the log cannot tell you what
#      you missed. On a 3, re-run AND run `read-since` over the conversations you care
#      about, and say one line about it rather than staying quiet. Verified on
#      2026-09-30: two host-level `ENOTFOUND slack.com` outages, 13 and 14.5 minutes,
#      all six bots deaf simultaneously, zero `[slack-event]` lines in either window —
#      a read end that only watches for events sees those as an ordinary quiet night.
#      Tuning: POLL_SECS (read timeout, 90), DEAF_SECS (staleness threshold, 200),
#      DEAF_BACKOFF (min seconds between two 3s, 60 — this is what stops a permanently
#      dead listener from becoming a hot respawn loop across the whole fleet).
#
# usage: wait-event.sh <bot> [egrep-pattern]     (default pattern: \[slack-event\])
set -u
BOT="${1:?usage: wait-event.sh <bot> [pattern]}"
PAT="${2:-\[slack-event\]}"
DIR="${BOTDOCK_RUNTIME:-$HOME/.botdock}/$BOT"
LOG="$DIR/$BOT-listener.log"
STATE="$DIR/.wait-offset"
WS="$DIR"   # cursors (.read-cursors.json) + .env live in the runtime dir
BIN="$(cd "$(dirname "$0")" && pwd)"
if [ -z "${CATCHUP+x}" ]; then
  CATCHUP=$(python3 -c 'import json,sys; print(" ".join(k for k in json.load(open(sys.argv[1])) if k.startswith("D")))' "$WS/.read-cursors.json" 2>/dev/null)
fi
STALE_SECS="${STALE_SECS:-3600}"   # older offset = previous session; don't replay it
# --- listener liveness -------------------------------------------------------------
# The listener writes one `[heartbeat] <ISO>` per minute, so heartbeats already flow
# through the loop below; a dead listener means NO lines at all and `read` blocks for
# ever. That silence is indistinguishable from "nobody is talking", which is how six
# bots went deaf for 13 min on 2026-09-30 with every read end reporting nothing.
# So: put a timeout on the read, and when it fires, judge liveness by HEARTBEAT AGE.
POLL_SECS="${POLL_SECS:-90}"        # heartbeat cadence is 60s; 90s of silence is already odd
DEAF_SECS="${DEAF_SECS:-200}"       # newest heartbeat older than this = not receiving
DEAF_BACKOFF="${DEAF_BACKOFF:-60}"  # min seconds between two deaf reports for this bot
DEAF_STATE="$DIR/.wait-deaf"        # when we last reported deafness
export LC_ALL=C                    # ${#line} must count bytes, not characters

[ -f "$LOG" ] || { echo "[wait-event] no log at $LOG"; exit 2; }

hb_age() {   # prints the newest heartbeat's age in seconds, or nothing if unreadable
  local hb t
  hb=$(tail -400 "$LOG" 2>/dev/null | grep '^\[heartbeat\] ' | tail -1 \
       | sed -E 's/^\[heartbeat\] //; s/\..*$//')
  [ -n "$hb" ] || return 0
  t=$(date -u -jf "%Y-%m-%dT%H:%M:%S" "$hb" +%s 2>/dev/null) \
     || t=$(date -u -d "$hb" +%s 2>/dev/null)
  [ -n "$t" ] || return 0            # unparsable: say nothing rather than raise a false alarm
  echo $(( $(date -u +%s) - t ))
}
size=$(stat -f %z "$LOG")
off=$size
if [ -f "$STATE" ] && [ $(( $(date +%s) - $(stat -f %m "$STATE") )) -lt "$STALE_SECS" ]; then
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
    age=$(hb_age)
    [ -n "$age" ] || continue                       # cannot tell -> stay quiet, keep waiting
    [ "$age" -le "$DEAF_SECS" ] && continue         # still beating -> just a quiet stretch
    # Throttle: the caller re-runs us on every non-event exit, so reporting instantly on
    # each run would turn one dead listener into a hot respawn loop across six bots —
    # worse than the outage. Wait out the backoff first, then re-check: if it recovered
    # during the wait we say nothing at all.
    last=0; [ -f "$DEAF_STATE" ] && last=$(cat "$DEAF_STATE" 2>/dev/null)
    [[ "$last" =~ ^[0-9]+$ ]] || last=0
    waited=$(( $(date -u +%s) - last ))
    if [ "$waited" -lt "$DEAF_BACKOFF" ]; then
      sleep $(( DEAF_BACKOFF - waited ))
      age=$(hb_age)
      { [ -n "$age" ] && [ "$age" -gt "$DEAF_SECS" ]; } || continue   # recovered: no alarm
    fi
    date -u +%s > "$DEAF_STATE"
    echo "[wait-event] listener heartbeat is ${age}s old (>${DEAF_SECS}s) — $BOT is probably NOT receiving Slack events"
    exit 3
  fi
  # --- a line arrived ---
  off=$((off + ${#line} + 1))
  # Deliver FIRST, mark handled AFTER: if we die in between, the line is replayed
  # (visible) instead of silently skipped. Same rule for the catch-up below.
  if printf '%s\n' "$line" | grep -Eq -- "$PAT"; then
    printf '%s\n' "$line"
    echo "$off" > "$STATE"
    exit 0
  fi
  if [ -n "$CATCHUP" ] && [[ "$line" == "[start]"* ]]; then
    sleep 8                          # let the new socket come up first
    found=""
    for ch in $CATCHUP; do
      # drop the bot's own replies ("bot" = posted via bot token) so they never wake anyone
      # --peek: never advance the cursor here. The woken session's own read-since
      # advances it after it has actually seen the messages; advancing here lost a
      # message when this process was killed between read-since and printf (example,
      # 2026-09-25, OOM). Worst case now = a replay, which the age stamp makes obvious.
      out=$(cd "$WS" && node "$BIN/read-since.mjs" "$ch" --peek 2>/dev/null | grep -E '^\[[0-9.]+\]' | grep -viE "^\[[0-9.]+\]( +↳)? (bot|$BOT): ")
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
  rm -f "$DEAF_STATE"                # a line arrived: this bot is demonstrably receiving
done
echo "[wait-event] tail of $LOG ended unexpectedly"
exit 1
