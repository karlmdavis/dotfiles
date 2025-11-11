#!/usr/bin/env bats

load '../helpers/test_helpers'

setup() {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR"
    export WKFLW_NTFY_DEBUG=0
    export WKFLW_NTFY_TOPIC="test-topic-12345"
    export WKFLW_NTFY_SERVER="https://ntfy.sh"
    setup_mocks

    # Create symlinks without executable_ prefix for PATH usage
    local bin_dir="$BATS_TEST_TMPDIR/bin"
    mkdir -p "$bin_dir"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-config" "$bin_dir/wkflw-ntfy-config"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-log" "$bin_dir/wkflw-ntfy-log"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/push/wkflw-ntfy-push" "$bin_dir/wkflw-ntfy-push"
    export PATH="$bin_dir:$PATH"
}

@test "push sends notification via curl to ntfy server" {
    wkflw-ntfy-push "Test Title" "Test body message"

    assert_mock_called "curl"
    assert_file_contains "$MOCK_LOG_DIR/curl.log" "https://ntfy.sh/test-topic-12345"
    assert_file_contains "$MOCK_LOG_DIR/curl.log" "POST"
}

@test "push includes title and body in request" {
    wkflw-ntfy-push "My Title" "My body"

    assert_file_contains "$MOCK_LOG_DIR/curl.log" "My Title"
    assert_file_contains "$MOCK_LOG_DIR/curl.log" "My body"
}

@test "push handles missing topic gracefully" {
    unset WKFLW_NTFY_TOPIC

    run wkflw-ntfy-push "Title" "Body"
    [ "$status" -ne 0 ]
}
