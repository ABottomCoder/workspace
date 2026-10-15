#!/bin/bash
# Service variant slot: Linux systemd (user unit). Not implemented yet.
# Same interface as service.mac-launchd.sh:
#   service.linux-systemd.sh install|uninstall|installed|sync|start|stop <runtime-dir>
# Intended shape: ~/.config/systemd/user/workspace-app-<co>-<id>.service with
#   ExecStart=/bin/bash <main>/apps/bin/guardian.sh <runtime-dir>, Restart=always,
# managed with `systemctl --user`. No staging needed (no TCC on Linux).
[ "${1:-}" = installed ] && exit 1   # "not installed", so app up/down fall back cleanly
echo "service.linux-systemd.sh: not implemented yet — run the write end in the session instead: app run <id> (run_in_background)" >&2
exit 2
