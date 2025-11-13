#!/usr/bin/env bats

load '../helpers/test_helpers'

setup() {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR/callbacks"
    export WKFLW_NTFY_DEBUG=0
    setup_mocks

    # Generate test session ID
    export TEST_SESSION_ID="2025-11-12T00-00-00-test0001"

    # Create symlinks without executable_ prefix for PATH usage
    local bin_dir="$BATS_TEST_TMPDIR/bin"
    mkdir -p "$bin_dir"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-config" "$bin_dir/wkflw-ntfy-config"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-log" "$bin_dir/wkflw-ntfy-log"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/marker/wkflw-ntfy-marker-create" "$bin_dir/wkflw-ntfy-marker-create"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/marker/wkflw-ntfy-marker-delete" "$bin_dir/wkflw-ntfy-marker-delete"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/macos/wkflw-ntfy-macos-send" "$bin_dir/wkflw-ntfy-macos-send"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/macos/wkflw-ntfy-macos-callback" "$bin_dir/wkflw-ntfy-macos-callback"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/macos/wkflw-ntfy-macos-focus" "$bin_dir/wkflw-ntfy-macos-focus"
    export PATH="$bin_dir:$PATH"
}

@test "macos-send calls terminal-notifier with title and body" {
    wkflw-ntfy-macos-send "$TEST_SESSION_ID" "Test Title" "Test body"

    assert_mock_called "terminal-notifier"
    assert_file_contains "$MOCK_LOG_DIR/terminal-notifier.log" "Test Title"
    assert_file_contains "$MOCK_LOG_DIR/terminal-notifier.log" "Test body"
}

@test "macos-send includes callback when provided" {
    # With session ID system, callback path is constructed automatically
    # Create the callback script first so macos-send will use it
    callback_script="$WKFLW_NTFY_STATE_DIR/callbacks/${TEST_SESSION_ID}.sh"
    touch "$callback_script"

    wkflw-ntfy-macos-send "$TEST_SESSION_ID" "Title" "Body"

    assert_file_contains "$MOCK_LOG_DIR/terminal-notifier.log" "execute"
    assert_file_contains "$MOCK_LOG_DIR/terminal-notifier.log" "${TEST_SESSION_ID}.sh"
}

@test "macos-callback deletes marker and focuses window" {
    marker_path=$(wkflw-ntfy-marker-create "$TEST_SESSION_ID" "test" "/test")
    [ -f "$marker_path" ]

    wkflw-ntfy-macos-callback "$TEST_SESSION_ID" "window id 12345"

    # Marker should be deleted
    [ ! -f "$marker_path" ]

    # Window focus should be called
    assert_mock_called "osascript"
    assert_file_contains "$MOCK_LOG_DIR/osascript.log" "12345"
}
