#!/usr/bin/env bats

load '../helpers/test_helpers'

setup() {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR"
    export WKFLW_NTFY_DEBUG=0
    setup_mocks

    # Generate test session ID
    export TEST_SESSION_ID="2025-11-12T00-00-00-test0001"

    # Create symlinks without executable_ prefix for PATH usage
    local bin_dir="$BATS_TEST_TMPDIR/bin"
    mkdir -p "$bin_dir"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-config" "$bin_dir/wkflw-ntfy-config"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-log" "$bin_dir/wkflw-ntfy-log"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/push/wkflw-ntfy-push" "$bin_dir/wkflw-ntfy-push"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/linux/wkflw-ntfy-linux-send" "$bin_dir/wkflw-ntfy-linux-send"
    # Also add notify-send mock
    ln -sf "$PWD/test/wkflw-ntfy/mocks/executable_notify-send" "$BATS_TEST_TMPDIR/mock-bin/notify-send"
    export PATH="$bin_dir:$PATH"
}

@test "linux-send calls notify-send with title and body" {
    wkflw-ntfy-linux-send "$TEST_SESSION_ID" "Test Title" "Test body"

    assert_mock_called "notify-send"
    assert_file_contains "$MOCK_LOG_DIR/notify-send.log" "Test Title"
    assert_file_contains "$MOCK_LOG_DIR/notify-send.log" "Test body"
}

@test "linux-send falls back to push if notify-send missing" {
    export WKFLW_NTFY_TOPIC="test-topic"
    # Remove notify-send mock but keep other mocks
    rm -f "$BATS_TEST_TMPDIR/mock-bin/notify-send"

    wkflw-ntfy-linux-send "$TEST_SESSION_ID" "Title" "Body"

    # Should call curl (push) as fallback
    assert_mock_called "curl"
}
