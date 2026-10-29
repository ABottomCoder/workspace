#!/bin/bash
# Stop hook: once this session's transcript passes the limit, tell Claude to hand off to a fresh
# session (RULES.md). Limit: CLAUDE_ROLLOVER_MB (default 50). Opt out: CLAUDE_ROLLOVER_DISABLE=1.
# Only interactive sessions roll over; CLAUDE_ROLLOVER_INTERACTIVE=1 skips the tty check (tests).
. "$(dirname "$0")/lib.sh"
LIMIT_MB=${CLAUDE_ROLLOVER_MB:-50}
[ "${CLAUDE_ROLLOVER_DISABLE:-0}" = 1 ] && exit 0

input=$(cat)
eval "$(printf '%s' "$input" | python3 -c '
import json, shlex, sys
try: d = json.loads(sys.stdin.buffer.read().decode("utf-8"))  # not the locale codec: GBK breaks on Chinese text
except Exception: d = {}
print("sid=%s tp=%s" % (shlex.quote(d.get("session_id", "")), shlex.quote(d.get("transcript_path", ""))))')"
{ [ -n "$sid" ] && [ -f "$tp" ]; } || exit 0

size=$(file_size "$tp") || exit 0
[ "$size" -lt $((LIMIT_MB * 1024 * 1024)) ] && exit 0

if [ "${CLAUDE_ROLLOVER_INTERACTIVE:-0}" != 1 ]; then
  pid=$(cc_find_pid) || exit 0
  has_tty "$pid" || exit 0
fi

mkdir -p "$STATE"
[ -e "$STATE/$sid.triggered" ] && exit 0   # fire once per session
date > "$STATE/$sid.triggered"

mb=$((size / 1024 / 1024))
target=$(bound_target "$sid"); new=""
[ -n "$target" ] || { target=$(bind_unrouted "$sid") && new=" This session was not attached, so it now is: ${target} (named after the session id). If you know what it is, rename it first: \`bash tools/work/work rename ${target} <co>/tickets/<ID> | user/work/<slug>\`, then use the new path in the steps below."; }
h=$(handoff_path "$sid")
case "$h" in
  */handoff/*.md) how="Edit your role's file $h in place (run \`bash tools/work/handoff ${target}\` first if it does not exist yet), then run \`bash tools/work/handoff ${target}\` to archive a copy and rebuild the index.${new}" ;;
  */DEVDOC.md|*/docs/HANDOFF.md)  how="Update $h: state, active work, TODO, and a \`## Session handoff\` section (replace any older one)." ;;
  *)            how="Write it to $h (this session is not attached to a work item)." ;;
esac
reason="This session's transcript is ${mb} MB (limit ${LIMIT_MB} MB). Hand off to a new session now, without asking the user (tools/rollover/RULES.md):
1. Write the handoff. ${how}
2. Run: bash tools/rollover/handoff.sh ${sid} \"${tp}\" [new name, only if this session is unnamed]
3. If it prints FAIL, tell the user why and keep this session as is."
python3 -c 'import json, sys; print(json.dumps({"decision": "block", "reason": sys.argv[1]}))' "$reason"
