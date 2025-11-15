#!/usr/bin/env bash
# Experiment: Terminal environment detection and capability testing
#
# Tests what works in different terminal environments:
# - iTerm2 (full support expected)
# - VS Code integrated terminal
# - macOS Terminal.app
# - Other terminals
#
# For each environment, test:
# - Can we get a session/window ID?
# - Do AppleScript commands work?
# - What fallback behavior makes sense?

set -euo pipefail

echo "=== Terminal Environment Detection Experiment ==="
echo ""

# Detect terminal environment
detect_terminal() {
    # Check environment variables that indicate terminal type
    if [ -n "${TERM_PROGRAM:-}" ]; then
        echo "$TERM_PROGRAM"
    elif [ -n "${VSCODE_INJECTION:-}" ]; then
        echo "vscode"
    elif [ -n "${ITERM_SESSION_ID:-}" ]; then
        echo "iTerm2"
    else
        echo "unknown"
    fi
}

TERMINAL_TYPE=$(detect_terminal)
echo "Detected terminal: $TERMINAL_TYPE"
echo "  TERM_PROGRAM: ${TERM_PROGRAM:-<not set>}"
echo "  ITERM_SESSION_ID: ${ITERM_SESSION_ID:-<not set>}"
echo "  VSCODE_INJECTION: ${VSCODE_INJECTION:-<not set>}"
echo ""

# Test: Can we get iTerm session ID?
echo "=== Test 1: iTerm Session ID ==="
if ITERM_SESSION_ID=$(osascript -e "tell application \"iTerm2\" to tell current session of current window to get id" 2>&1); then
    echo "✓ SUCCESS: Got iTerm session ID: $ITERM_SESSION_ID"
    CAN_GET_SESSION_ID=true
else
    echo "✗ FAILED: Cannot get iTerm session ID"
    echo "  Error: $ITERM_SESSION_ID"
    CAN_GET_SESSION_ID=false
fi
echo ""

# Test: Can we activate iTerm?
echo "=== Test 2: Activate iTerm ==="
if osascript -e 'tell application "iTerm2" to activate' 2>&1; then
    echo "✓ SUCCESS: Can activate iTerm"
    CAN_ACTIVATE=true
else
    echo "✗ FAILED: Cannot activate iTerm"
    CAN_ACTIVATE=false
fi
echo ""

# Test: Can we list iTerm windows?
echo "=== Test 3: List iTerm Windows ==="
if WINDOW_COUNT=$(osascript -e 'tell application "iTerm2" to count windows' 2>&1); then
    echo "✓ SUCCESS: Can query iTerm windows (count: $WINDOW_COUNT)"
    CAN_QUERY_WINDOWS=true
else
    echo "✗ FAILED: Cannot query iTerm windows"
    echo "  Error: $WINDOW_COUNT"
    CAN_QUERY_WINDOWS=false
fi
echo ""

# Test: Can we send desktop notifications?
echo "=== Test 4: Desktop Notifications ==="
if command -v terminal-notifier &>/dev/null; then
    echo "✓ terminal-notifier available"
    CAN_USE_TERMINAL_NOTIFIER=true

    # Test sending notification
    if terminal-notifier -title "Test" -message "Environment detection test" -sound Glass 2>&1; then
        echo "✓ SUCCESS: Sent notification with terminal-notifier"
    else
        echo "⚠️  terminal-notifier exists but failed to send notification"
    fi
else
    echo "⚠️  terminal-notifier not installed (falling back to osascript)"
    CAN_USE_TERMINAL_NOTIFIER=false

    # Test osascript notification
    if osascript -e 'display notification "Environment detection test" with title "Test"' 2>&1; then
        echo "✓ SUCCESS: Sent notification with osascript"
    else
        echo "✗ FAILED: Cannot send notifications"
    fi
fi
echo ""

# Test: Can we detect if terminal is focused?
echo "=== Test 5: Focus Detection ==="
if FRONTMOST=$(osascript -e 'tell application "System Events" to get name of first application process whose frontmost is true' 2>&1); then
    echo "✓ SUCCESS: Can detect frontmost app: $FRONTMOST"
    CAN_DETECT_FOCUS=true

    if [[ "$FRONTMOST" == "iTerm2" ]]; then
        echo "  → iTerm is currently focused"
    elif [[ "$FRONTMOST" == "Code" ]] || [[ "$FRONTMOST" == "Visual Studio Code" ]]; then
        echo "  → VS Code is currently focused"
    else
        echo "  → Another app is focused: $FRONTMOST"
    fi
else
    echo "✗ FAILED: Cannot detect frontmost app"
    echo "  Error: $FRONTMOST"
    CAN_DETECT_FOCUS=false
fi
echo ""

# Test: Can we get user idle time?
echo "=== Test 6: User Idle Time ==="
if command -v ioreg &>/dev/null; then
    IDLE_TIME=$(ioreg -c IOHIDSystem 2>/dev/null | awk '/HIDIdleTime/ {print int($NF/1000000000); exit}' || echo "error")
    if [[ "$IDLE_TIME" != "error" ]]; then
        echo "✓ SUCCESS: Can get idle time: ${IDLE_TIME}s"
        CAN_GET_IDLE=true
    else
        echo "✗ FAILED: ioreg command failed"
        CAN_GET_IDLE=false
    fi
else
    echo "✗ FAILED: ioreg not available"
    CAN_GET_IDLE=false
fi
echo ""

# Summary and recommendations
echo "=== Summary ==="
echo ""
echo "Environment: $TERMINAL_TYPE"
echo "Capabilities:"
echo "  - Get iTerm session ID: $CAN_GET_SESSION_ID"
echo "  - Activate iTerm: $CAN_ACTIVATE"
echo "  - Query iTerm windows: $CAN_QUERY_WINDOWS"
echo "  - terminal-notifier: $CAN_USE_TERMINAL_NOTIFIER"
echo "  - Detect focus: $CAN_DETECT_FOCUS"
echo "  - Get idle time: $CAN_GET_IDLE"
echo ""

# Determine appropriate fallback level
echo "=== Recommended Fallback Strategy ==="
echo ""

if $CAN_GET_SESSION_ID && $CAN_USE_TERMINAL_NOTIFIER; then
    echo "LEVEL 1: Full support"
    echo "  - Desktop notification with click-to-jump"
    echo "  - Progressive escalation to ntfy push"
    echo "  - Hybrid focus detection (app + idle)"
elif $CAN_ACTIVATE && $CAN_USE_TERMINAL_NOTIFIER; then
    echo "LEVEL 2: Partial support"
    echo "  - Desktop notification with click-to-activate (no specific session)"
    echo "  - Progressive escalation to ntfy push"
    echo "  - Basic focus detection (app only)"
elif command -v terminal-notifier &>/dev/null || osascript -e 'display notification "test"' &>/dev/null 2>&1; then
    echo "LEVEL 3: Desktop only"
    echo "  - Desktop notification (no click action)"
    echo "  - Progressive escalation to ntfy push"
    echo "  - No focus detection (always notify)"
else
    echo "LEVEL 4: Minimal support"
    echo "  - ntfy push only (no desktop notification)"
    echo "  - Immediate notification (no progressive delay)"
fi
echo ""

# Environment-specific notes
echo "=== Environment-Specific Notes ==="
echo ""

case "$TERMINAL_TYPE" in
    "iTerm.app" | "iTerm2")
        echo "iTerm2: Full support expected"
        echo "  - All features should work"
        echo "  - Use full click-to-jump notification system"
        ;;
    "vscode" | "Code")
        echo "VS Code: Partial support"
        echo "  - Running in VS Code integrated terminal"
        echo "  - iTerm AppleScript commands may not work"
        echo "  - Fallback: desktop notification only, no session jumping"
        echo "  - Consider: detect VS Code and use different activation method"
        ;;
    "Apple_Terminal")
        echo "macOS Terminal.app: Partial support"
        echo "  - iTerm-specific commands won't work"
        echo "  - Fallback: desktop notification only"
        ;;
    *)
        echo "Unknown terminal: Minimal support"
        echo "  - Use most conservative fallback"
        echo "  - Desktop notification if possible, otherwise ntfy push only"
        ;;
esac
echo ""
