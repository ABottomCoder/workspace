#!/bin/bash
# SessionStart hook: start the journal catch-up (journal_catchup.py) in the background, at most once a
# day, and return at once. Skips when the catch-up already finished today, when one is running (its
# own lock), and inside the worker itself (JOURNAL_WORKER). Output: none.
# Wiring: .claude/settings.json → "SessionStart": [{"matcher":"startup|resume","hooks":[{"type":"command",
#   "command":"bash \"$CLAUDE_PROJECT_DIR/tools/sessions/journal-hook.sh\"","timeout":10}]}]
cat >/dev/null
[ -n "${JOURNAL_WORKER:-}" ] && exit 0
HERE="$(cd "$(dirname "$0")" && pwd)"; MAIN="$(cd "$HERE/../.." && pwd)"
OUT="${INTERVENTION_OUT:-$MAIN/user/intervention}"
[ "$(cat "$OUT/.catchup_date" 2>/dev/null)" = "$(date +%F)" ] && exit 0
[ -d "$OUT/.catchup.lock" ] && exit 0
mkdir -p "$OUT"
# A fresh session's environment would make the worker a child of this session: drop its markers.
for v in $(env | grep -oE '^(CLAUDECODE|CLAUDE_CODE_[A-Z_]*|CLAUDE_PID|CLAUDE_EFFORT)=' | tr -d =); do unset "$v"; done
PYTHONIOENCODING=utf-8 nohup python3 -u "$HERE/journal_catchup.py" >> "$OUT/catchup.log" 2>&1 < /dev/null &
disown 2>/dev/null
exit 0
