# Shared helpers for apps/bin scripts. Source it: . "$(dirname "$0")/lib.sh"
# Channel-agnostic: nothing here knows about any chat vendor.
APPS_BIN="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPS_ROOT="$(cd "$APPS_BIN/.." && pwd)"
MAIN="${WORKSPACE_MAIN:-$(cd "$APPS_ROOT/.." && pwd)}"   # main dir = parent of apps/
BUSINESS="$MAIN/business"

# Chat text is UTF-8; on a Chinese Windows Python's default codec is GBK, which garbles or chokes on it
# (a CJK character before an escaping backslash breaks the JSON line; "⚠️" cannot be printed).
export PYTHONUTF8=1

die() { echo "app: $*" >&2; exit 1; }
now() { date -u +%Y-%m-%dT%H:%MZ; }

# --- portability (BSD/macOS vs GNU/Linux) — see docs/compatibility.md ---
file_size()  { stat -L -f %z "$1" 2>/dev/null || stat -L -c %s "$1" 2>/dev/null; }   # -L: runtime logs are symlinks
file_mtime() { stat -L -f %m "$1" 2>/dev/null || stat -L -c %Y "$1" 2>/dev/null; }
iso_to_epoch() { date -u -jf "%Y-%m-%dT%H:%M:%S" "$1" +%s 2>/dev/null || date -u -d "$1" +%s 2>/dev/null; }

# Flat "key: value" reader (no YAML dependency on purpose).
field() { sed -n "s/^$2:[[:space:]]*//p" "$1" 2>/dev/null | sed 's/[[:space:]]*#.*$//; s/^"\(.*\)"$/\1/' | head -1; }
set_field() {   # <file> <key> <value>
  python3 - "$1" "$2" "$3" <<'EOF'
import sys, re
p, k, v = sys.argv[1:4]
s = open(p).read()
line = f"{k}: {v}"
s2, n = re.subn(rf"^{re.escape(k)}:.*$", lambda m: line, s, count=1, flags=re.M)
open(p, "w").write(s2 if n else s.rstrip("\n") + "\n" + line + "\n")
EOF
}

# --- app lookup ---------------------------------------------------------------------------
# An app id is <channel>_<name> (e.g. slack_helper). Its home is business/<co>/apps/<id>/.
# resolve_app <id|name|co/id> [business]  -> sets APP_CO APP_ID APP_HOME APP_RUN APP_CONF APP_CHANNEL APP_NAME
resolve_app() {
  local ref=$1 co=${2:-} id cands=() d
  case "$ref" in */*) co=${ref%%/*}; ref=${ref#*/};; esac
  [[ "$ref" =~ ^[a-z0-9][a-z0-9-]*(_[a-z0-9][a-z0-9-]*)?$ ]] || die "bad app id '$ref' (want <channel>_<name>, lowercase)"
  for d in "$BUSINESS"/${co:-*}/apps/*/; do
    [ -f "$d/app.yaml" ] || continue
    id=$(basename "$d")
    [ "$id" = "$ref" ] || [ "${id#*_}" = "$ref" ] && cands+=("${d%/}")
  done
  [ ${#cands[@]} -gt 0 ] || die "no app '$ref' under $BUSINESS/${co:-*}/apps/ (create it: app new <co> <channel>_<name>)"
  if [ ${#cands[@]} -gt 1 ]; then
    printf 'app: %s is ambiguous, pass --business <co>:\n' "$ref" >&2; printf '  %s\n' "${cands[@]#$BUSINESS/}" >&2; exit 1
  fi
  APP_HOME=${cands[0]}; APP_ID=$(basename "$APP_HOME"); APP_CO=$(basename "$(dirname "$(dirname "$APP_HOME")")")
  APP_RUN="$APP_HOME/.runtime"; APP_CONF="$APP_HOME/app.yaml"
  APP_CHANNEL=$(field "$APP_CONF" channel); APP_CHANNEL=${APP_CHANNEL:-${APP_ID%%_*}}
  APP_NAME=$(field "$APP_CONF" name); APP_NAME=${APP_NAME:-${APP_ID#*_}}
  APP_REF="$APP_CO/$APP_ID"
}

# Which registered app (if any) does a Claude session id belong to? Prints the app home.
app_for_session() {
  local f
  for f in "$BUSINESS"/*/apps/*/.runtime/.session-id; do
    [ -f "$f" ] || continue
    [ "$(tr -d '[:space:]' < "$f")" = "$1" ] && { dirname "$(dirname "$f")"; return 0; }
  done
  return 1
}

# Run a channel verb: channels/<kind>/<verb>.{js,mjs,sh} or an executable named <verb>.
channel_dir() { echo "$APPS_ROOT/channels/$1"; }
channel_cmd() {   # <kind> <verb> -> prints the command to run, or fails
  local d f; d=$(channel_dir "$1")
  for f in "$d/$2.js" "$d/$2.mjs" "$d/$2.sh" "$d/$2"; do
    [ -f "$f" ] || continue
    case "$f" in *.js|*.mjs) echo "node $f";; *.sh) echo "bash $f";; *) echo "$f";; esac; return 0
  done
  return 1
}

ensure_node() {   # node may be missing from PATH under service managers
  command -v node >/dev/null 2>&1 && return 0
  local d; for d in "$HOME"/.nvm/versions/node/*/bin /opt/homebrew/bin /usr/local/bin; do
    [ -x "$d/node" ] && { PATH="$d:$PATH"; export PATH; return 0; }
  done
}

hb_age() {   # <log> -> seconds since the newest [heartbeat], empty if unknown
  local hb t; hb=$(tail -400 "$1" 2>/dev/null | grep '^\[heartbeat\] ' | tail -1 | sed -E 's/^\[heartbeat\] //; s/\..*$//')
  [ -n "$hb" ] || return 0
  t=$(iso_to_epoch "$hb") || return 0; [ -n "$t" ] || return 0
  echo $(( $(date -u +%s) - t ))
}

listener_count() {   # <log> -> number of node processes holding the log open (writers)
  lsof -t "$1" 2>/dev/null | while read -r p; do ps -o comm= -p "$p" 2>/dev/null; done | grep -c 'node$'
}

service_variant() {   # which service.<variant>.sh applies here (override: APPS_SERVICE)
  [ -n "${APPS_SERVICE:-}" ] && { echo "$APPS_SERVICE"; return; }
  case "$(uname -s)" in Darwin) echo mac-launchd;; Linux) echo linux-systemd;; *) echo none;; esac
}
