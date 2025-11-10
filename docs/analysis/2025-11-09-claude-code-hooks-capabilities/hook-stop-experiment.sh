#!/usr/bin/env bash
# Experimental Stop hook to understand when it fires
set -euo pipefail

# Read JSON input from stdin
input_json=$(cat)

# Log everything
log_file="$HOME/.claude/tmp/hook-experiments.log"
echo "===== STOP HOOK FIRED: $(date) =====" >> "$log_file"
echo "Input JSON: $input_json" | jq '.' >> "$log_file" 2>&1 || echo "$input_json" >> "$log_file"
echo "" >> "$log_file"

# Play a sound so you know it fired
say "Stop hook fired" &

exit 0
