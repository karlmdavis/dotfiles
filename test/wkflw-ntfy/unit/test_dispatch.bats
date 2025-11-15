#!/usr/bin/env bats

load '../helpers/test_helpers'

setup() {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR/markers"
    export WKFLW_NTFY_DEBUG=0
    export WKFLW_NTFY_TOPIC="test-topic"
    export WKFLW_NTFY_ESCALATION_DELAY=0  # No delay in tests
    setup_mocks

    # Generate test session ID
    export TEST_SESSION_ID="2025-11-12T00-00-00-test0001"

    # Create symlinks without executable_ prefix for PATH usage
    local bin_dir="$BATS_TEST_TMPDIR/bin"
    mkdir -p "$bin_dir"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-config" "$bin_dir/wkflw-ntfy-config"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-log" "$bin_dir/wkflw-ntfy-log"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-dispatch" "$bin_dir/wkflw-ntfy-dispatch"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/marker/wkflw-ntfy-marker-create" "$bin_dir/wkflw-ntfy-marker-create"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/marker/wkflw-ntfy-marker-check" "$bin_dir/wkflw-ntfy-marker-check"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/macos/wkflw-ntfy-macos-send" "$bin_dir/wkflw-ntfy-macos-send"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/linux/wkflw-ntfy-linux-send" "$bin_dir/wkflw-ntfy-linux-send"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/push/wkflw-ntfy-push" "$bin_dir/wkflw-ntfy-push"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/escalation/wkflw-ntfy-escalate-spawn" "$bin_dir/wkflw-ntfy-escalate-spawn"
    export PATH="$bin_dir:$PATH"
}

@test "dispatch progressive creates marker and sends macos notification" {
    wkflw-ntfy-dispatch "$TEST_SESSION_ID" "test-event" "iterm" "progressive" "Test Title" "Test Body" "/test/dir" "window-123"

    # Desktop notification should be sent
    assert_mock_called "terminal-notifier"
    assert_file_contains "$MOCK_LOG_DIR/terminal-notifier.log" "Test Title"
    assert_file_contains "$MOCK_LOG_DIR/terminal-notifier.log" "Test Body"

    # Marker should be created - check using marker-check
    run wkflw-ntfy-marker-check "$TEST_SESSION_ID"
    [ "$status" -eq 0 ]
}

@test "dispatch desktop-only with macos-gui sends macos notification" {
    wkflw-ntfy-dispatch "$TEST_SESSION_ID" "test-event" "macos-gui" "desktop-only" "Test Title" "Test Body" "/test/dir" ""

    # Desktop notification should be sent (macos)
    assert_mock_called "terminal-notifier"
    assert_file_contains "$MOCK_LOG_DIR/terminal-notifier.log" "Test Title"

    # No escalation worker
    # (We can't easily test absence, but we can verify no marker was created)
    marker_file="$WKFLW_NTFY_STATE_DIR/markers/${TEST_SESSION_ID}.json"
    [ ! -f "$marker_file" ]
}

@test "dispatch desktop-only with linux-gui sends linux notification" {
    wkflw-ntfy-dispatch "$TEST_SESSION_ID" "test-event" "linux-gui" "desktop-only" "Test Title" "Test Body" "/test/dir" ""

    # Desktop notification should be sent (linux)
    assert_mock_called "notify-send"
    assert_file_contains "$MOCK_LOG_DIR/notify-send.log" "Test Title"
    assert_file_contains "$MOCK_LOG_DIR/notify-send.log" "Test Body"

    # No macos notification
    assert_mock_not_called "terminal-notifier"
}

@test "dispatch push-only sends push notification" {
    wkflw-ntfy-dispatch "$TEST_SESSION_ID" "test-event" "nogui" "push-only" "Test Title" "Test Body" "/test/dir" ""

    # Push notification should be sent
    assert_mock_called "curl"

    # No desktop notification
    assert_mock_not_called "terminal-notifier"
    assert_mock_not_called "notify-send"
}

@test "dispatch handles unknown strategy" {
    run wkflw-ntfy-dispatch "$TEST_SESSION_ID" "test-event" "iterm" "unknown-strategy" "Test Title" "Test Body" "/test/dir" ""

    [ "$status" -eq 1 ]
}

@test "dispatch passes window_id to macos-send for progressive" {
    wkflw-ntfy-dispatch "$TEST_SESSION_ID" "test-event" "iterm" "progressive" "Test Title" "Test Body" "/test/dir" "window id 12345"

    # Check that window_id was passed (terminal-notifier should have callback)
    assert_file_contains "$MOCK_LOG_DIR/terminal-notifier.log" "execute"
    assert_file_contains "$MOCK_LOG_DIR/terminal-notifier.log" "12345"
}
