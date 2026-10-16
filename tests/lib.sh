#!/bin/bash
# Tiny assertion helpers for tests/test_*.sh. Plain bash: Git Bash on Windows, bash on macOS/Linux.
# A test file sources this, defines test_* functions, and ends with `run_tests`.
# Each test runs once in a subshell (env/cwd changes stay inside); exit status 0 pass, 1 fail, 3 skip.
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$REPO/tools/lib/os.sh"
_t_failed=0; _t_skip=0; _cur=""

fail() { echo "  FAIL [$_cur] $*"; _t_failed=1; }
assert_eq() { [ "$1" = "$2" ] || fail "${3:-} expected [$2] got [$1]"; }
assert_contains() { case "$1" in *"$2"*) ;; *) fail "${3:-} [$2] not in: $(printf '%s' "$1" | head -c 200)";; esac; }
assert_not_contains() { case "$1" in *"$2"*) fail "${3:-} unexpected [$2]";; esac; }
assert_file() { [ -f "$1" ] || fail "missing file ${1#$REPO/}"; }
assert_no_file() { [ ! -e "$1" ] || fail "unexpected file ${1#$REPO/}"; }
# usage: skip_unless_os win || return 0
skip_unless_os() { [ "$(os_variant)" = "$1" ] && return 0; echo "  skip [$_cur] needs $1"; _t_skip=1; return 1; }
new_tmp() { mktemp -d "${TMPDIR:-/tmp}/wstest.XXXXXX"; }

run_tests() {
  local t rc pass=0 failn=0 skip=0 file; file=$(basename "$0" .sh)
  for t in $(declare -F | awk '{print $3}' | grep '^test_'); do
    _cur="$file:${t#test_}"
    ( _t_failed=0; _t_skip=0; "$t"; [ "$_t_failed" = 1 ] && exit 1; [ "$_t_skip" = 1 ] && exit 3; exit 0 ); rc=$?
    case $rc in 0) pass=$((pass + 1)) ;; 3) skip=$((skip + 1)) ;; *) failn=$((failn + 1)) ;; esac
  done
  echo "$file: $pass passed, $failn failed, $skip skipped"
  [ "$failn" = 0 ]
}
