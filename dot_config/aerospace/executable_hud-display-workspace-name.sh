#!/usr/bin/env bash
# HUD notification for Aerospace workspace switches.
# Called from ~/.aerospace.toml keybindings, e.g.:
#   alt-n = ['workspace N', 'exec-and-forget ~/.config/aerospace/hud-display-workspace-name.sh N']
#
# Resolves the workspace ID to a friendly name (from workspaces.yaml) and displays it
# as a brief on-screen alert. Uses Hammerspoon if available, otherwise falls back to
# macOS notification center via osascript.
set -euo pipefail

ID="${1:-}"
[[ -z "$ID" ]] && ID=$(aerospace list-workspaces --focused 2>/dev/null || true)
[[ -z "$ID" ]] && exit 0

PREFIX="${2:-}"

# Resolve friendly name from workspaces.yaml (if present).
YAML="$HOME/.config/aerospace/workspaces.yaml"
if [[ -f "$YAML" ]] && command -v yq &>/dev/null; then
    NAME=$(yq ".workspaces.\"$ID\" // \"$ID\"" "$YAML")
else
    NAME="$ID"
fi

DISPLAY="${PREFIX}${NAME}"

# Try Hammerspoon (brief centered HUD), fall back to osascript notification.
if pgrep -xq Hammerspoon; then
    open -g "hammerspoon://workspace?name=${DISPLAY}"
else
    osascript -e "display notification \"${DISPLAY}\" with title \"Workspace\"" &>/dev/null || true
fi
