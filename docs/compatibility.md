# Compatibility

Every platform-, terminal- or vendor-specific piece, named as a variant (`<name>.<variant>.<ext>`, or a
labelled section in a doc). Add a row whenever a variant is added. ✅ works · ❌ not available · ⬜ untested / not written.

| Feature | File | mac | linux |
|---|---|---|---|
| Chrome DevTools MCP launch recipe | `docs/reference/browser-testing.md` § Launch recipe (variant: mac) | ✅ | ⬜ |
| Apps: write end as a service (launchd LaunchAgent; stages code + credentials outside TCC-protected ~/Documents) | `apps/bin/service.mac-launchd.sh` | ⬜ (written, not run) | ❌ |
| Apps: write end as a service (systemd user unit) — slot, exits with a message | `apps/bin/service.linux-systemd.sh` | ❌ | ⬜ |
| Apps: file size/mtime + ISO date parsing (`stat -f`/`date -j` vs `stat -c`/`date -d`) | `apps/bin/lib.sh` (`file_size`, `file_mtime`, `iso_to_epoch`) | ✅ | ⬜ |
| Apps: Slack channel adapter (Socket Mode; vendor variant of the channel contract) | `apps/channels/slack/` | ⬜ (code proven in legacy fleet; contract rename not yet run live) | ⬜ |
| Apps: process checks (`lsof`, `pgrep -f` ERE, `ps -o comm=`) | `apps/bin/lib.sh`, `app`, `listener-guard.sh` | ✅ | ⬜ |
| meeting-proxy (whole kit: BlackHole, sox `coreaudio`, SwitchAudioSource) | `kits/meeting-proxy/` | ✅ | ❌ |
| meeting-proxy launcher + audio restore | `kits/meeting-proxy/bin/meeting-run.mac.sh`, `bin/restore-audio.mac.sh` | ✅ | ❌ |
| meeting-proxy one-click app bundle | `kits/meeting-proxy/MeetingProxy.app` | ✅ | ❌ |
| figma-to-pptx OCR helper (Vision); elsewhere `--no-ocr` or own `--ocr-cmd` | `kits/deck-tools/ocr.mac.swift` | ✅ | ❌ |
| figma-to-pptx without OCR | `kits/deck-tools/figma-to-pptx.py --no-ocr` | ✅ | ⬜ |
| page-chat-kit, mcp-scaffold, contrast-check, render_deck (pure Node/Python) | `kits/{page-chat-kit,mcp-scaffold,contrast-check}/`, `kits/deck-tools/render_deck.py` | ✅ | ⬜ |
| slack-app-provision (Chrome over CDP; launch command differs) | `kits/slack-app-provision/` | ✅ | ⬜ |
| Session rollover: new terminal window (dispatcher) | `tools/rollover/launch.sh` → `launch.<variant>.sh` by `$WORKSPACE_TERMINAL` / `$TERM_PROGRAM`; fails clearly when no variant | ✅ | ✅ (dispatcher; no Linux variant yet) |
| Rollover launcher: iTerm2 | `tools/rollover/launch.mac-iterm.sh` (osascript) | ⬜ (syntax-checked; not run, it opens a window) | ❌ |
| Rollover launcher: Terminal.app | `tools/rollover/launch.mac-terminal.sh` (osascript) | ⬜ | ❌ |
| Rollover launcher: tmux / Linux terminals | slot: `tools/rollover/launch.tmux.sh` (not written; `$TMUX` already detected) | ⬜ | ⬜ |
| File size | `tools/rollover/lib.sh` `file_size` (GNU `stat -c` first, BSD `stat -f`) | ✅ | ✅ |
| Interactive-session check | `tools/rollover/lib.sh` `has_tty` (no tty = `??` on mac, `?` on Linux) | ✅ | ✅ |
| New-session detection | `tools/rollover/handoff.sh` waits for `<pre-generated --session-id>.jsonl` (replaces BSD-only `find -newerBm`) | ✅ | ✅ |
| Claude Code internals (transcript dir encoding, custom-title, CLI flags) | `tools/lib/cc-internals.sh` (one place to fix after an upgrade) | ✅ | ✅ |
| Work items + SessionStart restore | `tools/work/work` (bash 3.2+ / python3; no `sed -i`) | ✅ | ✅ |
| Transcript dir symlink | `tools/sessions/setup-transcript-link.sh` | ✅ (fixture only) | ⬜ |
| Leak guard | `tools/guard/{pre-commit,path-lint.sh,route-check.sh,install.sh}` | ✅ | ✅ |
