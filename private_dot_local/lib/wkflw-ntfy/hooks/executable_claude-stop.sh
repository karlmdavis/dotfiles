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

# Read hook JSON from stdin
hook_data=$(cat)

if ! command -v jq &>/dev/null; then
    "$SCRIPT_DIR/../core/wkflw-ntfy-log" error "claude-stop" "jq not found, cannot parse hook data"
    exit 1
fi

# Extract fields
cwd=$(echo "$hook_data" | jq -r '.cwd // "unknown"')
dir_name=$(basename "$cwd")

# Notification content
title="Claude Code - Finished"
body="$dir_name: Task completed"

# Detect environment and choose strategy
env=$("$SCRIPT_DIR/../core/wkflw-ntfy-detect-env")
strategy=$("$SCRIPT_DIR/../core/wkflw-ntfy-decide-strategy" "$env" "claude-stop" "")

"$SCRIPT_DIR/../core/wkflw-ntfy-log" debug "claude-stop" "Environment: $env, Strategy: $strategy"
"$SCRIPT_DIR/../core/wkflw-ntfy-log" debug "claude-stop" "Notification: title='$title', body='$body', cwd='$cwd', dir_name='$dir_name'"

case "$strategy" in
    progressive)
        # Create marker for progressive escalation
        marker=$("$SCRIPT_DIR/../marker/wkflw-ntfy-marker-create" "claude-stop" "$cwd")

        # Get window ID (if iTerm)
        window_id=""
        if [[ "$env" == "iterm" ]]; then
            window_id=$("$SCRIPT_DIR/../macos/wkflw-ntfy-macos-get-window" || echo "")
        fi

        # Create callback script
        callback_script="$WKFLW_NTFY_STATE_DIR/callback-$$"
        cat > "$callback_script" <<EOF
#!/usr/bin/env bash
"$SCRIPT_DIR/../macos/wkflw-ntfy-macos-callback" "$marker" "$window_id"
rm -f "$callback_script"
EOF
        chmod +x "$callback_script"

        # Send desktop notification with callback
        "$SCRIPT_DIR/../macos/wkflw-ntfy-macos-send" "$title" "$body" "$callback_script"

        # Spawn escalation worker with callback script path
        "$SCRIPT_DIR/../escalation/wkflw-ntfy-escalate-spawn" "$marker" "$title" "$body" "$callback_script"
        ;;

    desktop-only)
        # Send desktop notification (no escalation)
        if [[ "$env" == "linux-gui" ]]; then
            "$SCRIPT_DIR/../linux/wkflw-ntfy-linux-send" "$title" "$body"
        else
            "$SCRIPT_DIR/../macos/wkflw-ntfy-macos-send" "$title" "$body"
        fi
        ;;

    push-only)
        # Send push notification
        "$SCRIPT_DIR/../push/wkflw-ntfy-push" "$title" "$body"
        ;;

    *)
        "$SCRIPT_DIR/../core/wkflw-ntfy-log" error "claude-stop" "Unknown strategy: $strategy"
        exit 1
        ;;
esac
