#!/usr/bin/env bats
# E2E tests for Claude Code notification hooks

load test_helpers

setup() {
    setup_test_env

    # Speed up tests with fast thresholds
    export NTFY_CLAUDE_DURATION_THRESHOLD=0.1
    export NTFY_GRACE_PERIOD=0.1
    export NTFY_IDLE_THRESHOLD=5

    export MOCK_ITERM_FOCUSED=false
    export MOCK_IDLE_SECONDS=30
}

teardown() {
    cleanup_test_env
}

@test "Claude: unfocused terminal → send notification" {
    # Setup: User is away (terminal not focused, idle)
    export MOCK_ITERM_FOCUSED=false
    export MOCK_IDLE_SECONDS=30

    # Simulate UserPromptSubmit hook (record start time)
    local session_id="test-session-unfocused"
    create_session_start "$session_id" "$(($(date +%s) - 1))" "/dev/ttys001"

    # Simulate Stop hook (pass JSON via stdin)
    echo "{\"session_id\": \"$session_id\", \"cwd\": \"$(pwd)\"}" | "$ORIGINAL_HOME/.local/bin/ntfy-claude-hook-stop.sh"

    # Wait for background notification process (immediate since unfocused)
    wait_for_notification 10

    # Assert: notification log was created
    [ -f "$NTFY_MOCK_LOG" ]

    # Assert: notification was sent
    run grep "Claude Code" "$NTFY_MOCK_LOG"
    echo "# NTFY_MOCK_LOG contents: $(cat "$NTFY_MOCK_LOG")" >&3
    [ "$status" -eq 0 ]

    # Assert: includes project name (chezmoi source directory)
    run grep "chezmoi" "$NTFY_MOCK_LOG"
    [ "$status" -eq 0 ]
}

@test "Claude: focused terminal + active user → no notification" {
    # Setup: User is actively watching (terminal focused, not idle)
    export MOCK_ITERM_FOCUSED=true
    export MOCK_IDLE_SECONDS=2

    # Simulate UserPromptSubmit hook
    local session_id="test-session-focused"
    create_session_start "$session_id" "$(($(date +%s) - 1))" "/dev/ttys001"

    # Simulate Stop hook (pass JSON via stdin)
    echo "{\"session_id\": \"$session_id\", \"cwd\": \"$(pwd)\"}" | "$ORIGINAL_HOME/.local/bin/ntfy-claude-hook-stop.sh"

    # Wait for grace period (0.1s) plus buffer
    sleep 0.3

    # Assert: NO notification sent (file should not exist or be empty)
    if [[ -f "$NTFY_MOCK_LOG" ]]; then
        run grep -q "Claude Code" "$NTFY_MOCK_LOG"
        [ "$status" -ne 0 ]
    fi
}

@test "Claude: short session (< 30 sec) → no notification" {
    # Setup: Session too short to warrant notification
    export MOCK_ITERM_FOCUSED=false
    export MOCK_IDLE_SECONDS=30

    # Simulate UserPromptSubmit hook with recent start time (~0 seconds ago)
    local session_id="test-session-short"
    create_session_start "$session_id" "$(date +%s)" "/dev/ttys001"

    # Simulate Stop hook (pass JSON via stdin)
    echo "{\"session_id\": \"$session_id\", \"cwd\": \"$(pwd)\"}" | "$ORIGINAL_HOME/.local/bin/ntfy-claude-hook-stop.sh"

    # Wait briefly
    sleep 0.3

    # Assert: NO notification sent (duration below threshold)
    if [[ -f "$NTFY_MOCK_LOG" ]]; then
        run grep -q "Claude Code" "$NTFY_MOCK_LOG"
        [ "$status" -ne 0 ]
    fi
}
