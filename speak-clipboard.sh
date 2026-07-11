#!/usr/bin/env bash
# Read clipboard aloud (best browser workflow: highlight -> Ctrl+C -> run this / hotkey).
exec "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/speak.sh"
