#!/usr/bin/env bash
# Generate a random ntfy topic UUID for secure notifications
# This script runs once via chezmoi to create a unique notification topic
# The topic file is NOT managed by chezmoi and is local to each machine

set -euo pipefail

topic_file="$HOME/.local/share/ntfy-topic"

# Only generate if file doesn't exist
if [[ -f "$topic_file" ]]; then
    echo "ntfy topic already exists at: $topic_file"
    exit 0
fi

# Ensure parent directory exists
mkdir -p "$(dirname "$topic_file")"

# Generate random UUID for topic name
# Use uuidgen if available, otherwise fall back to random generation
if command -v uuidgen &>/dev/null; then
    topic="claude-$(uuidgen | tr '[:upper:]' '[:lower:]')"
else
    # Fallback: generate random string
    topic="claude-$(head -c 16 /dev/urandom | base64 | tr -dc 'a-z0-9' | head -c 32)"
fi

# Write topic to file
echo "$topic" > "$topic_file"
chmod 600 "$topic_file"  # Protect the file

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Generated ntfy notification topic"
echo ""
echo "📍 Location: $topic_file"
echo "📱 Topic: $topic"
echo ""
echo "To receive notifications on your devices:"
echo "  1. Install ntfy on your phone/tablet:"
echo "     • iOS: https://apps.apple.com/us/app/ntfy/id1625396347"
echo "     • Android: https://play.google.com/store/apps/details?id=io.heckel.ntfy"
echo ""
echo "  2. Subscribe to your topic: $topic"
echo "     (Use the + button in the app)"
echo ""
echo "  3. Notifications will appear when:"
echo "     • Claude Code finishes work (after 3+ minutes)"
echo "     • Long-running shell commands complete (after 3+ minutes)"
echo ""
echo "⚠️  Keep this topic private! Anyone with the topic name can send you notifications."
echo ""
echo "📝 This file is NOT managed by chezmoi and is local to this machine."
echo "   If you delete it, run 'chezmoi apply --force' to regenerate."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
