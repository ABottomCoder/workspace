#!/bin/bash
# tools/work: project state files, state policy, log placement, restore, tickets.
. "$(dirname "$0")/lib.sh"
W="$REPO/tools/work/work"

setup() {   # fresh WORK_ROOT with templates; exports WORK_ROOT and a fake session id
  R=$(new_tmp); mkdir -p "$R/user/sessions" "$R/templates" "$R/business/co"
  cp -r "$REPO/templates/project" "$REPO/templates/ticket" "$R/templates/"
  export WORK_ROOT="$R" CLAUDE_CODE_SESSION_ID="test-$RANDOM"
}
restore() { printf '{"session_id":"%s","source":"compact"}' "$CLAUDE_CODE_SESSION_ID" | bash "$W" restore; }
policy() { printf '**Project state policy:** %s\n' "$1" > "$R/business/co/stack.md"; }

test_state_file_precedence() {
  setup
  mkdir -p "$R/business/co/a/docs" "$R/business/co/b/.state" "$R/business/co/c"
  printf '# a\n' > "$R/business/co/a/docs/HANDOFF.md"; printf '# b\n\n## Change log\n\n' > "$R/business/co/b/.state/DEVDOC.md"
  bash "$W" attach co/a >/dev/null; assert_contains "$(bash "$W" show)" "state: docs/HANDOFF.md"
  bash "$W" attach co/b >/dev/null; assert_contains "$(bash "$W" show)" "state: .state/DEVDOC.md"
  bash "$W" attach co/c >/dev/null; assert_contains "$(bash "$W" show)" "state: DEVDOC.md"
  assert_no_file "$R/business/co/a/DEVDOC.md"
}

test_policy_in_repo_creates_handoff() {
  setup; policy 'in-repo `docs/HANDOFF.md`'; mkdir -p "$R/business/co/p"
  bash "$W" attach co/p >/dev/null
  assert_file "$R/business/co/p/docs/HANDOFF.md"; assert_no_file "$R/business/co/p/DEVDOC.md"
}

test_policy_orphan_stops() {
  setup; policy 'orphan branch `state/x`'; mkdir -p "$R/business/co/p"
  out=$(bash "$W" attach co/p 2>&1); rc=$?
  assert_eq "$rc" 1 "exit code"; assert_contains "$out" "orphan branch"; assert_contains "$out" "still attached to"
}

test_policy_template_line_means_unset() {
  setup; cp "$REPO/templates/business/stack.md" "$R/business/co/stack.md"; mkdir -p "$R/business/co/p"
  bash "$W" attach co/p >/dev/null
  assert_file "$R/business/co/p/DEVDOC.md"
  assert_eq "$(head -1 "$R/business/co/p/DEVDOC.md")" "# p — dev doc" "template filled"
}

test_log_keeps_date_bullets_outside_change_log() {
  setup; mkdir -p "$R/business/co/p/docs"
  printf '# p\n\n## Session log\n- 2026-10-01\n  did stuff\n' > "$R/business/co/p/docs/HANDOFF.md"
  bash "$W" attach co/p >/dev/null; bash "$W" log "entry"
  assert_contains "$(cat "$R/business/co/p/docs/HANDOFF.md")" "- 2026-10-01"
}

test_log_removes_template_placeholder() {
  setup; mkdir -p "$R/business/co/p"; bash "$W" attach co/p >/dev/null; bash "$W" log "first"
  sec=$(sed -n '/^## Change log/,/^## Reference/p' "$R/business/co/p/DEVDOC.md")
  assert_contains "$sec" "first"; assert_eq "$(printf '%s\n' "$sec" | grep -c '^- [0-9-]*$')" 0 "placeholder gone"
}

test_log_new_section_after_h1_and_restored_from_big_file() {
  setup; mkdir -p "$R/business/co/p/docs"
  { printf '# p\n\n## Current state\nok\n'; for i in $(seq 2500); do echo "filler line $i"; done; } > "$R/business/co/p/docs/HANDOFF.md"
  bash "$W" attach co/p >/dev/null; bash "$W" log "tail entry"
  assert_eq "$(sed -n '3p' "$R/business/co/p/docs/HANDOFF.md")" "## Change log" "section right after H1"
  assert_contains "$(restore)" "tail entry" "entry within restore budget"
}

test_log_skips_fenced_and_front_matter() {
  setup; mkdir -p "$R/business/co/p/docs"
  printf -- '---\ntitle: x\n---\nintro\n```bash\n# start server\n```\n' > "$R/business/co/p/docs/HANDOFF.md"
  bash "$W" attach co/p >/dev/null; bash "$W" log "e"
  f="$R/business/co/p/docs/HANDOFF.md"
  assert_eq "$(sed -n '5p' "$f")" "## Change log" "after front matter"
  assert_contains "$(sed -n '/```bash/,/```$/p' "$f")" "# start server"
  assert_not_contains "$(sed -n '/```bash/,/```$/p' "$f")" "Change log" "not inside fence"
}

test_ticket_flow() {
  setup
  bash "$W" new-ticket co T-1 "a ticket" >/dev/null; assert_file "$R/business/co/tickets/T-1/STATE.md"
  bash "$W" attach co/tickets/T-1 >/dev/null; bash "$W" log "did a thing"; bash "$W" handoff >/dev/null
  out=$(restore); assert_contains "$out" "## STATE.md"; assert_contains "$out" "## HANDOFF.md"; assert_contains "$out" "did a thing"
  bash "$W" index co >/dev/null; assert_contains "$(cat "$R/business/co/tickets/INDEX.md")" "T-1"
}

test_restore_unattached() {
  setup; assert_contains "$(printf '{"session_id":"nobody","source":"startup"}' | bash "$W" restore)" "Not attached"
}

run_tests
