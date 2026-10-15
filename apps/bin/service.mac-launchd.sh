#!/bin/bash
# Service variant: macOS launchd. Runs an app's write end (guardian.sh) as a LaunchAgent so it
# survives session exits, sleep and reboots. Only touched when the user runs
# `app install-service <id>`; `app up/down` call start/stop if it is installed.
#
#   service.mac-launchd.sh install|uninstall|installed|sync|start|stop <runtime-dir>
#
# macOS privacy protection (TCC) blocks launchd jobs from reading ~/Documents, ~/Desktop and
# ~/Downloads ("Operation not permitted"), and the main dir usually lives there. So `install`/`sync`
# stage what the write end needs (apps code + node_modules, the generated .env, a copy of the
# credentials, mode 600) into a non-protected dir and point <runtime>/listener.log at the staged
# log with a symlink; readers in the session are unaffected. Re-run `sync` (done by `app up`) after
# changing apps code or credentials.
#   stage: ${APPS_SERVICE_HOME:-~/.local/share/workspace-apps}/<co>/<id>/{code,run}
set -u
. "$(cd "$(dirname "$0")" && pwd)/lib.sh"
VERB=${1:-}; RUN=${2:-}
[ -n "$VERB" ] && [ -f "$RUN/.env" ] || die "usage: service.mac-launchd.sh install|uninstall|installed|sync|start|stop <runtime-dir>"
HOME_DIR=$(cd "$RUN/.." && pwd); ID=$(basename "$HOME_DIR"); CO=$(basename "$(dirname "$(dirname "$HOME_DIR")")")
LABEL="workspace.app.$CO.$ID"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
STAGE="${APPS_SERVICE_HOME:-$HOME/.local/share/workspace-apps}/$CO/$ID"
DOMAIN="gui/$(id -u)"

sync_stage() {
  mkdir -p "$STAGE/code" "$STAGE/run"; chmod 700 "$STAGE/run"
  rsync -a --delete "$APPS_ROOT/bin" "$APPS_ROOT/channels" "$APPS_ROOT/package.json" "$STAGE/code/"
  [ -d "$APPS_ROOT/node_modules" ] || die "run npm install in $APPS_ROOT first"
  rsync -a --delete "$APPS_ROOT/node_modules" "$STAGE/code/"
  local sec; sec=$(sed -n 's/^APP_SECRETS=//p' "$RUN/.env")
  ( umask 077; cp "$sec" "$STAGE/run/secrets.env"
    sed "s|^APP_SECRETS=.*|APP_SECRETS=$STAGE/run/secrets.env|" "$RUN/.env" > "$STAGE/run/.env" )
  # Session-side readers keep using <runtime>/listener.log.
  if [ ! -L "$RUN/listener.log" ]; then
    [ -f "$RUN/listener.log" ] && cat "$RUN/listener.log" >> "$STAGE/run/listener.log"
    rm -f "$RUN/listener.log"; touch "$STAGE/run/listener.log"; ln -s "$STAGE/run/listener.log" "$RUN/listener.log"
  fi
}

write_plist() {
  local node_dir; ensure_node; node_dir=$(dirname "$(command -v node)")
  mkdir -p "$(dirname "$PLIST")"
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$STAGE/code/bin/guardian.sh</string><string>$STAGE/run</string></array>
  <key>WorkingDirectory</key><string>$STAGE/run</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>10</integer>
  <key>EnvironmentVariables</key><dict>
    <key>HOME</key><string>$HOME</string>
    <key>PATH</key><string>$node_dir:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>StandardOutPath</key><string>$STAGE/run/launchd.out.log</string>
  <key>StandardErrorPath</key><string>$STAGE/run/launchd.err.log</string>
</dict></plist>
EOF
}

loaded() { launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; }

case "$VERB" in
  installed) [ -f "$PLIST" ] ;;
  sync) sync_stage ;;
  install) sync_stage; write_plist; loaded && launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null
           launchctl bootstrap "$DOMAIN" "$PLIST" && echo "installed $LABEL ($PLIST); stage $STAGE" ;;
  start) if loaded; then launchctl kickstart -k "$DOMAIN/$LABEL"; else launchctl bootstrap "$DOMAIN" "$PLIST"; fi ;;
  stop) loaded && launchctl bootout "$DOMAIN/$LABEL"; true ;;
  uninstall) loaded && launchctl bootout "$DOMAIN/$LABEL"; rm -f "$PLIST"
             if [ -L "$RUN/listener.log" ]; then rm -f "$RUN/listener.log"; cp "$STAGE/run/listener.log" "$RUN/listener.log" 2>/dev/null; fi
             rm -rf "$STAGE"; echo "uninstalled $LABEL" ;;
  *) die "unknown verb '$VERB'" ;;
esac
