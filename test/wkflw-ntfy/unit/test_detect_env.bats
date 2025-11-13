#!/usr/bin/env bats
load '../helpers/test_helpers'


setup() {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR"
    export WKFLW_NTFY_DEBUG=0

    # Generate test session ID
    export TEST_SESSION_ID="2025-11-12T00-00-00-test0001"

    # Create symlinks without executable_ prefix for PATH usage
    local bin_dir="$BATS_TEST_TMPDIR/bin"
    mkdir -p "$bin_dir"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-config" "$bin_dir/wkflw-ntfy-config"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-log" "$bin_dir/wkflw-ntfy-log"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-detect-env" "$bin_dir/wkflw-ntfy-detect-env"
    export PATH="$bin_dir:$PATH"
}

@test "detect-env identifies iTerm" {
    export TERM_PROGRAM="iTerm.app"
    result=$(wkflw-ntfy-detect-env "$TEST_SESSION_ID")
    [[ "$result" == "iterm" ]]
}

@test "detect-env identifies macOS GUI (non-iTerm)" {
    export TERM_PROGRAM="Apple_Terminal"
    result=$(wkflw-ntfy-detect-env "$TEST_SESSION_ID")
    [[ "$result" == "macos-gui" ]]
}

@test "detect-env identifies Linux GUI (X11)" {
    unset TERM_PROGRAM
    export DISPLAY=":0"
    result=$(wkflw-ntfy-detect-env "$TEST_SESSION_ID")
    [[ "$result" == "linux-gui" ]]
}

@test "detect-env identifies Linux GUI (Wayland)" {
    unset TERM_PROGRAM
    unset DISPLAY
    export WAYLAND_DISPLAY="wayland-0"
    result=$(wkflw-ntfy-detect-env "$TEST_SESSION_ID")
    [[ "$result" == "linux-gui" ]]
}

@test "detect-env identifies no-GUI (SSH)" {
    unset TERM_PROGRAM
    unset DISPLAY
    unset WAYLAND_DISPLAY
    export SSH_CONNECTION="1.2.3.4 12345 5.6.7.8 22"
    result=$(wkflw-ntfy-detect-env "$TEST_SESSION_ID")
    [[ "$result" == "nogui" ]]
}

@test "detect-env identifies no-GUI (headless)" {
    unset TERM_PROGRAM
    unset DISPLAY
    unset WAYLAND_DISPLAY
    unset SSH_CONNECTION
    result=$(wkflw-ntfy-detect-env "$TEST_SESSION_ID")
    [[ "$result" == "nogui" ]]
}
