#!/bin/bash
# Everything the listener received for an app since the last call — direct messages, mentions and
# THREAD REPLIES — one compact line each, with the thread to answer in. Run it on every wake,
# alongside (not instead of) read-since: it is the exact record of what woke you, including
# mentions posted as replies under older threads, which a top-level conversation read can miss.
# Own offset (<runtime>/.inbox-offset), independent of wait-event.sh's. First run starts at the end.
# usage: inbox.sh <co>/<id>
set -u
. "$(cd "$(dirname "$0")" && pwd)/lib.sh"
resolve_app "${1:?usage: inbox.sh <co>/<id>}"
LOG="$APP_RUN/listener.log"; STATE="$APP_RUN/.inbox-offset"
[ -f "$LOG" ] || { echo "[inbox] no log at $LOG"; exit 2; }
size=$(file_size "$LOG")
off=$size
if [ -f "$STATE" ]; then off=$(cat "$STATE"); [[ "$off" =~ ^[0-9]+$ ]] && [ "$off" -le "$size" ] || off=$size; fi
[ "$size" -gt "$off" ] || exit 0
tail -c +$((off + 1)) "$LOG" | head -c $((size - off)) | grep -E '^\[(chat|slack)-event\] ' | sed -E 's/^\[(chat|slack)-event\] //' | python3 -c '
import json, sys
for line in sys.stdin:
    try: e = json.loads(line)
    except Exception: continue
    conv = e.get("conv") or e.get("channel")            # legacy [slack-event]: channel = conversation id
    th = e.get("thread") or e.get("thread_ts"); ts = e.get("ts")
    loc = "%s %s" % (e.get("conv_name") or e.get("channel_name") or conv, conv) + (" thread=%s" % th if th and th != ts else "")
    text = (e.get("text") or "").replace("\n", " / ")
    print("[%s] %s ts=%s | %s (%s): %s" % (e.get("type"), loc, ts, e.get("user_name"), e.get("user"), text[:600]))
' && echo "$size" > "$STATE"   # advance only after the events were printed
