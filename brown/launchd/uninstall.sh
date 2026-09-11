#!/usr/bin/env bash
set -euo pipefail
LABEL=com.brown.passive-jobs
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
echo "Removed $LABEL"
