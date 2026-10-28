#!/bin/bash
# Stop hook of a persona session (persona-session.sh): a persona app is present in the chat by
# waiting on it, so ending the turn is blocked and the session is sent back to wait_event.
# To let it stop: touch <runtime>/session/stop (or interrupt it in its terminal).
# usage: persona-stop-hook.sh <runtime-dir>   (hook JSON on stdin, ignored)
cat >/dev/null
[ -f "${1:?runtime dir}/session/stop" ] && exit 0
printf '%s\n' '{"decision":"block","reason":"Stay present: call wait_event again (memory notes first if something is worth keeping)."}'
