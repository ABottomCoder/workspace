#!/bin/bash
# Report absolute home paths (/Users/<name>, /home/<name>) in framework files. Exit 1 on any hit.
# Usage: path-lint.sh [dir]  (default: the framework repo; user/, business/, .staging/ are skipped)
here="$(cd "$(dirname "$0")" && pwd)"; . "$here/patterns.sh"
dir="$(cd "${1:-$here/../..}" && pwd)"
if git -C "$dir" rev-parse --git-dir >/dev/null 2>&1; then
  list=$(cd "$dir" && git ls-files -co --exclude-standard)
else
  list=$(cd "$dir" && find . -type f ! -path './.git/*' | sed 's|^\./||')
fi
hits=$(cd "$dir" && printf '%s\n' "$list" | grep -vE "$GUARD_BLOCKED_DIRS" | grep -v '^$' \
       | tr '\n' '\0' | xargs -0 grep -InE "$GUARD_HOMEPATH_RE" 2>/dev/null)
[ -z "$hits" ] && { echo "path-lint: clean ($dir)"; exit 0; }
printf '%s\n' "$hits" | cut -c1-160; echo "path-lint: absolute home paths found; use \$CLAUDE_PROJECT_DIR, paths relative to the main dir, or ~" >&2; exit 1
