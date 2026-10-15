#!/bin/bash
# Restore audio defaults saved by meeting-run.mac.sh. Safe to run any time.
set -u
PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
# Device names vary per Mac; override in the environment if yours differ.
BUILTIN_OUT="${MP_BUILTIN_OUTPUT:-MacBook Pro Speakers}"
BUILTIN_IN="${MP_BUILTIN_INPUT:-MacBook Pro Microphone}"
STATE="$PROJECT/tmp/audio-state.prev"
SAS="$(command -v SwitchAudioSource || echo /opt/homebrew/bin/SwitchAudioSource)"

if [ ! -f "$STATE" ]; then
  echo "No saved audio state ($STATE) — nothing to restore."
  exit 0
fi
# shellcheck disable=SC1090
source "$STATE"
# If the saved device is gone (e.g. headphones unplugged since), fall back to
# speakers — otherwise macOS may pick a BlackHole device and everything goes silent.
if "$SAS" -a -t output | grep -qx "$OUTPUT"; then :; else
  echo "Saved output '$OUTPUT' no longer present — falling back to speakers."
  OUTPUT="$BUILTIN_OUT"; SYSTEM="$BUILTIN_OUT"
fi
if "$SAS" -a -t input | grep -qx "$INPUT"; then :; else
  INPUT="$BUILTIN_IN"
fi
# Recency scrub: the launcher made BlackHole a recent default, so macOS would
# pick it as FALLBACK if the restored device is later unplugged (headphones) —
# result: silent system. Touch the built-in devices right before the real
# restore so they sit next in the recency stack, not BlackHole.
if [ "$OUTPUT" != "$BUILTIN_OUT" ]; then
  "$SAS" -t output -s "$BUILTIN_OUT" >/dev/null 2>&1
fi
if [ "$INPUT" != "$BUILTIN_IN" ]; then
  "$SAS" -t input -s "$BUILTIN_IN" >/dev/null 2>&1
fi
"$SAS" -t output -s "$OUTPUT" >/dev/null 2>&1 && echo "Restored output -> $OUTPUT"
"$SAS" -t input  -s "$INPUT"  >/dev/null 2>&1 && echo "Restored input  -> $INPUT"
"$SAS" -t system -s "${SYSTEM:-$OUTPUT}" >/dev/null 2>&1
rm -f "$STATE"
echo "Audio config restored."
