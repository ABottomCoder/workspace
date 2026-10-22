#!/bin/bash
# Usage: handoff.sh <session_id> <transcript_path> [new_name_if_unnamed]
# Starts a new interactive session in the main dir (named <Desc>_<app>_<n+1>, binding copied,
# prompted to read the handoff), waits for its transcript, then terminates the current claude
# process. Rules: RULES.md. Test without exiting: CLAUDE_ROLLOVER_DRYRUN=1.
. "$(dirname "$0")/lib.sh"
sid=${1:-}; tp=${2:-}; fallback=${3:-}
[ -n "$sid" ] && [ -f "$tp" ] || { echo "FAIL: usage: handoff.sh <session_id> <transcript_path> [name]"; exit 1; }
h=$(handoff_path "$sid")
trig="$STATE/$sid.triggered"
[ -s "$h" ] || { echo "FAIL: handoff missing or empty: $h"; exit 1; }
! grep -Eq '<the literal next|<3.6 bullets' "$h" || { echo "FAIL: handoff is still the empty template: $h"; exit 1; }
[ ! -e "$trig" ] || [ "$h" -nt "$trig" ] || { echo "FAIL: handoff not updated since the rollover fired: $h"; exit 1; }
old_pid=$(cc_find_pid) || { echo "FAIL: cannot find the current claude process"; exit 1; }

# Name: <Desc>_<app>_<n> -> n+1 (padding kept); named without a number -> append _2;
# unnamed -> caller's name, else <bound item>_None_2.
cur=$(cc_session_title "$tp")
if [ -z "$cur" ]; then
  t=$(bound_target "$sid")
  if [ -n "$fallback" ]; then name=$fallback
  elif [ -n "$t" ]; then name="$(basename "$t" | tr '_ ' '--')_None_2"
  else echo "FAIL: session is unnamed and not attached; pass a name as the 3rd argument"; exit 1; fi
elif [[ $cur =~ ^(.*[^0-9])([0-9]+)$ ]]; then
  num=${BASH_REMATCH[2]}
  name="${BASH_REMATCH[1]}$(printf "%0${#num}d" $((10#$num + 1)))"
else
  name="${cur}_2"
fi

new_sid=$(new_uuid) || { echo "FAIL: cannot generate a session id"; exit 1; }
# Bind before launch, so the new session's SessionStart hook already restores the work item.
if [ -f "$BIND/$sid" ]; then cp "$BIND/$sid" "$BIND/$new_sid"; echo "from=$sid" >> "$BIND/$new_sid"; fi

rel_h=${h#$ROOT/}
prompt="Take over from the previous session ${cur:-$sid}: read ${rel_h}, then tools/rollover/RULES.md (\"When you are the new session\"), and continue."
"$ROLLOVER_DIR/launch.sh" "$ROOT" "$(cc_launch_cmd "$name" "$prompt" "$new_sid")" || {
  rm -f "$BIND/$new_sid"; echo "FAIL: could not open a terminal (see message above); old session left running"; exit 1; }

# The new session's transcript appears next to ours once it starts (90 s max).
new_tp="$(dirname "$tp")/$new_sid.jsonl"
i=0; while [ ! -e "$new_tp" ] && [ $i -lt 45 ]; do sleep 2; i=$((i + 1)); done
[ -e "$new_tp" ] || { echo "FAIL: new session $new_sid did not start within 90s; old session left running"; exit 1; }

echo "$(date '+%F %T') ${cur:-<unnamed>} ($sid) -> $name ($new_sid)" >> "$STATE/rollover.log"
echo "OK: new session \"$name\" ($new_sid) started. This session (pid $old_pid) exits in 5s."
[ "${CLAUDE_ROLLOVER_DRYRUN:-0}" = 1 ] && { echo "(dry run: not exiting)"; exit 0; }
nohup sh -c "sleep 5; kill -TERM $old_pid" >/dev/null 2>&1 &
