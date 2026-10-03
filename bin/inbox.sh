#!/bin/bash
# Everything the listener received for <bot> since the last call — DMs, @mentions, and THREAD
# REPLIES — one compact line each. Run it on every wake, alongside (not instead of) read-since.
#
# Why (read-since has since been fixed to include replies under older parents, 2026-10-01 — this
# remains the record of exactly what woke you): read-since used to list top-level messages only. An @mention posted as a thread
# reply reaches the listener log (and wakes the session) but never shows up in read-since, so it
# looked like "no new messages". example's two thread mentions in #example-team on 2026-10-01 went
# unanswered for hours this way.
#
# Own offset (<botdir>/.inbox-offset), independent of wait-event.sh's. First run starts at the end.
# usage: inbox.sh <bot>
set -u
BOT="${1:?usage: inbox.sh <bot>}"
DIR="${BOTDOCK_HOME:-$HOME/app_bot}/slack/$BOT/.runtime"
LOG="$DIR/$BOT-listener.log"; STATE="$DIR/.inbox-offset"
[ -f "$LOG" ] || { echo "[inbox] no log at $LOG"; exit 2; }
size=$(stat -f %z "$LOG")
off=$size
if [ -f "$STATE" ]; then off=$(cat "$STATE"); [[ "$off" =~ ^[0-9]+$ ]] && [ "$off" -le "$size" ] || off=$size; fi
[ "$size" -gt "$off" ] || exit 0
tail -c +$((off + 1)) "$LOG" | head -c $((size - off)) | grep '^\[slack-event\] ' | sed 's/^\[slack-event\] //' | python3 -c '
import json, sys
for line in sys.stdin:
    try: e = json.loads(line)
    except Exception: continue
    ch, th, ts = e.get("channel"), e.get("thread_ts"), e.get("ts")
    loc = "%s %s" % (e.get("channel_name") or ch, ch) + (" thread=%s" % th if th and th != ts else "")
    text = (e.get("text") or "").replace("\n", " / ")
    print("[%s] %s ts=%s | %s: %s" % (e.get("type"), loc, ts, e.get("user_name"), text[:600]))
' && echo "$size" > "$STATE"   # advance only after the events were printed
