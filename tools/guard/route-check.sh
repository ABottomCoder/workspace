#!/bin/bash
# PostToolUse hook (Write|Edit|MultiEdit). Two checks on the file just written:
#  1. memory or the main CLAUDE.md -> knowledge-routing self-check reminder (+ MEMORY.md size warning);
#  2. a framework file (not user/, business/, .staging/) -> warning if it now contains a
#     user/denylist.txt term, an absolute home path or a secret-like token.
here="$(cd "$(dirname "$0")" && pwd)"; . "$here/patterns.sh"
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$here/../.." && pwd)}"
# stdin is UTF-8; the locale codec (GBK on a Chinese Windows) broke the JSON of an edit with Chinese text in it
f=$(python3 -c 'import json,sys
sys.stdout.reconfigure(encoding="utf-8")
try: print(json.loads(sys.stdin.buffer.read().decode("utf-8")).get("tool_input",{}).get("file_path",""))
except Exception: pass' 2>/dev/null)
[ -n "$f" ] || exit 0
# Windows: Claude Code passes D:\x paths; compare everything in one (POSIX) form or nothing ever matches.
. "$here/../lib/os.sh"
if [ "$(os_variant)" = win ]; then f=$(cygpath -u "$f"); ROOT=$(cygpath -u "$ROOT"); fi
emit() { python3 -c 'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":sys.argv[1]}}))' "$1"; }

case "$f" in
  "$ROOT/CLAUDE.md"|"$ROOT"/user/memory/*|*/.claude/projects/*/memory/*)
    emit "Routing self-check: you just wrote an always-loaded file (memory or the main CLAUDE.md). (1) Would an unrelated session waste context on this? Then move it down to business/<co>/..., the project CLAUDE.md/DEVDOC.md or the ticket, and leave at most a one-line pointer. (2) Memory holds only pointers and things that fit nowhere else, never business facts. (3) One fact, one home; elsewhere only pointers. (4) Main CLAUDE.md stays an index under 200 lines. Fix the write now if any rule is broken."
    m="$ROOT/user/memory/MEMORY.md"   # the index silently stops loading past 25 KB / 200 lines
    if [ -f "$m" ]; then b=$(wc -c < "$m" | tr -d ' '); l=$(wc -l < "$m" | tr -d ' ')
      { [ "$b" -gt 20480 ] || [ "$l" -gt 180 ]; } && emit "MEMORY.md is $((b / 1024)) KB / $l lines; it stops loading past 25 KB / 200 lines. Compress superseded rows now."
    fi
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
