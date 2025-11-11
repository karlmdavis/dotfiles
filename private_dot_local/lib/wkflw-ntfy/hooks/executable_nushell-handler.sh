#!/usr/bin/env bash
# Nushell hook handler: Notify when long-running command completes
#
# Called by nushell with args:
# $1: command
# $2: duration (seconds)
# $3: exit code
# $4: cwd

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

cmd="${1:-}"
duration="${2:-0}"
exit_code="${3:-0}"
cwd="${4:-unknown}"

# Check threshold
threshold="${WKFLW_NTFY_NUSHELL_THRESHOLD:-90}"
if (( duration < threshold )); then
    "$SCRIPT_DIR/../core/wkflw-ntfy-log" debug "nushell" "Command duration ${duration}s below threshold ${threshold}s"
    exit 0
fi

# Filter interactive commands
filtered_cmds=("hx" "vim" "nvim" "nano" "emacs" "bash" "zsh" "fish" "nu" "htop" "top" "less" "more")
cmd_base=$(echo "$cmd" | awk '{print $1}')
for filtered in "${filtered_cmds[@]}"; do
    if [[ "$cmd_base" == "$filtered" ]]; then
        "$SCRIPT_DIR/../core/wkflw-ntfy-log" debug "nushell" "Command $cmd_base is filtered"
        exit 0
    fi
done

# Notification content
dir_name=$(basename "$cwd")
duration_min=$((duration / 60))
status="succeeded"
if [[ "$exit_code" != "0" ]]; then
    status="failed"
fi

title="Command Complete"
body="$dir_name: $cmd ($duration_min min, $status)"

# Detect environment and choose strategy
env=$("$SCRIPT_DIR/../core/wkflw-ntfy-detect-env")
strategy=$("$SCRIPT_DIR/../core/wkflw-ntfy-decide-strategy" "$env" "nushell" "")

"$SCRIPT_DIR/../core/wkflw-ntfy-log" debug "nushell" "Command: $cmd, Duration: ${duration}s, Environment: $env, Strategy: $strategy"

case "$strategy" in
    progressive)
        # Create marker for progressive escalation
        marker=$("$SCRIPT_DIR/../marker/wkflw-ntfy-marker-create" "nushell" "$cwd")

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
EOF
        chmod +x "$callback_script"

        # Send desktop notification with callback
        "$SCRIPT_DIR/../macos/wkflw-ntfy-macos-send" "$title" "$body" "$callback_script"

        # Spawn escalation worker
        "$SCRIPT_DIR/../escalation/wkflw-ntfy-escalate-spawn" "$marker" "$title" "$body"
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
        "$SCRIPT_DIR/../core/wkflw-ntfy-log" error "nushell" "Unknown strategy: $strategy"
        exit 1
        ;;
esac
