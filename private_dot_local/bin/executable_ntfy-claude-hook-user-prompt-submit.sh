#!/usr/bin/env bash
# Claude Code UserPromptSubmit hook handler
# Records the start time and TTY when user submits a prompt
#
# This allows the Stop hook to calculate duration and know which terminal to check

set -euo pipefail

# Read JSON input from stdin
input_json=$(cat)
session_id=$(echo "$input_json" | jq -r '.session_id')

# Directory for Claude temporary files
claude_tmp="$HOME/.claude/tmp"
mkdir -p "$claude_tmp"

start_file="$claude_tmp/session-${session_id}.start"

# Get current timestamp
start_time=$(date +%s)

# Try to get TTY (will be 'unknown' if not available)
# Redirect both stdout and stderr to capture any error messages
tty_output=$(tty 2>&1) || true

# Validate TTY path (must start with /dev/)
if [[ "$tty_output" =~ ^/dev/ ]]; then
    tty_path="$tty_output"
else
    tty_path="unknown"
fi

# Check if we're in a Zellij session and can get pane info
if [[ -n "${ZELLIJ_PANE_ID:-}" ]] && [[ "$tty_path" == "unknown" ]]; then
    # We're in Zellij but don't have a direct TTY
    # Try to infer from parent shell
    tty_output=$(ps -p $$ -o tty= 2>&1) || true
    if [[ "$tty_output" =~ ^/dev/ ]]; then
        tty_path="$tty_output"
    else
        tty_path="unknown"
    fi
fi

# Write start time and TTY to file
echo "$start_time $tty_path" > "$start_file"

exit 0
