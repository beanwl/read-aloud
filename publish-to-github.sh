#!/usr/bin/env bash
# Create GitHub repo and push Read Aloud (run after: gh auth login)
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"
REPO_DIR="$HOME/Tools/read-aloud"
REPO_NAME="read-aloud"

cd "$REPO_DIR"

if ! gh auth status >/dev/null 2>&1; then
  echo "Not logged into GitHub. Run:"
  echo "  gh auth login"
  exit 1
fi

# Use main branch (GitHub default)
git branch -M main 2>/dev/null || git checkout -b main

if git remote get-url origin >/dev/null 2>&1; then
  echo "Remote origin already set."
else
  gh repo create "$REPO_NAME" \
    --public \
    --source=. \
    --remote=origin \
    --description "Read Aloud TTS with Chrome extension and Linux speak daemon" \
    --push
  echo
  echo "Done:"
  gh repo view --web=false --json url -q .url
  exit 0
fi

git push -u origin main
echo
echo "Done:"
gh repo view --web=false --json url -q .url
