#!/usr/bin/env bash
# Install Chrome/Brave/Chromium native host + point you at the extension folder.
set -euo pipefail

DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
HOST_NAME="com.readaloud.speak"
HOST_PY="$DIR/native-host/read-aloud-host.py"
EXT_ID="$(tr -d '[:space:]' < "$DIR/browser-extension/extension-id.txt")"
EXT_DIR="$DIR/browser-extension"

chmod +x "$HOST_PY"

make_host_manifest() {
  local allowed_json="$1"
  cat <<EOF
{
  "name": "$HOST_NAME",
  "description": "Read Aloud text-to-speech host",
  "path": "$HOST_PY",
  "type": "stdio",
  "allowed_origins": $allowed_json
}
EOF
}

install_chrome_family() {
  local config_dir="$1"
  local label="$2"
  local nm_dir="$config_dir/NativeMessagingHosts"
  mkdir -p "$nm_dir"
  make_host_manifest "[\"chrome-extension://${EXT_ID}/\"]" > "$nm_dir/$HOST_NAME.json"
  echo "Installed native host for $label → $nm_dir/$HOST_NAME.json"
}

# Chrome / Chromium / Brave (same extension ID via manifest key)
[[ -d "$HOME/.config/google-chrome" ]] && install_chrome_family "$HOME/.config/google-chrome" "Google Chrome"
[[ -d "$HOME/.config/chromium" ]] && install_chrome_family "$HOME/.config/chromium" "Chromium"
[[ -d "$HOME/.config/BraveSoftware/Brave-Browser" ]] && install_chrome_family "$HOME/.config/BraveSoftware/Brave-Browser" "Brave"

echo
echo "============================================"
echo "  Enable the browser extension (one time)"
echo "============================================"
echo
echo "1. Open Chrome (or Brave) →  chrome://extensions"
echo "2. Turn ON  Developer mode  (top right)"
echo "3. Click  Load unpacked"
echo "4. Choose this folder:"
echo
echo "   $EXT_DIR"
echo
echo "5. Restart the browser, then:"
echo "   Highlight text → right-click → Read Aloud"
echo
echo "Extension ID should be: $EXT_ID"
echo
# Keep TTS warm for fast first words
pkill -f 'speak-daemon.py' 2>/dev/null || true
sleep 0.2
nohup "$DIR/venv/bin/python" "$DIR/native-host/speak-daemon.py" >/dev/null 2>&1 &
mkdir -p "$HOME/.config/autostart"
cp "$HOME/.config/autostart/read-aloud-speak-daemon.desktop" "$HOME/.config/autostart/read-aloud-speak-daemon.desktop" 2>/dev/null || true
echo "Speak daemon started (stays warm for faster speech)."
echo
