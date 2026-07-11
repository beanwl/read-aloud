#!/usr/bin/env bash
# Build a Chrome Web Store / Edge Add-ons zip from browser-extension-store/
set -euo pipefail

DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
SRC="$DIR/browser-extension-store"
OUT_DIR="$DIR/store/dist"
VERSION="$(python3 -c "import json; print(json.load(open('$SRC/manifest.json'))['version'])")"
ZIP="$OUT_DIR/read-aloud-store-v${VERSION}.zip"

mkdir -p "$OUT_DIR"
rm -f "$ZIP"

# Zip contents at archive root (required by stores — not a nested folder).
(
  cd "$SRC"
  zip -r -q "$ZIP" . \
    -x '*.pem' \
    -x '*~' \
    -x '*.map' \
    -x '.*'
)

echo "Created: $ZIP"
echo "Size:    $(du -h "$ZIP" | cut -f1)"
echo
echo "Upload this zip to:"
echo "  Chrome: https://chrome.google.com/webstore/devconsole"
echo "  Edge:   https://partner.microsoft.com/dashboard/microsoftedge"
