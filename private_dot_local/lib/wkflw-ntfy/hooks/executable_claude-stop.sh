#!/usr/bin/env bash
# Claude Code Stop hook: Notify when Claude finishes a task
#
# Receives JSON via stdin with fields:
# - hook_event_name: "Stop"
# - cwd: Current working directory
# - transcript_path: Path to transcript file

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

# shellcheck disable=SC1091
source "$SCRIPT_DIR/../core/wkflw-ntfy-config"

# Generate session ID for this notification event
SESSION_ID=$("$SCRIPT_DIR/../core/wkflw-ntfy-session-id")

# Read hook JSON from stdin
hook_data=$(cat)

if ! command -v jq &>/dev/null; then
    "$SCRIPT_DIR/../core/wkflw-ntfy-log" "$SESSION_ID" error "claude-stop" "jq not found, cannot parse hook data"
    exit 1
fi

# Extract fields
cwd=$(echo "$hook_data" | jq -r '.cwd // "unknown"')
dir_name=$(basename "$cwd")

# Notification content
title="Claude Code - Finished"
body="$dir_name: Task completed"

# Detect environment and choose strategy
env=$("$SCRIPT_DIR/../core/wkflw-ntfy-detect-env" "$SESSION_ID")
strategy=$("$SCRIPT_DIR/../core/wkflw-ntfy-decide-strategy" "$SESSION_ID" "$env" "claude-stop" "")

"$SCRIPT_DIR/../core/wkflw-ntfy-log" "$SESSION_ID" debug "claude-stop" "Environment: $env, Strategy: $strategy"
"$SCRIPT_DIR/../core/wkflw-ntfy-log" "$SESSION_ID" debug "claude-stop" "Notification: title='$title', body='$body', cwd='$cwd', dir_name='$dir_name'"

case "$strategy" in
    progressive)
        # Create marker for progressive escalation
        "$SCRIPT_DIR/../marker/wkflw-ntfy-marker-create" "$SESSION_ID" "claude-stop" "$cwd" >/dev/null

        # Get window ID (if iTerm) - must be captured in hook context before process exits
        window_id=""
        if [[ "$env" == "iterm" ]]; then
            window_id=$("$SCRIPT_DIR/../macos/wkflw-ntfy-macos-get-window" "$SESSION_ID" || echo "")
        fi

        # Send desktop notification with window_id for callback
        "$SCRIPT_DIR/../macos/wkflw-ntfy-macos-send" "$SESSION_ID" "$title" "$body" "$window_id"

        # Spawn escalation worker
        "$SCRIPT_DIR/../escalation/wkflw-ntfy-escalate-spawn" "$SESSION_ID" "$title" "$body"
        ;;

    desktop-only)
        # Send desktop notification (no escalation)
        if [[ "$env" == "linux-gui" ]]; then
            "$SCRIPT_DIR/../linux/wkflw-ntfy-linux-send" "$SESSION_ID" "$title" "$body"
        else
            "$SCRIPT_DIR/../macos/wkflw-ntfy-macos-send" "$SESSION_ID" "$title" "$body"
        fi
        ;;

    push-only)
        # Send push notification
        "$SCRIPT_DIR/../push/wkflw-ntfy-push" "$SESSION_ID" "$title" "$body"
        ;;

    *)
        "$SCRIPT_DIR/../core/wkflw-ntfy-log" "$SESSION_ID" error "claude-stop" "Unknown strategy: $strategy"
        exit 1
        ;;
esac
