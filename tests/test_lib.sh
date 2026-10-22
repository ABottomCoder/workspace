#!/bin/bash
# tools/lib: OS detection, native paths, transcript dir encoding, links, state policy, rollover handoff path.
. "$(dirname "$0")/lib.sh"

test_os_variant_known() {
  v=$(os_variant); case "$v" in mac|win|linux) ;; *) fail "unknown os_variant [$v]";; esac
}

test_transcript_dir_encoding() {
  . "$REPO/tools/lib/cc-internals.sh"
  assert_eq "$(cc_encode_path 'D:\workspace')" "D--workspace" "windows form"
  assert_eq "$(cc_encode_path '/opt/x/ws')" "-opt-x-ws" "posix form"
  d=$(CC_PROJECTS_BASE=/base cc_transcript_dir "$REPO")
  assert_eq "$d" "/base/$(cc_encode_path "$(native_path "$REPO")")" "uses the native path"
}

test_dir_link_writes_through() {
  . "$REPO/tools/lib/link.sh"
  d=$(new_tmp); mkdir -p "$d/target"; dir_link "$d/target" "$d/lnk" || fail "dir_link failed"
  [ -L "$d/lnk" ] || fail "not a link"
  echo hi > "$d/lnk/probe"; assert_file "$d/target/probe"
  [ "$(os_variant)" = win ] && cmd //c rmdir "$(cygpath -w "$d/lnk")" >/dev/null   # remove the junction only
  assert_file "$d/target/probe"
}

test_hook_link_idempotent() {
  . "$REPO/tools/lib/link.sh"
  d=$(new_tmp); printf '#!/bin/sh\necho ran\n' > "$d/script"; chmod +x "$d/script"
  hook_installed "$d/script" "$d/hook" && fail "installed before install"
  hook_link "$d/script" "$d/hook"; hook_installed "$d/script" "$d/hook" || fail "not detected after install"
  assert_eq "$(sh "$d/hook")" "ran" "hook runs the script"
}

test_state_policy_parsing() {
  . "$REPO/tools/lib/state.sh"
  d=$(new_tmp); mkdir -p "$d/business/a" "$d/business/b" "$d/business/c" "$d/business/t"
  printf '**Project state policy:** in-repo `docs/HANDOFF.md`\n' > "$d/business/a/stack.md"
  printf '**Project state policy:** orphan branch `state/x`\n' > "$d/business/b/stack.md"
  printf '**Project state policy:** local `DEVDOC.md`\n' > "$d/business/c/stack.md"
  cp "$REPO/templates/business/stack.md" "$d/business/t/stack.md"
  assert_eq "$(state_policy "$d" a)" in-repo; assert_eq "$(state_default "$d" a)" docs/HANDOFF.md
  assert_eq "$(state_policy "$d" b)" orphan; assert_eq "$(state_default "$d" b)" .state/DEVDOC.md
  assert_eq "$(state_policy "$d" c)" local; assert_eq "$(state_default "$d" c)" DEVDOC.md
  assert_eq "$(state_policy "$d" t)" "" "template line = unset"; assert_eq "$(state_policy "$d" none)" "" "no stack.md"
}

test_rollover_handoff_path_follows_state() {
  d=$(new_tmp); mkdir -p "$d/tools" "$d/user/sessions/.bindings" "$d/business/a/p1/docs" "$d/business/a/p2" "$d/business/b/q"
  cp -r "$REPO/tools/lib" "$REPO/tools/rollover" "$d/tools/"
  printf '**Project state policy:** in-repo `docs/HANDOFF.md`\n' > "$d/business/a/stack.md"; printf '# p1\n' > "$d/business/a/p1/docs/HANDOFF.md"
  printf 'target=business/a/p1\n' > "$d/user/sessions/.bindings/s1"; printf 'target=business/a/p2\n' > "$d/user/sessions/.bindings/s2"
  printf 'target=business/b/q\n' > "$d/user/sessions/.bindings/s3"
  out=$(. "$d/tools/rollover/lib.sh"; handoff_path s1; handoff_path s2; handoff_path s3; handoff_path none)
  assert_contains "$out" "business/a/p1/docs/HANDOFF.md" "existing in-repo file"
  assert_contains "$out" "business/a/p2/docs/HANDOFF.md" "new in-repo project"
  assert_contains "$out" "business/b/q/DEVDOC.md" "no policy"
  assert_contains "$out" "user/sessions/.rollover/none.handoff.md" "unbound session"
  printf 'target=business/b/tickets/T-1\nrole=qa\n' > "$d/user/sessions/.bindings/s4"
  assert_contains "$(. "$d/tools/rollover/lib.sh"; handoff_path s4)" "business/b/tickets/T-1/handoff/qa.md" "ticket role file"
}

test_rollover_binds_unrouted_session() {
  d=$(new_tmp); mkdir -p "$d/tools" "$d/user/sessions" "$d/templates"
  cp -r "$REPO/tools/lib" "$REPO/tools/rollover" "$REPO/tools/work" "$d/tools/"; cp -r "$REPO/templates/ticket" "$d/templates/"
  out=$(. "$d/tools/rollover/lib.sh"; bind_unrouted 12345678-aaaa; handoff_path 12345678-aaaa)
  assert_contains "$out" "user/work/s-12345678"; assert_contains "$out" "user/work/s-12345678/handoff/main.md"
  assert_file "$d/user/work/s-12345678/STATE.md"
}

run_tests
