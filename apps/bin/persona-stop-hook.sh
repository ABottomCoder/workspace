#!/bin/bash
# Stop hook of a persona session (persona-session.sh). Ending a turn is fine while a wait_event is
# pending (Claude Code runs the long call in the background and wakes the session when it returns:
# app-mcp.mjs writes <runtime>/session/waiting with its pid meanwhile). With no wait pending the
# session would go deaf, so the stop is blocked and it is sent back to wait_event.
# Also lets it stop when <runtime>/session/stop exists.
# usage: persona-stop-hook.sh <runtime-dir>   (hook JSON on stdin, ignored)
cat >/dev/null
S="${1:?runtime dir}/session"
[ -f "$S/stop" ] && exit 0
[ -f "$S/waiting" ] && kill -0 "$(cat "$S/waiting" 2>/dev/null)" 2>/dev/null && exit 0
printf '%s\n' '{"decision":"block","reason":"No wait is pending: call wait_event (memory notes first if something is worth keeping), then end your turn silently."}'
