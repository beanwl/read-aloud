#!/usr/bin/env bash
# One-time: load the Read Aloud extension into Chrome.
set -euo pipefail

EXT_DIR="/home/beanwl/Tools/read-aloud/browser-extension"
EXT_ID="$(tr -d '[:space:]' < "$EXT_DIR/extension-id.txt")"

"/home/beanwl/Tools/read-aloud/install-browser-integration.sh" >/tmp/read-aloud-install.log 2>&1 || true

if command -v xclip >/dev/null 2>&1; then
  printf '%s' "$EXT_DIR" | xclip -selection clipboard
fi

zenity --info --title="Install Read Aloud" --width=520 \
  --text="<b>Chrome needs the Read Aloud extension loaded once.</b>

The folder path is already <b>copied</b> to your clipboard:

$EXT_DIR

Next:
1. Chrome opens to <b>Extensions</b>
2. Turn ON <b>Developer mode</b> (top right)
3. Click <b>Load unpacked</b>
4. Paste the path (Ctrl+L then Ctrl+V) and press Enter

Then highlight text → right-click → <b>Read Aloud</b>" \
  --ok-label="Open Chrome Extensions" || true

google-chrome "chrome://extensions" >/dev/null 2>&1 &
sleep 1
notify-send "Read Aloud" "Developer mode → Load unpacked → paste folder path (already copied)." || true
