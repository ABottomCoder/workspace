#!/bin/bash
# Make Claude Code keep this main dir's transcripts inside it (spec §3.6):
#   ~/.claude/projects/<encoded main dir>  ->  <main>/user/sessions   (symlink; Windows: junction, tools/lib/link.sh)
# Idempotent. Refuses when a real non-empty transcript dir exists, unless --merge (moves its
# entries into user/sessions first; stops on any name clash). --dry-run prints the plan only.
# Run it with no Claude session open in the main dir.
set -eu
MAIN="$(cd "$(dirname "$0")/../.." && pwd)"
. "$MAIN/tools/lib/cc-internals.sh"
. "$MAIN/tools/lib/link.sh"
merge=0; dry=0
for a in "$@"; do case "$a" in --merge) merge=1;; --dry-run) dry=1;; *) echo "usage: $0 [--merge] [--dry-run]" >&2; exit 2;; esac; done
link=$(cc_transcript_dir "$MAIN"); dest="$MAIN/user/sessions"
run() { echo "+ $*"; [ $dry = 1 ] || "$@"; }

echo "link: $link"; echo "dest: $dest"
if [ -L "$link" ]; then
  cur=$(readlink "$link")
  [ "$cur" = "$dest" ] && { echo "already linked; nothing to do"; exit 0; }
  echo "refusing: $link is a symlink to $cur, not $dest. Remove it yourself if that is intended." >&2; exit 1
fi
if [ -d "$link" ]; then
  if [ -n "$(ls -A "$link")" ]; then
    [ $merge = 1 ] || { echo "refusing: $link is a real dir with $(ls -A "$link" | wc -l | tr -d ' ') entries. Re-run with --merge to move them into $dest." >&2; exit 1; }
    for e in "$link"/* "$link"/.[!.]*; do
      [ -e "$e" ] || continue
      [ -e "$dest/$(basename "$e")" ] && { echo "refusing: $dest/$(basename "$e") already exists; resolve the clash first" >&2; exit 1; }
    done
    for e in "$link"/* "$link"/.[!.]*; do [ -e "$e" ] && run mv "$e" "$dest/"; done
  fi
  run mkdir -p "$dest"; run rmdir "$link"
elif [ -e "$link" ]; then
  echo "refusing: $link exists and is not a directory" >&2; exit 1
fi
run mkdir -p "$dest" "$(dirname "$link")"
run dir_link "$dest" "$link"
echo "done: new transcripts for $MAIN land in $dest"
