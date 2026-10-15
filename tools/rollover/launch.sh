#!/bin/bash
# Usage: launch.sh <dir> <command>  — open a new terminal window running `cd <dir> && <command>`.
# Picks launch.<variant>.sh: $WORKSPACE_TERMINAL if set, else detected from $TERM_PROGRAM.
# Add a terminal by adding launch.<variant>.sh (and a row in docs/compatibility.md).
here="$(cd "$(dirname "$0")" && pwd)"
v=${WORKSPACE_TERMINAL:-}
if [ -z "$v" ]; then
  case "${TERM_PROGRAM:-}" in
    iTerm.app) v=mac-iterm ;;
    Apple_Terminal) v=mac-terminal ;;
    *) [ -n "${TMUX:-}" ] && v=tmux ;;
  esac
fi
avail=$(cd "$here" && ls launch.*.sh 2>/dev/null | sed 's/^launch\.//; s/\.sh$//' | tr '\n' ' ')
if [ -z "$v" ]; then
  echo "launch: cannot detect the terminal (TERM_PROGRAM='${TERM_PROGRAM:-}'). Set WORKSPACE_TERMINAL to one of: $avail" >&2; exit 1
fi
[ -f "$here/launch.$v.sh" ] || { echo "launch: no variant launch.$v.sh. Available: $avail" >&2; exit 1; }
exec bash "$here/launch.$v.sh" "$@"
