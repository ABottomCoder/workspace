#!/bin/bash
# Project live-state file, shared by tools/work and tools/rollover (tools/work/README.md -> Project state policy).
# Source it (bash 3.2+).
#   state_file <project dir>            first existing state file, relative to the dir; fails if none
#   state_policy <root> <business>      in-repo | orphan | local | "" (unset: the stack.md line is missing or still lists options)
#   state_default <root> <business>     the file a new project gets under that policy
# Keep WORK_STATE_FILES in sync with the list in tools/work/work cmd_restore (python).
WORK_STATE_FILES="DEVDOC.md .state/DEVDOC.md docs/HANDOFF.md"
state_file() { local f; for f in $WORK_STATE_FILES; do [ -f "$1/$f" ] && { echo "$f"; return 0; }; done; return 1; }
state_policy() {
  local l; l=$(grep -m1 -i 'project state policy' "$1/business/$2/stack.md" 2>/dev/null)
  case "$l" in ""|*"|"*) echo "" ;; *docs/HANDOFF.md*) echo in-repo ;; *[Oo]rphan*) echo orphan ;; *) echo local ;; esac
}
state_default() { case "$(state_policy "$1" "$2")" in in-repo) echo docs/HANDOFF.md ;; orphan) echo .state/DEVDOC.md ;; *) echo DEVDOC.md ;; esac; }
