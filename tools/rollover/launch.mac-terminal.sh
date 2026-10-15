#!/bin/bash
# launch variant: macOS + Terminal.app. Usage: launch.mac-terminal.sh <dir> <command>
sq() { printf "'%s'" "${1//\'/\'\\\'\'}"; }
osascript -e 'on run argv' -e 'tell application "Terminal"' -e 'activate' \
  -e 'do script (item 1 of argv)' -e 'end tell' -e 'end run' "cd $(sq "$1") && $2" >/dev/null \
  || { echo "launch: osascript could not open a Terminal window" >&2; exit 1; }
