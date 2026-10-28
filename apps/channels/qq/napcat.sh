#!/bin/bash
# The QQ login endpoint (NapCat in Docker) for one qq app. Not a contract verb: QQ needs a logged-in
# client next to the adapter, and this starts, checks and stops it. Nothing auto-starts.
#
#   napcat.sh find <qq account>      print the app (<co>/<id>) whose app.yaml has qq_account: <account>
#   napcat.sh up <app|qq account>    create/start the container, write the OneBot config from the
#                                    credentials file, wait until logged in (QR: saved to
#                                    <runtime>/qrcode.png and opened; scan it with the phone)
#   napcat.sh status <app|account>   container state + login check
#   napcat.sh down <app|account>     stop the container (the login is kept for next time)
#
# Container: napcat-<name>; login data: <app dir>/napcat/{qq,config}; ports from the credentials file
# (ONEBOT_HTTP / ONEBOT_WS), bound to 127.0.0.1. Each docker call has a timeout: a wedged Docker
# daemon hangs every call for ever.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/../../bin/lib.sh"
IMAGE=${NAPCAT_IMAGE:-mlikiowa/napcat-docker:latest}
dk() { perl -e 'alarm shift; exec @ARGV' "${DK_TIMEOUT:-60}" docker "$@"; }

find_app() {   # <qq account> -> co/id
  local f; for f in "$BUSINESS"/*/apps/qq_*/app.yaml; do
    [ -f "$f" ] && [ "$(field "$f" qq_account)" = "$1" ] && { echo "$(basename "$(dirname "$(dirname "$(dirname "$f")")")")/$(basename "$(dirname "$f")")"; return 0; }
  done; return 1
}
load() {
  local ref=$1
  [[ "$ref" =~ ^[0-9]{5,}$ ]] && { ref=$(find_app "$ref") || die "no qq app with qq_account: $1 (set it in business/<co>/apps/qq_<name>/app.yaml)"; }
  resolve_app "$ref"; [ "$APP_CHANNEL" = qq ] || die "$APP_ID is not a qq app"
  ACCOUNT=$(field "$APP_CONF" qq_account); [ -n "$ACCOUNT" ] || die "set qq_account: in $APP_CONF"
  SEC="$BUSINESS/$APP_CO/.secrets/apps/$APP_ID.env"; [ -f "$SEC" ] || die "no credentials: $SEC (format: $HERE/secrets.env.example)"
  NAME="napcat-$APP_NAME"; ND="$APP_HOME/napcat"
}
port() { sed -n "s/^$1=.*:\([0-9][0-9]*\).*/\1/p" "$SEC" | head -1; }
logged_in() {   # validate-creds against the endpoint, without needing `app up` first
  local vc; vc=$(channel_cmd qq validate-creds) || return 1; ensure_node
  (cd "$APP_HOME" && APP_ENV=/dev/null APP_SECRETS="$SEC" APP_LISTEN_CONVS="$(field "$APP_CONF" listen_convs)" $vc 2>&1)
}

write_config() {   # OneBot HTTP + forward WS servers, token from the credentials file (never printed)
  mkdir -p "$ND/qq" "$ND/config"; chmod 700 "$ND"
  python3 - "$SEC" "$ND/config/onebot11_$ACCOUNT.json" <<'EOF'
import json, os, sys
tok = next(l.split("=", 1)[1].split("#")[0].strip() for l in open(sys.argv[1]) if l.startswith("ONEBOT_TOKEN="))
srv = dict(enable=True, host="0.0.0.0", messagePostFormat="array", token=tok, debug=False)
cfg = {"network": {"httpServers": [dict(srv, name="http", port=3000, enableCors=False, enableWebsocket=False)],
                   "httpSseServers": [], "httpClients": [], "websocketClients": [], "plugins": [],
                   "websocketServers": [dict(srv, name="ws", port=3001, reportSelfMessage=True,
                                             enableForcePushEvent=True, heartInterval=30000)]},
       "musicSignUrl": "", "enableLocalFile2Url": False, "parseMultMsg": False}
fd = os.open(sys.argv[2], os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
os.write(fd, json.dumps(cfg, indent=2).encode()); os.close(fd)
EOF
}

cmd_up() {
  load "$1"
  dk version --format '{{.Server.Version}}' >/dev/null 2>&1 || die "Docker is not answering (start or restart Docker Desktop)"
  write_config
  if dk inspect "$NAME" >/dev/null 2>&1; then
    dk start "$NAME" >/dev/null || die "docker start $NAME failed"
  else
    local hp wp; hp=$(port ONEBOT_HTTP); wp=$(port ONEBOT_WS); [ -n "$hp" ] && [ -n "$wp" ] || die "ONEBOT_HTTP / ONEBOT_WS ports missing in $SEC"
    dk pull "$IMAGE" >/dev/null 2>&1 || true
    DK_TIMEOUT=120 dk run -d --name "$NAME" --restart no -e NAPCAT_UID="$(id -u)" -e NAPCAT_GID="$(id -g)" -e ACCOUNT="$ACCOUNT" \
      -p "127.0.0.1:$hp:3000" -p "127.0.0.1:$wp:3001" -v "$ND/qq:/app/.config/QQ" -v "$ND/config:/app/napcat/config" "$IMAGE" >/dev/null \
      || die "docker run failed"
  fi
  echo "napcat: $NAME started for $ACCOUNT ($APP_REF); waiting for login…"
  local i qr_shown=0 out
  for i in $(seq 1 90); do   # ~3 min: quick login takes seconds, a QR scan longer
    sleep 2
    out=$(logged_in) && { echo "logged in: $out"; return 0; }
    if [ $qr_shown = 0 ] && dk logs --since 2m "$NAME" 2>&1 | grep -q '二维码已保存'; then
      dk cp "$NAME:/app/napcat/cache/qrcode.png" "$APP_RUN/qrcode.png" >/dev/null 2>&1 && chmod 600 "$APP_RUN/qrcode.png"
      echo "QR login needed: scan $APP_RUN/qrcode.png with the phone QQ of $ACCOUNT, then confirm on the phone"
      command -v open >/dev/null && open "$APP_RUN/qrcode.png"; qr_shown=1
    fi
  done
  die "not logged in after 3 min (QR expired? run napcat.sh up again; account frozen? check the phone). Last: $out"
}
cmd_status() { load "$1"; echo "container: $(dk inspect -f '{{.State.Status}}' "$NAME" 2>/dev/null || echo missing)"; echo "login: $(logged_in || true)"; }
cmd_down() { load "$1"; dk stop "$NAME" >/dev/null 2>&1 && echo "napcat: $NAME stopped" || echo "napcat: $NAME was not running"; }

case "${1:-}" in
  find) find_app "${2:?qq account}" || die "no qq app with qq_account: $2" ;;
  up|status|down) c=$1; shift; "cmd_$c" "${1:?app or qq account}" ;;
  *) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
