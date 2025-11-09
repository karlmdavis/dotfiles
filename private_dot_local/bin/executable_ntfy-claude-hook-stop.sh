#!/usr/bin/env bash
# Claude Code Stop hook handler
# Checks if Claude has been working long enough to warrant a notification
#
# This script is called by the Claude Code Stop hook and receives:
# - session_id
# - cwd (current working directory)
#
# It reads the start time/TTY from a temp file, calculates duration,
# and spawns a background notification check if duration >= 30 seconds.

set -euo pipefail

session_id="$1"
cwd="${2:-.}"

# Directory for Claude temporary files
claude_tmp="$HOME/.claude/tmp"
mkdir -p "$claude_tmp"

start_file="$claude_tmp/session-${session_id}.start"

# Check if start time was recorded
if [[ ! -f "$start_file" ]]; then
    # No start time recorded, skip notification
    exit 0
fi

# Read start time and TTY from file
read -r start_time tty_path < "$start_file"

# Cleanup start file
rm -f "$start_file"

# Calculate duration
end_time=$(date +%s)
duration=$((end_time - start_time))

# Duration threshold: 30 seconds (also in ntfy-nu-hooks.nu:37)
if [[ $duration -lt 30 ]]; then
    exit 0
fi

# Format duration for display
format_duration() {
    local total_seconds=$1
    local minutes=$((total_seconds / 60))
    local seconds=$((total_seconds % 60))

    if [[ $minutes -gt 0 ]]; then
        echo "${minutes}m ${seconds}s"
    else
        echo "${seconds}s"
    fi
}

duration_formatted=$(format_duration "$duration")

# Get project name from cwd (basename)
project_name=$(basename "$cwd")

# Spawn background notification check (detached from hook process)
# This allows the hook to complete quickly while notification logic runs in background
nohup "$HOME/.local/bin/ntfy-alert-if-unfocused.sh" \
    "$tty_path" \
    "Claude Code" \
    "Session completed" \
    "$duration_formatted" \
    "$project_name" \
    </dev/null >/dev/null 2>&1 &

disown

exit 0
