#!/usr/bin/env bash
# Read some or all of a PDF aloud using Andrew (edge-tts).
# Usage:
#   speak-pdf file.pdf              # whole PDF
#   speak-pdf file.pdf 5            # page 5 only
#   speak-pdf file.pdf 3 7          # pages 3-7
set -euo pipefail

DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
SPEAK="$DIR/speak.sh"

pdf="${1:-}"
[[ -n "$pdf" && -f "$pdf" ]] || { echo "Usage: speak-pdf file.pdf [page] [end-page]"; exit 1; }

if ! command -v pdftotext >/dev/null 2>&1; then
  echo "Install poppler: sudo apt install poppler-utils"
  exit 1
fi

start_page="${2:-}"
end_page="${3:-$start_page}"

TMP="$(mktemp /tmp/pdf-speak-XXXXXX.txt)"
cleanup() { rm -f "$TMP"; }
trap cleanup EXIT

if [[ -n "$start_page" ]]; then
  [[ -n "$end_page" ]] || end_page="$start_page"
  pdftotext -f "$start_page" -l "$end_page" "$pdf" "$TMP"
  echo "Reading pages $start_page-$end_page of $(basename "$pdf")..."
else
  pdftotext "$pdf" "$TMP"
  echo "Reading $(basename "$pdf")..."
fi

text="$(tr '\n' ' ' < "$TMP" | sed 's/  */ /g; s/^ *//; s/ *$//')"
[[ -n "$text" ]] || { echo "No text found (maybe scanned/image PDF)."; exit 1; }

# Speak in ~4000-char chunks (edge-tts limit is generous but keeps responses snappy)
chunk=4000
len=${#text}
if (( len <= chunk )); then
  exec "$SPEAK" "$text"
fi

pos=0
part=1
while (( pos < len )); do
  slice="${text:pos:chunk}"
  # try to break at sentence end
  if (( pos + chunk < len )); then
    better="${slice%.*}."
    if [[ ${#better} -gt 200 ]]; then
      slice="$better"
    fi
  fi
  echo "Part $part..."
  "$SPEAK" "$slice"
  pos=$((pos + ${#slice}))
  part=$((part + 1))
done
