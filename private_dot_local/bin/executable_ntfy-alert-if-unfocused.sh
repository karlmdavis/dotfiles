#!/usr/bin/env bash
# Hybrid notification script: notify only if user is away
# Uses immediate check + delayed grace period approach
#
# Usage: ntfy-alert-if-unfocused.sh <tty-path> <title> <message> <duration> <project-name>
#
# Hybrid logic:
# - If terminal focused AND user active (idle < 10s): wait 30s grace period, then recheck
# - Otherwise: notify immediately (user is clearly away)

set -euo pipefail

tty_path="${1:-unknown}"
title="$2"
message="$3"
duration="$4"
project_name="${5:-}"

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

    if [[ "$tty" == "unknown" ]]; then
        return 1  # Unknown TTY = not focused
    fi

    if ! command -v osascript &>/dev/null; then
        return 1  # No AppleScript = can't determine focus
    fi

    "$HOME/.local/bin/ntfy-iterm-check-focus.sh" "$tty"
}

# Function to get user idle time in seconds
get_idle_seconds() {
    if ! command -v ioreg &>/dev/null; then
        echo "999999"  # If can't determine, assume idle
        return
    fi

    ioreg -c IOHIDSystem 2>/dev/null | awk '/HIDIdleTime/ {print int($NF/1000000000); exit}' || echo "999999"
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

# Hybrid decision logic
# Idle threshold: 10 seconds (CANONICAL - also checked at line 88, documented in README.md:75)
if $is_focused && [[ $idle_seconds -lt 10 ]]; then
    # Terminal focused AND recently active - user might be reading something
    # Grace period: 30 seconds (CANONICAL - documented in README.md:74)
    sleep 30

    # Re-check after grace period
    is_focused_now=false
    is_terminal_focused "$tty_path" && is_focused_now=true

    idle_now=$(get_idle_seconds)

    if $is_focused_now && [[ $idle_now -lt 10 ]]; then
        # User is still present (both focused and active)
        exit 0  # Don't notify
    fi

    # User went away during grace period - notify
    send_notification
else
    # User is clearly away (terminal not focused OR idle > 10s)
    # Notify immediately
    send_notification
fi
