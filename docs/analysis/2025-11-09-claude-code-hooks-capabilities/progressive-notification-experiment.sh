#!/usr/bin/env bash
# Experiment: Progressive notifications with marker files
#
# Tests if we can use marker files + notification clicks to implement:
# 1. Immediate desktop notification (click to acknowledge)
# 2. Delayed ntfy push if not acknowledged (progressive escalation)
#
# Flow:
# 1. Create marker file tied to iTerm session
# 2. Show desktop notification with click action to delete marker and jump to session
# 3. Background task waits N minutes, sends ntfy push if marker still exists
#
# Test scenarios:
# - Click notification → marker deleted, no ntfy push
# - Ignore notification → marker persists, ntfy push fires

set -euo pipefail

echo "=== Progressive Notification Experiment ==="
echo ""

# Configuration
MARKER_DIR="/tmp/ntfy-notifications"
DELAY_SECONDS=120  # 2 minutes for testing (production would be 10+ minutes)

# Ensure marker directory exists
mkdir -p "$MARKER_DIR"

# Get iTerm session ID (will be "unknown" if not in iTerm)
SESSION_ID=$(osascript -e "tell application \"iTerm2\" to tell current session of current window to get id" 2>/dev/null || echo "unknown")

if [ "$SESSION_ID" = "unknown" ]; then
    echo "⚠️  Not running in iTerm - will test fallback behavior"
    MARKER_FILE="$MARKER_DIR/test-notification-fallback"
else
    echo "✓ Running in iTerm session: $SESSION_ID"
    MARKER_FILE="$MARKER_DIR/notification-$SESSION_ID"
fi

echo "Marker file: $MARKER_FILE"
echo ""

# Create marker file
echo "$(date): Notification created for session $SESSION_ID" > "$MARKER_FILE"
echo "✓ Created marker file"

# Create helper script to handle notification click
CLICK_HANDLER="$MARKER_DIR/handle-click-$SESSION_ID.sh"
cat > "$CLICK_HANDLER" <<EOF
#!/usr/bin/env bash
# Handler script for notification click
set -euo pipefail

echo "\$(date): Notification clicked, deleting marker" >> "$MARKER_FILE.log"

# Delete marker file
rm -f "$MARKER_FILE"

# Jump to iTerm session if available
if [ "$SESSION_ID" != "unknown" ]; then
    osascript <<'APPLESCRIPT'
tell application "iTerm2"
    activate
    repeat with w in windows
        repeat with t in tabs of w
            repeat with s in sessions of t
                if id of s is "$SESSION_ID" then
                    select w
                    select t
                    return
                end if
            end repeat
        end repeat
    end repeat
end tell
APPLESCRIPT
fi
EOF
chmod +x "$CLICK_HANDLER"
echo "✓ Created click handler: $CLICK_HANDLER"

# Spawn background task to check marker after delay
BACKGROUND_CHECKER="$MARKER_DIR/check-marker-$SESSION_ID.sh"
cat > "$BACKGROUND_CHECKER" <<EOF
#!/usr/bin/env bash
set -euo pipefail

echo "\$(date): Background checker started, waiting $DELAY_SECONDS seconds..." >> "$MARKER_FILE.log"
sleep $DELAY_SECONDS

if [ -f "$MARKER_FILE" ]; then
    echo "\$(date): Marker still exists after $DELAY_SECONDS seconds - will send ntfy push" >> "$MARKER_FILE.log"

    # Delete marker FIRST (atomically claim it) to prevent race conditions:
    # - If user clicks notification during network call, won't trigger duplicate
    # - If background checker runs twice somehow, second one sees no marker
    rm -f "$MARKER_FILE"
    echo "\$(date): Deleted marker file, now sending ntfy push" >> "$MARKER_FILE.log"

    # Send ntfy push notification
    # TODO: Replace with actual ntfy.sh URL and topic
    curl -X POST \\
        -H "Title: Still waiting for you" \\
        -H "Priority: default" \\
        -H "Tags: warning" \\
        -d "Session $SESSION_ID is still waiting for your attention (test notification)" \\
        "https://ntfy.sh/test-progressive-notifications" 2>&1 >> "$MARKER_FILE.log" || true

    echo "\$(date): Sent ntfy push" >> "$MARKER_FILE.log"
    echo "✓ Sent ntfy push notification"
else
    echo "\$(date): Marker was deleted - notification was acknowledged" >> "$MARKER_FILE.log"
    echo "✓ No ntfy push needed (notification was acknowledged)"
fi

# Cleanup
rm -f "$BACKGROUND_CHECKER"
EOF
chmod +x "$BACKGROUND_CHECKER"
echo "✓ Created background checker: $BACKGROUND_CHECKER"

# Start background checker (detached)
nohup "$BACKGROUND_CHECKER" </dev/null >/dev/null 2>&1 &
echo "✓ Started background checker (PID: $!)"
echo ""

# Send desktop notification
echo "Sending desktop notification..."
if command -v terminal-notifier &>/dev/null; then
    terminal-notifier \
        -title "Progressive Notification Test" \
        -subtitle "Session: $SESSION_ID" \
        -message "Click to acknowledge (marker will be deleted)" \
        -sound Glass \
        -execute "$CLICK_HANDLER"
    echo "✓ Sent notification with terminal-notifier"
else
    echo "⚠️  terminal-notifier not installed - showing basic notification"
    osascript -e "display notification \"Click won't delete marker (terminal-notifier required)\" with title \"Progressive Notification Test\""
fi

echo ""
echo "=== Test Instructions ==="
echo ""
echo "SCENARIO 1: Test acknowledgement"
echo "1. Click the notification you just saw"
echo "2. Wait a few seconds"
echo "3. Run: cat $MARKER_FILE.log"
echo "4. Should see: \"Notification clicked, deleting marker\""
echo "5. Run: ls $MARKER_FILE"
echo "6. Should see: \"No such file\""
echo ""
echo "SCENARIO 2: Test progressive escalation"
echo "1. Run this script again: $0"
echo "2. DON'T click the notification"
echo "3. Wait $DELAY_SECONDS seconds (~2 minutes)"
echo "4. Check: cat $MARKER_FILE.log"
echo "5. Should see ntfy push was sent"
echo ""
echo "View logs: cat $MARKER_FILE.log"
echo "Check marker: ls -la $MARKER_FILE"
echo ""
