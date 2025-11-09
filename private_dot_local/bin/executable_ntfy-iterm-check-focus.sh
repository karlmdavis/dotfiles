#!/usr/bin/env bash
# Check if a specific TTY's iTerm2 session is currently focused
# Usage: ntfy-iterm-check-focus.sh <tty-path>
# Returns: 0 if focused, 1 if not focused or on error

set -euo pipefail

target_tty="${1:-}"

if [[ -z "$target_tty" ]]; then
    echo "Usage: $0 <tty-path>" >&2
    exit 2
fi

# AppleScript to check if target TTY is in focused session
focused=$(osascript 2>/dev/null <<EOF
tell application "iTerm2"
    try
        set focusedTTY to tty of current session of current window
        if focusedTTY is equal to "$target_tty" then
            return "true"
        else
            return "false"
        end if
    on error
        return "false"
    end try
end tell
EOF
) || focused="false"

if [[ "$focused" == "true" ]]; then
    exit 0  # Focused
else
    exit 1  # Not focused
fi
