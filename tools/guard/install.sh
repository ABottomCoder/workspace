#!/bin/bash
# Install the pre-commit guard as a git hook (symlink). Usage: install.sh [repo dir] [--force]
# Default repo: the framework repo this script lives in. --force replaces an existing hook.
set -eu
here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/../.." && pwd)"; force=0
for a in "$@"; do case "$a" in --force) force=1;; *) repo="$(cd "$a" && pwd)";; esac; done
hooks="$(cd "$repo" && git rev-parse --git-path hooks)"; case "$hooks" in /*) ;; *) hooks="$repo/$hooks";; esac
hook="$hooks/pre-commit"
if [ -L "$hook" ] && [ "$(readlink "$hook")" = "$here/pre-commit" ]; then echo "already installed: $hook"; exit 0; fi
if [ -e "$hook" ] && [ $force = 0 ]; then echo "refusing: $hook exists (re-run with --force to replace)" >&2; exit 1; fi
mkdir -p "$hooks"; ln -sfn "$here/pre-commit" "$hook"; chmod +x "$here/pre-commit"
echo "installed: $hook -> $here/pre-commit"
