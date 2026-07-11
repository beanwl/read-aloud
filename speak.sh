#!/usr/bin/env bash
# Speak text using Microsoft neural voices (same quality as Edge / good PDF-to-MP3 tools).
set -euo pipefail

DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
EDGE="$DIR/venv/bin/edge-tts"
VOICE="${SPEAK_VOICE:-en-US-AndrewNeural}"   # US male; also: en-US-GuyNeural, en-US-JennyNeural (female)
PLAYER="${SPEAK_PLAYER:-paplay}"
TMP="$(mktemp /tmp/speak-XXXXXX.mp3)"

cleanup() { rm -f "$TMP"; }
trap cleanup EXIT

text="${*:-}"

if [[ -z "$text" ]]; then
  if command -v xclip >/dev/null 2>&1; then
    text="$(xclip -selection clipboard -o 2>/dev/null || true)"
  fi
  if [[ -z "$text" ]] && command -v xclip >/dev/null 2>&1; then
    text="$(xclip -selection primary -o 2>/dev/null || true)"
  fi
fi

text="$(printf '%s' "$text" | tr '\n' ' ' | sed 's/  */ /g; s/^ *//; s/ *$//')"
[[ -n "$text" ]] || { echo "No text. Highlight text, copy it, or run: speak.sh \"hello\""; exit 1; }

"$EDGE" --voice "$VOICE" --text "$text" --write-media "$TMP"
if command -v "$PLAYER" >/dev/null 2>&1; then
  "$PLAYER" "$TMP"
else
  aplay "$TMP" 2>/dev/null || ffplay -nodisp -autoexit "$TMP"
fi
