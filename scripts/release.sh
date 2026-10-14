#!/usr/bin/env bash
# Refresh the engine this plugin ships from the engine repo, then prove it.
# The engine repo stays the source of truth; this copy exists so a fresh install
# with no engine on disk can still run a whole swipe.
#
#   ENGINE=~/Documents/projects/swipe-goat scripts/release.sh
set -euo pipefail
cd "$(dirname "$0")/.."
ENGINE="${ENGINE:-$HOME/Documents/projects/swipe-goat}"
[ -d "$ENGINE/_system" ] || { echo "no engine at $ENGINE/_system (set ENGINE=...)"; exit 2; }
rsync -a --delete --exclude '__pycache__' --exclude '.DS_Store' "$ENGINE/_system/" _system/
for f in .claude-plugin/plugin.json package.json; do grep -o '"version": "[^"]*"' "$f"; done
grep -o 'version: "[^"]*"' site/index.html
npm test
node --check scripts/swipe-capture.mjs
echo "engine synced and tested; versions above must all match before you commit"
