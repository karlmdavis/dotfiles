#!/usr/bin/env bash
# Claude Code Notification hook: Notify when Claude needs attention
#
# Receives JSON via stdin with fields:
# - hook_event_name: "Notification"
# - notification_type: "permission_prompt" or "idle_input"
# - message: Notification message
# - cwd: Current working directory

set -euo pipefail

# Load config and logging
# Resolve symlinks to find actual script location
SCRIPT_PATH="${BASH_SOURCE[0]}"
while [ -L "$SCRIPT_PATH" ]; do
    SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
    SCRIPT_PATH="$(readlink "$SCRIPT_PATH")"
    [[ "$SCRIPT_PATH" != /* ]] && SCRIPT_PATH="$SCRIPT_DIR/$SCRIPT_PATH"
done
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"

# shellcheck disable=SC1091  # Config path is dynamic (resolved from symlink)
source "$SCRIPT_DIR/../core/wkflw-ntfy-config"

# Generate session ID for this notification event
SESSION_ID=$("$SCRIPT_DIR/../core/wkflw-ntfy-session-id")

# Read hook JSON from stdin
hook_data=$(cat)

if ! command -v jq &>/dev/null; then
    "$SCRIPT_DIR/../core/wkflw-ntfy-log" "$SESSION_ID" error "claude-notification" "jq not found, cannot parse hook data"
    exit 1
fi

# Extract fields
notification_type=$(echo "$hook_data" | jq -r '.notification_type // "unknown"')
message=$(echo "$hook_data" | jq -r '.message // "Claude needs attention"')
cwd=$(echo "$hook_data" | jq -r '.cwd // "unknown"')
dir_name=$(basename "$cwd")

# Notification content based on type
case "$notification_type" in
    permission_prompt)
        title="Claude Code - Permission Needed"
        body="$message"
        ;;
    idle_input|*)
        title="Claude Code - Input Needed"
        body="$dir_name: $message"
        ;;
esac

# Detect environment and choose strategy
env=$("$SCRIPT_DIR/../core/wkflw-ntfy-detect-env" "$SESSION_ID")
strategy=$("$SCRIPT_DIR/../core/wkflw-ntfy-decide-strategy" "$SESSION_ID" "$env" "claude-notification" "$notification_type")

"$SCRIPT_DIR/../core/wkflw-ntfy-log" "$SESSION_ID" debug "claude-notification" "Type: $notification_type, Environment: $env, Strategy: $strategy"
"$SCRIPT_DIR/../core/wkflw-ntfy-log" "$SESSION_ID" debug "claude-notification" "Notification: title='$title', body='$body'"

# Capture window ID in hook context (if iTerm) - must be done before dispatch
window_id=""
if [[ "$env" == "iterm" ]]; then
    window_id=$("$SCRIPT_DIR/../macos/wkflw-ntfy-macos-get-window" "$SESSION_ID" || echo "")
fi

# Dispatch to shared strategy handler
"$SCRIPT_DIR/../core/wkflw-ntfy-dispatch" "$SESSION_ID" "claude-notification" "$env" "$strategy" "$title" "$body" "$cwd" "$window_id"
