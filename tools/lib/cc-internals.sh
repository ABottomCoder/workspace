#!/bin/bash
# Claude Code internals in ONE place. These are undocumented behaviours that may change with a
# Claude Code upgrade; when one breaks, fix it here only. Used by tools/work, tools/rollover,
# tools/sessions. Source it (bash 3.2+), or run it: cc-internals.sh <function> [args].
#
#   cc_encode_path <abs path>      transcript dir name: every non-alphanumeric char -> '-'
#   cc_projects_base               ~/.claude/projects (override: CC_PROJECTS_BASE, for tests)
#   cc_transcript_dir <abs path>   <projects base>/<encoded path>
#   cc_session_title <transcript>  latest custom title (`/rename` or `claude -n`), empty if none
#   cc_current_session_id <dir>    $CLAUDE_CODE_SESSION_ID / $CLAUDE_SESSION_ID, else newest *.jsonl in <dir>
#   cc_find_pid                    PID of the claude process this script runs under
#   cc_launch_cmd <name> <prompt> <uuid>  shell command starting a named session with that id

# Claude Code (JS) replaces per UTF-16 unit; sed per character. Only differs for non-BMP chars.
cc_encode_path() { printf '%s' "$1" | sed 's/[^A-Za-z0-9]/-/g'; }

cc_projects_base() { printf '%s' "${CC_PROJECTS_BASE:-$HOME/.claude/projects}"; }

# Claude Code encodes the OS-native path (Windows: D:\x -> D--x), so Git Bash paths (/d/x) are converted first.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/os.sh"
cc_transcript_dir() { printf '%s/%s' "$(cc_projects_base)" "$(cc_encode_path "$(native_path "$1")")"; }

# Transcript records: {"type":"custom-title","customTitle":"<name>","sessionId":"..."}; last one wins.
cc_session_title() {
  [ -f "$1" ] || return 0
  grep '"custom-title"' "$1" | tail -1 | python3 -c '
import json, sys
line = sys.stdin.read().strip()
try: print(json.loads(line).get("customTitle", "") if line else "")
except Exception: print("")'
}

cc_current_session_id() {
  local sid="${CLAUDE_CODE_SESSION_ID:-${CLAUDE_SESSION_ID:-}}" f
  if [ -z "$sid" ] && [ -n "${1:-}" ]; then
    f=$(ls -t "$1"/*.jsonl 2>/dev/null | head -1)
    [ -n "$f" ] && { sid=$(basename "$f" .jsonl); echo "cc: no session id in env; guessed newest transcript $sid" >&2; }
  fi
  [ -n "$sid" ] && printf '%s' "$sid"
}

cc_find_pid() {
  if [ -n "${CLAUDE_PID:-}" ] && kill -0 "$CLAUDE_PID" 2>/dev/null; then echo "$CLAUDE_PID"; return 0; fi
  local p=$$ comm
  while [ "${p:-0}" -gt 1 ]; do
    comm=$(ps -o comm= -p "$p" 2>/dev/null)
    [ "$(basename "$comm")" = claude ] && { echo "$p"; return 0; }
    p=$(ps -o ppid= -p "$p" 2>/dev/null | tr -d ' ')
  done
  return 1
}

# Single-quote for the shell (bash 3.2's printf %q mangles UTF-8).
cc_sq() { printf "'%s'" "${1//\'/\'\\\'\'}"; }
cc_launch_cmd() { printf 'claude --session-id %s -n %s %s' "$(cc_sq "$3")" "$(cc_sq "$1")" "$(cc_sq "$2")"; }

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  fn="cc_${1:-}"; shift || true
  type "$fn" >/dev/null 2>&1 || { sed -n '5,13p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
  "$fn" "$@"
fi
