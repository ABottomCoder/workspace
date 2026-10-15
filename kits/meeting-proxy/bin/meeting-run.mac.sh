#!/bin/bash
# meeting-proxy one-click runner.
# Saves current audio defaults -> switches to meeting routing -> runs the proxy.
# On ANY exit (Ctrl+C, closing the Terminal window, crash) restores the saved defaults.
#
# Routing it sets up:
#   system OUTPUT -> "BlackHole 16ch"   (Zoom speaker, if Zoom uses "Same as System")
#   system INPUT  -> "BlackHole 2ch"    (AI voice + your real mic, bridged in by sox below)
#   PASSTHROUGH   -> your previous real output device (so YOU still hear the meeting)

set -u
PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
# Device names vary per Mac; override in the environment if yours differ.
BUILTIN_OUT="${MP_BUILTIN_OUTPUT:-MacBook Pro Speakers}"
BUILTIN_IN="${MP_BUILTIN_INPUT:-MacBook Pro Microphone}"
HEADSET_MIC="${MP_HEADSET_MIC:-External Microphone}"
STATE="$PROJECT/tmp/audio-state.prev"
SAS="$(command -v SwitchAudioSource || echo /opt/homebrew/bin/SwitchAudioSource)"

say_fail() { echo ""; echo "✗ $1"; echo ""; read -r -p "Press Enter to close..."; exit 1; }

# ---------- preflight ----------
command -v sox >/dev/null || say_fail "sox not found (brew install sox)"
[ -x "$SAS" ] || say_fail "SwitchAudioSource not found (brew install switchaudio-osx)"
[ -d "$PROJECT/node_modules" ] || say_fail "node_modules missing — run: cd $PROJECT && npm install"

OUT_DEVICES="$("$SAS" -a -t output)"
IN_DEVICES="$("$SAS" -a -t input)"
echo "$OUT_DEVICES" | grep -q "^BlackHole 16ch$" || say_fail "BlackHole 16ch missing (brew install --cask blackhole-16ch, then reboot)"
echo "$OUT_DEVICES" | grep -q "^BlackHole 2ch$"  || say_fail "BlackHole 2ch missing (brew install --cask blackhole-2ch, then reboot)"
# NOTE: the old "Meeting Mic" aggregate is DEPRECATED — Zoom only reads the first
# sub-device stream of an aggregate, so the human-mic channel was never audible
# to Zoom. Zoom mic = BlackHole 2ch directly; your real mic is
# bridged into it below, mixing natively with the AI voice.

# Anchored to the real node process — a bare "tsx src/index.ts" pattern also
# matches any supervising shell whose command line merely CONTAINS that string.
if pgrep -f "^node .*tsx src/index.ts" >/dev/null; then
  say_fail "meeting-proxy is already running (another window?)"
fi

# ---------- pick context ----------
cd "$PROJECT" || exit 1
CTX="${1:-}"
if [ -z "$CTX" ]; then
  # shellcheck disable=SC2012
  N=$(ls context/*.md 2>/dev/null | wc -l | tr -d ' ')
  if [ "$N" = "0" ]; then
    cp context-templates/example.md context/default.md
    echo "No context file found — created context/default.md from the template."
    echo "EDIT IT to reflect this meeting, then run again."
    open -t context/default.md
    read -r -p "Press Enter to close..."
    exit 1
  elif [ "$N" = "1" ]; then
    CTX="$(ls context/*.md)"
  else
    echo "Pick a meeting context:"
    select f in context/*.md; do CTX="$f"; break; done
  fi
fi
[ -f "$CTX" ] || say_fail "context file not found: $CTX"

# ---------- save current defaults ----------
mkdir -p "$PROJECT/tmp"
if [ -f "$STATE" ]; then
  # Previous run died without restoring — its saved state is the REAL previous
  # config; do not overwrite it with the current (meeting) devices.
  echo "Found leftover audio state from a previous run — will restore to that."
else
  {
    echo "OUTPUT=\"$("$SAS" -c -t output)\""
    echo "INPUT=\"$("$SAS" -c -t input)\""
    echo "SYSTEM=\"$("$SAS" -c -t system)\""
  } > "$STATE"
fi
# shellcheck disable=SC1090
source "$STATE"
echo "Saved audio defaults: output='$OUTPUT' input='$INPUT'"

# ---------- restore on ANY exit ----------
BRIDGE_PID=""
restore() {
  trap - EXIT INT TERM HUP
  echo ""
  [ -n "$BRIDGE_PID" ] && kill "$BRIDGE_PID" 2>/dev/null
  "$PROJECT/bin/restore-audio.mac.sh"
  exit 0
}
trap restore EXIT INT TERM HUP

# Monitor device (your real output) is still the default here — if it's muted or
# near-zero you'd sit in the meeting hearing nothing.
VOL="$(osascript -e 'output volume of (get volume settings)' 2>/dev/null || echo 50)"
MUTED="$(osascript -e 'output muted of (get volume settings)' 2>/dev/null || echo false)"
if [ "$MUTED" = "true" ] || [ "${VOL:-50}" -lt 10 ]; then
  echo "⚠ '$OUTPUT' was muted/volume $VOL — raising to 40 so you can hear the meeting."
  osascript -e 'set volume without output muted' -e 'set volume output volume 40'
fi

# ---------- switch to meeting routing ----------
"$SAS" -t output -s "BlackHole 16ch" >/dev/null
# BlackHole's own device volume slider ATTENUATES the loopback (a rolled-down
# slider = -28dB = silent listen path). It's default output
# right now, so force it to 100%.
osascript -e 'set volume without output muted' -e 'set volume output volume 100' 2>/dev/null
"$SAS" -t input  -s "BlackHole 2ch"  >/dev/null
# Keep alert/system sounds OFF the meeting feed:
"$SAS" -t system -s "$OUTPUT" >/dev/null 2>&1

# Mic bridge: pipe your real microphone into BlackHole 2ch, where it mixes with
# the AI voice — Zoom reads BlackHole 2ch as its mic and hears both.
if echo "$IN_DEVICES" | grep -qx "$HEADSET_MIC"; then
  REAL_MIC="$HEADSET_MIC"
else
  REAL_MIC="$BUILTIN_IN"
  echo "⚠ No headset mic detected — bridging the BUILT-IN mic. With speakers as monitor this can echo; plug in a headset for real meetings."
fi
sox -q -t coreaudio "$REAL_MIC" -c 2 -t coreaudio "BlackHole 2ch" &
BRIDGE_PID=$!
echo "Mic bridge ON: '$REAL_MIC' -> BlackHole 2ch (pid $BRIDGE_PID)"

# You hear the meeting via the proxy's passthrough tee -> your previous output.
case "$OUTPUT" in
  "BlackHole"*|"Meeting Output") PASSTHROUGH_DEVICE="$BUILTIN_OUT" ;;
  *)                             PASSTHROUGH_DEVICE="$OUTPUT" ;;
esac
export PASSTHROUGH_DEVICE   # wins over .env (dotenv never overrides existing env)
echo "Meeting routing ON: output->BlackHole 16ch, mic->BlackHole 2ch, you hear via '$PASSTHROUGH_DEVICE'"
if [ "$PASSTHROUGH_DEVICE" = "$BUILTIN_OUT" ]; then
  echo "⚠ Using SPEAKERS for monitoring — plug in wired headphones to avoid echo into the headset mic."
fi

echo ""
echo "=== In Zoom: Settings > Audio > Speaker AND Microphone = 'Same as System' ==="
echo "=== Stop: Ctrl+C or just close this window (audio config auto-restores)   ==="
echo ""

npm start -- --context "$CTX"
# fallthrough (normal exit) hits the EXIT trap -> restore
