#!/usr/bin/env bash
# Installs a launchd agent that checks Workday every 20 minutes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NODE="$(command -v node)"
LABEL=com.brown.passive-jobs
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/data"
sed -e "s#__NODE__#$NODE#g" -e "s#__ROOT__#$ROOT#g" "$ROOT/launchd/$LABEL.plist.template" > "$PLIST"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Installed $PLIST (runs every 20 min, log: $ROOT/data/run.log)"
