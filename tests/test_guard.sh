#!/bin/bash
# tools/guard: leak patterns, route-check hook, pre-commit blocking in a real git repo.
. "$(dirname "$0")/lib.sh"
. "$REPO/tools/guard/patterns.sh"

hits() { printf '%s\n' "$1" | grep -cE "$2"; }
hits_i() { printf '%s\n' "$1" | grep -ciE "$2"; }   # the guard matches the denylist case-insensitively
# Fixture paths are assembled at runtime so this file never contains a literal home path (the guard would block it).
U="Us""ers"; H="ho""me"; BS='\'

test_homepath_pattern() {
  assert_eq "$(hits "/$U/bob/x" "$GUARD_HOMEPATH_RE")" 1 "mac home"
  assert_eq "$(hits "/$H/al/x" "$GUARD_HOMEPATH_RE")" 1 "linux home"
  assert_eq "$(hits "C:$BS$U${BS}bob${BS}x" "$GUARD_HOMEPATH_RE")" 1 "windows home"
  assert_eq "$(hits "C:${BS}Program Files${BS}x" "$GUARD_HOMEPATH_RE")" 0 "not a home"
  assert_eq "$(hits 'docs/users/guide' "$GUARD_HOMEPATH_RE")" 0 "relative path"
}

test_secret_pattern() {
  assert_eq "$(hits "ghp_$(printf 'a%.0s' $(seq 36))" "$GUARD_SECRET_RE")" 1 "github token"
  assert_eq "$(hits 'ghp_short' "$GUARD_SECRET_RE")" 0 "too short"
}

test_denylist_word_boundaries() {
  d=$(new_tmp); printf '# c\nAcmeCorp\n' > "$d/deny"; re=$(guard_denylist_re "$d/deny")
  assert_eq "$(hits_i 'we work for AcmeCorp now' "$re")" 1 "word"
  assert_eq "$(hits_i 'acmecorp_x' "$re")" 1 "underscore is a boundary"
  assert_eq "$(hits_i 'AcmeCorporation' "$re")" 0 "inside a longer word"
}

route() {   # route <file path as the OS gives it> -> hook output
  python3 -c 'import json,sys; print(json.dumps({"tool_input": {"file_path": sys.argv[1]}}))' "$1" \
    | CLAUDE_PROJECT_DIR="$(native_path "$REPO")" bash "$REPO/tools/guard/route-check.sh"
}

test_route_check_posix_paths() {
  assert_contains "$(route "$REPO/CLAUDE.md")" "Routing self-check"
  assert_contains "$(route "$REPO/user/memory/x.md")" "Routing self-check"
  assert_eq "$(route "$REPO/business/co/x.md")" "" "business is silent"
}

test_route_check_native_windows_paths() {
  skip_unless_os win || return 0
  assert_contains "$(route "$(cygpath -w "$REPO/CLAUDE.md")")" "Routing self-check"
}

test_route_check_edit_with_chinese_text() {
  # hook input is UTF-8; read with GBK, "。" before the escaped quote broke the JSON and the check was skipped
  out=$(PYTHONIOENCODING=utf-8 python3 -c 'import json,sys; print(json.dumps({"tool_input": {"file_path": sys.argv[1], "new_string": "状态。\"x"}}, ensure_ascii=False))' \
          "$(native_path "$REPO/CLAUDE.md")" \
        | env -u PYTHONIOENCODING -u PYTHONUTF8 CLAUDE_PROJECT_DIR="$(native_path "$REPO")" bash "$REPO/tools/guard/route-check.sh")
  assert_contains "$out" "Routing self-check"
}

test_route_check_flags_leak_in_framework_file() {
  f="$REPO/docs/_wstest_probe.md"; printf 'token ghp_%s\n' "$(printf 'b%.0s' $(seq 36))" > "$f"
  out=$(route "$(native_path "$f")"); rm -f "$f"
  assert_contains "$out" "Framework-leak warning"
}

test_pre_commit_blocks_secret() {
  d=$(new_tmp); git init -q "$d/r"; mkdir -p "$d/r/tools/guard" "$d/r/user"
  cp "$REPO/tools/guard/pre-commit" "$REPO/tools/guard/"*.sh "$d/r/tools/guard/"
  cd "$d/r" || return 1
  git config core.autocrlf false
  printf 'key ghp_%s\n' "$(printf 'c%.0s' $(seq 36))" > leak.md; git add leak.md
  out=$(bash tools/guard/pre-commit 2>&1); rc=$?
  assert_eq "$rc" 1 "blocked"; assert_contains "$out" "secret-like token"
  git reset -q; printf 'clean\n' > ok.md; git add ok.md
  bash tools/guard/pre-commit >/dev/null 2>&1; assert_eq "$?" 0 "clean commit passes"
}

run_tests
