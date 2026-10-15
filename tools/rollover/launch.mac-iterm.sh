#!/bin/bash
# launch variant: macOS + iTerm2. Usage: launch.mac-iterm.sh <dir> <command>
sq() { printf "'%s'" "${1//\'/\'\\\'\'}"; }
osascript -e 'on run argv' -e 'tell application "iTerm"' \
  -e 'set w to (create window with default profile)' \
  -e 'tell current session of w to write text (item 1 of argv)' \
  -e 'end tell' -e 'end run' "cd $(sq "$1") && $2" >/dev/null \
  || { echo "launch: osascript could not open an iTerm window" >&2; exit 1; }
