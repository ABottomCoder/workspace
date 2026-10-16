#!/bin/bash
# PostToolUse hook (Write|Edit|MultiEdit). Two checks on the file just written:
#  1. memory or the main CLAUDE.md -> knowledge-routing self-check reminder;
#  2. a framework file (not user/, business/, .staging/) -> warning if it now contains a
#     user/denylist.txt term, an absolute home path or a secret-like token.
here="$(cd "$(dirname "$0")" && pwd)"; . "$here/patterns.sh"
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$here/../.." && pwd)}"
f=$(python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))
except Exception: pass' 2>/dev/null)
[ -n "$f" ] || exit 0
# Windows: Claude Code passes D:\x paths; compare everything in one (POSIX) form or nothing ever matches.
. "$here/../lib/os.sh"
if [ "$(os_variant)" = win ]; then f=$(cygpath -u "$f"); ROOT=$(cygpath -u "$ROOT"); fi
emit() { python3 -c 'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":sys.argv[1]}}))' "$1"; }

case "$f" in
  "$ROOT/CLAUDE.md"|"$ROOT"/user/memory/*|*/.claude/projects/*/memory/*)
    emit "Routing self-check: you just wrote an always-loaded file (memory or the main CLAUDE.md). (1) Would an unrelated session waste context on this? Then move it down to business/<co>/..., the project CLAUDE.md/DEVDOC.md or the ticket, and leave at most a one-line pointer. (2) Memory holds only pointers and things that fit nowhere else, never business facts. (3) One fact, one home; elsewhere only pointers. (4) Main CLAUDE.md stays an index under 200 lines. Fix the write now if any rule is broken."
    exit 0 ;;
esac

case "$f" in "$ROOT"/*) rel=${f#$ROOT/} ;; *) exit 0 ;; esac
printf '%s\n' "$rel" | grep -qE "$GUARD_BLOCKED_DIRS" && exit 0
[ -f "$f" ] && LC_ALL=C grep -Iq '' "$f" || exit 0
msg=""
re=$(guard_denylist_re "$ROOT/user/denylist.txt") && {
  h=$(grep -niE "$re" "$f" | head -5 | cut -c1-120); [ -n "$h" ] && msg="$msg
denylist terms (business/person identifiers):
$h"; }
h=$(grep -nE "$GUARD_HOMEPATH_RE" "$f" | head -5 | cut -c1-120); [ -n "$h" ] && msg="$msg
absolute home paths:
$h"
h=$(grep -nE "$GUARD_SECRET_RE" "$f" | cut -d: -f1 | paste -sd, -); [ -n "$h" ] && msg="$msg
secret-like token on line(s) $h (value not shown)"
[ -n "$msg" ] && emit "Framework-leak warning: $rel is a framework file (git-tracked, company-agnostic, English) but contains:$msg
Replace names with roles or neutral examples, use relative or \$CLAUDE_PROJECT_DIR paths, and move business or personal material to business/<co>/ or user/. The pre-commit guard will block it otherwise."
exit 0
