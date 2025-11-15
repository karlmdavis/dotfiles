#!/usr/bin/env bash
# Experimental Notification hook to test blocking and timeout behavior
set -euo pipefail

# Read JSON input from stdin
input_json=$(cat)

# Log everything
log_file="$HOME/.claude/tmp/hook-experiments.log"
echo "===== NOTIFICATION HOOK FIRED: $(date) =====" >> "$log_file"
echo "Input JSON: $input_json" | jq '.' >> "$log_file" 2>&1 || echo "$input_json" >> "$log_file"

# Extract message for audio feedback
message=$(echo "$input_json" | jq -r '.message // "unknown"')
echo "Message: $message" >> "$log_file"
echo "" >> "$log_file"

# Play a sound so you know it fired
say "Notification hook fired" &

# Configurable delay to test blocking behavior
# Set HOOK_DELAY env var to test different delays (in seconds)
# Default to 65 seconds to test timeout behavior
delay="${HOOK_DELAY:-65}"

if [[ $delay -gt 0 ]]; then
    echo "Sleeping for $delay seconds to test blocking..." >> "$log_file"
    for i in $(seq 1 "$delay"); do
        echo "  Second $i of $delay ($(date +%H:%M:%S))" >> "$log_file"
        sleep 1
    done
    echo "Sleep completed at $(date)" >> "$log_file"
fi

exit 0
