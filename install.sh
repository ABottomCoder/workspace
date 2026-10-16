#!/usr/bin/env bash
# One-time (idempotent) setup of this workspace on a machine. Safe to re-run.
#  1. user/ from templates/user/ (only files that don't exist yet)
#  2. .claude/settings.local.json with autoMemoryDirectory -> user/memory (machine-specific absolute path)
#  3. transcripts: ~/.claude/projects/<encoded main dir> -> user/sessions (symlink; Windows: junction)
#  4. pre-commit leak guard
set -euo pipefail
MAIN="$(cd "$(dirname "$0")" && pwd -P)"
cd "$MAIN"

echo "== user/"
mkdir -p user/memory user/sessions user/logs user/work business
if [ -d templates/user ]; then
  (cd templates/user && find . -type f) | while read -r f; do
    case "$f" in ./feedback/feedback_use_subagents.md) continue ;; ./feedback/*) dst="user/memory/${f#./feedback/}" ;; ./MEMORY.md) dst="user/memory/MEMORY.md" ;; *) dst="user/${f#./}" ;; esac
    if [ ! -e "$dst" ]; then mkdir -p "$(dirname "$dst")"; cp "templates/user/${f#./}" "$dst"; echo "  + $dst"; fi
  done
fi
[ -e user/denylist.txt ] || printf '# Business/personal identifiers that must never appear in framework files (one per line)\n' > user/denylist.txt

echo "== .claude/settings.local.json"
LOCAL=.claude/settings.local.json
. tools/lib/os.sh   # Claude Code needs the OS-native path (Windows: D:\...)
python3 - "$LOCAL" "$(native_path "$MAIN/user/memory")" <<'EOF'
import json, os, sys
p, mem = sys.argv[1], sys.argv[2]
d = json.load(open(p)) if os.path.exists(p) else {}
if d.get("autoMemoryDirectory") != mem:
    d["autoMemoryDirectory"] = mem
    json.dump(d, open(p, "w"), indent=2); open(p, "a").write("\n")
    print("  autoMemoryDirectory =", mem)
else:
    print("  ok")
EOF

echo "== transcripts"
tools/sessions/setup-transcript-link.sh

echo "== git guard"
if [ -d .git ]; then tools/guard/install.sh; else echo "  not a git repo, skipped"; fi

cat <<EOF

Done. Also required at user level (~/.claude/settings.json): "cleanupPeriodDays": 36500
so Claude Code never deletes old transcripts. Start Claude Code in: $MAIN
EOF
