#!/usr/bin/env bash
# Hybrid notification script: notify only if user is away
# Uses immediate check + delayed grace period approach
#
# Usage: ntfy-alert-if-unfocused.sh <tty-path> <title> <message> <duration> <project-name>
#
# Hybrid logic:
# - If terminal focused AND user active (idle < threshold): wait for grace period, then recheck
# - Otherwise: notify immediately (user is clearly away)

set -euo pipefail

tty_path="${1:-unknown}"
title="$2"
message="$3"
duration="$4"
project_name="${5:-}"

# Debug log
debug_log="$HOME/.claude/tmp/ntfy-debug.log"
echo "=== $(date) ===" >> "$debug_log"
echo "TTY: $tty_path" >> "$debug_log"

# Configuration defaults
grace_period="${NTFY_GRACE_PERIOD:-30}"
idle_threshold="${NTFY_IDLE_THRESHOLD:-10}"

# Read ntfy topic from config file
topic_file="$HOME/.local/share/ntfy-topic"
if [[ -f "$topic_file" ]]; then
    topic=$(cat "$topic_file")
else
    echo "Warning: ntfy topic file not found at $topic_file" >&2
    topic="claude-notifications"
fi

# Function to check if terminal is focused
is_terminal_focused() {
    local tty="$1"

    if ! command -v osascript &>/dev/null; then
        return 1  # No AppleScript = can't determine focus
    fi

    if [[ "$tty" == "unknown" ]]; then
        # Can't check specific TTY, but check if iTerm is frontmost application
        # This handles Claude Code and other non-TTY contexts
        local frontmost
        frontmost=$(osascript -e 'tell application "System Events" to get name of first application process whose frontmost is true' 2>/dev/null) || return 1

        if [[ "$frontmost" == "iTerm2" ]]; then
            return 0  # iTerm is frontmost, treat as focused
        else
            return 1  # Different app is frontmost
        fi
    fi

    "$HOME/.local/bin/ntfy-iterm-check-focus.sh" "$tty"
}

# Function to get user idle time in seconds
get_idle_seconds() {
    if ! command -v ioreg &>/dev/null; then
        echo "999999"  # If can't determine, assume idle
        return
    fi

    local idle_time
    idle_time=$(ioreg -c IOHIDSystem 2>/dev/null | awk '/HIDIdleTime/ {print int($NF/1000000000); exit}')

    if [[ -z "$idle_time" ]]; then
        echo "999999"
    else
        echo "$idle_time"
    fi
}

# Function to send notification
send_notification() {
    local full_message
    if [[ -n "$project_name" ]]; then
        full_message="[$project_name] $message ($duration)"
    else
        full_message="$message ($duration)"
    fi

    if command -v ntfy &>/dev/null; then
        ntfy publish "$topic" "$title: $full_message"
    else
        echo "Warning: ntfy not installed, notification not sent" >&2
        echo "Would have sent: $title: $full_message" >&2
    fi
}

# Immediate check
is_focused=false
is_terminal_focused "$tty_path" && is_focused=true

idle_seconds=$(get_idle_seconds)

echo "Initial check: is_focused=$is_focused, idle_seconds=$idle_seconds" >> "$debug_log"

# Hybrid decision logic
# Idle threshold (configurable via NTFY_IDLE_THRESHOLD)
if $is_focused && [[ $idle_seconds -lt $idle_threshold ]]; then
    # Terminal focused AND recently active - user might be reading something
    # Grace period (configurable via NTFY_GRACE_PERIOD)
    echo "User appears present, waiting grace period ($grace_period seconds)..." >> "$debug_log"
    sleep "$grace_period"

    # Re-check after grace period
    is_focused_now=false
    is_terminal_focused "$tty_path" && is_focused_now=true

    idle_now=$(get_idle_seconds)

    echo "After grace period: is_focused=$is_focused_now, idle_seconds=$idle_now" >> "$debug_log"

    if $is_focused_now && [[ $idle_now -lt $idle_threshold ]]; then
        # User is still present (both focused and active)
        echo "User still present, NOT sending notification" >> "$debug_log"
        exit 0  # Don't notify
    fi

    # User went away during grace period - notify
    echo "User went away during grace period, sending notification" >> "$debug_log"
    send_notification
else
    # User is clearly away (terminal not focused OR idle > 10s)
    # Notify immediately
    echo "User clearly away (focused=$is_focused, idle=$idle_seconds), sending notification immediately" >> "$debug_log"
    send_notification
fi
