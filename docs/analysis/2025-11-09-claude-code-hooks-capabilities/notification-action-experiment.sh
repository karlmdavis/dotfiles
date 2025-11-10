#!/usr/bin/env bash
# Experiment: Can we click a macOS notification and jump to a specific iTerm session?
#
# This script tests different approaches for making notifications actionable.

set -euo pipefail

# Test data
test_cwd="/Users/karl/.local/share/chezmoi"
test_session_id="test-123"

echo "=== macOS Notification Action Experiment ==="
echo ""
echo "Testing approaches for click-to-jump-to-session..."
echo ""

# Approach 1: Simple osascript notification (baseline)
echo "1. Simple notification (no action):"
osascript -e "display notification \"Claude Code finished work\" with title \"Test Notification\" subtitle \"$test_cwd\""
echo "   ✓ Sent (no click action)"
echo ""

# Approach 2: AppleScript with sound
echo "2. Notification with sound:"
osascript <<EOF
display notification "Claude Code finished work" ¬
    with title "Test Notification" ¬
    subtitle "$test_cwd" ¬
    sound name "Glass"
EOF
echo "   ✓ Sent (sound: Glass)"
echo ""

# Approach 3: Try to make iTerm active (separate from notification)
echo "3. Notification + activate iTerm (separate actions):"
osascript -e "display notification \"Click to see iTerm\" with title \"Test\" sound name \"Glass\""
sleep 1
osascript -e 'tell application "iTerm2" to activate'
echo "   ✓ Sent notification, then activated iTerm"
echo ""

# Approach 4: Try to activate specific iTerm session by directory
echo "4. Activate iTerm session by current directory:"
osascript <<EOF
tell application "iTerm2"
    activate
    tell current window
        tell current session
            -- Try to switch to session in specific directory
            -- This won't work if session already exists, but demonstrates approach
            write text "# This is a test - checking current directory"
            write text "pwd"
        end tell
    end tell
end tell
EOF
echo "   ✓ Attempted to interact with current session"
echo ""

echo "=== Analysis ==="
echo ""
echo "Key findings:"
echo "1. macOS display notification does NOT support click actions or buttons"
echo "2. Clicking notification activates the app that sent it (Terminal/iTerm)"
echo "3. We cannot embed AppleScript actions in notifications directly"
echo "4. Workarounds:"
echo "   - Send notification, then immediately activate iTerm + switch session"
echo "   - Use 'terminal-notifier' tool (if available) for richer notifications"
echo "   - Use macOS native Notification Center with action buttons (requires helper app)"
echo ""
echo "Testing terminal-notifier (if available):"
if command -v terminal-notifier &>/dev/null; then
    echo "terminal-notifier is installed, testing..."

    # Test 1: Basic notification with terminal-notifier
    terminal-notifier \
        -title "Claude Code" \
        -subtitle "$test_cwd" \
        -message "Session finished" \
        -sound Glass
    echo "   ✓ Sent basic terminal-notifier notification"

    # Test 2: Notification with action
    # Note: -execute runs a command when notification is clicked
    terminal-notifier \
        -title "Claude Code (Click to jump)" \
        -subtitle "$test_cwd" \
        -message "Click to activate session" \
        -sound Glass \
        -execute "osascript -e 'tell application \"iTerm2\" to activate'"
    echo "   ✓ Sent notification with click action"

else
    echo "terminal-notifier not installed"
    echo "Install with: brew install terminal-notifier"
fi
echo ""

echo "Next steps:"
echo "- Install terminal-notifier: brew install terminal-notifier"
echo "- Test -execute parameter with session-switching script"
echo "- Figure out how to identify correct iTerm tab by cwd or session_id"
echo ""
echo "=== SOLUTION FOUND ==="
echo ""
echo "Working approach for cross-space session jumping:"
echo "1. Get AppleScript session ID: osascript -e 'tell application \"iTerm2\" to tell current session of current window to get id'"
echo "2. Use 'select window' in AppleScript (not 'set frontmost') - this triggers space switch"
echo "3. Pass session ID to helper script via terminal-notifier -execute parameter"
echo ""
echo "See: jump-to-iterm-session-by-id.sh for working implementation"
