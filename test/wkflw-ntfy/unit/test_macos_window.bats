#!/usr/bin/env bats

bats_require_minimum_version 1.5.0

load '../helpers/test_helpers'

setup() {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR"
    export WKFLW_NTFY_DEBUG=0
    setup_mocks

    # Create symlinks without executable_ prefix for PATH usage
    local bin_dir="$BATS_TEST_TMPDIR/bin"
    mkdir -p "$bin_dir"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-config" "$bin_dir/wkflw-ntfy-config"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-log" "$bin_dir/wkflw-ntfy-log"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/macos/wkflw-ntfy-macos-get-window" "$bin_dir/wkflw-ntfy-macos-get-window"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/macos/wkflw-ntfy-macos-focus" "$bin_dir/wkflw-ntfy-macos-focus"
    export PATH="$bin_dir:$MOCK_LOG_DIR:$PATH"
}

@test "macos-get-window calls osascript and returns window ID" {
    result=$(wkflw-ntfy-macos-get-window)

    assert_mock_called "osascript"
    [[ "$result" == "12345" ]]
}

@test "macos-focus calls osascript with window ID" {
    wkflw-ntfy-macos-focus "12345"

    assert_mock_called "osascript"
    assert_file_contains "$MOCK_LOG_DIR/osascript.log" "window id 12345"
}

@test "macos-get-window handles AppleScript failure gracefully" {
    # Override PATH to exclude osascript entirely (mock and system paths)
    # This simulates running on a system without AppleScript/iTerm support
    local bin_dir="$BATS_TEST_TMPDIR/bin"
    local mock_no_osascript="$BATS_TEST_TMPDIR/mock-no-osascript"
    mkdir -p "$mock_no_osascript"

    # Copy only the mocks we need (excluding osascript)
    ln -sf "$PWD/test/wkflw-ntfy/mocks/executable_terminal-notifier" "$mock_no_osascript/terminal-notifier"
    ln -sf "$PWD/test/wkflw-ntfy/mocks/executable_curl" "$mock_no_osascript/curl"

    # Run with restricted PATH that doesn't include system /usr/bin
    PATH="$bin_dir:$mock_no_osascript" run -127 wkflw-ntfy-macos-get-window
}
