#!/usr/bin/env bash
# Speak whatever text you just highlighted (mouse selection / primary buffer).
set -euo pipefail

if ! command -v xclip >/dev/null 2>&1; then
  echo "Install xclip first: sudo apt install xclip"
  exit 1
fi

text="$(xclip -selection primary -o 2>/dev/null || true)"
if [[ -z "$text" ]]; then
  echo "Highlight some text first, then run this again."
  exit 1
fi

exec "$(dirname "$0")/speak.sh" "$text"
