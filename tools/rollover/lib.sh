# Shared helpers for tools/rollover. Platform differences are isolated here (see docs/compatibility.md).
ROLLOVER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$ROLLOVER_DIR/../.." && pwd)"
. "$ROOT/tools/lib/cc-internals.sh"
. "$ROOT/tools/lib/state.sh"
STATE="$ROOT/user/sessions/.rollover"
BIND="$ROOT/user/sessions/.bindings"

# Bytes in a file. GNU stat first: BSD/macOS stat rejects -c, while GNU `stat -f` means
# "file system" and would print garbage instead of failing.
file_size() { stat -c %s "$1" 2>/dev/null || stat -f %z "$1"; }

# True if the process has a controlling terminal. No tty prints "??" on macOS, "?" on Linux.
has_tty() {
  local t; t=$(ps -o tty= -p "$1" 2>/dev/null | tr -d ' ')
  case "$t" in ""|"?"|"??") return 1 ;; *) return 0 ;; esac
}

bound_target() { [ -f "$BIND/$1" ] && sed -n 's/^target=//p' "$BIND/$1" | head -1; }
bound_role() { local r; r=$([ -f "$BIND/$1" ] && sed -n 's/^role=//p' "$BIND/$1" | head -1); echo "${r:-main}"; }

# Unattached session about to roll over: give it a work item named after its id, user/work/s-<sid8>
# (rename it once its subject is known: tools/work/work rename). Prints the new target.
bind_unrouted() {
  local t="user/work/s-${1:0:8}"
  [ -d "$ROOT/$t" ] || WORK_ROOT="$ROOT" bash "$ROOT/tools/work/work" new-ticket user "s-${1:0:8}" "Unrouted session ${1:0:8}" >/dev/null || return 1
  mkdir -p "$BIND"; printf 'target=%s\nrole=main\nattached=%s\n' "$t" "$(date -u +%Y-%m-%dT%H:%MZ)" > "$BIND/$1"
  echo "$t"
}

# Where this session's rollover handoff goes: its role's file in the bound ticket, the project state
# file, else a per-session file.
handoff_path() {
  local t; t=$(bound_target "$1")
  case "$t" in
    "") echo "$STATE/$1.handoff.md" ;;
    user/work/*|business/*/tickets/*) echo "$ROOT/$t/handoff/$(bound_role "$1").md" ;;
    *) local f; f=$(state_file "$ROOT/$t") || f=$(state_default "$ROOT" "$(echo "$t" | cut -d/ -f2)"); echo "$ROOT/$t/$f" ;;
  esac
}

new_uuid() { python3 -c 'import uuid; print(uuid.uuid4())'; }
