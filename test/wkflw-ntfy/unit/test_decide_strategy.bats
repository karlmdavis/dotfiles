#!/usr/bin/env bats
load '../helpers/test_helpers'


setup() {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR"
    export WKFLW_NTFY_DEBUG=0

    # Create symlinks without executable_ prefix for PATH usage
    local bin_dir="$BATS_TEST_TMPDIR/bin"
    mkdir -p "$bin_dir"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-config" "$bin_dir/wkflw-ntfy-config"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-log" "$bin_dir/wkflw-ntfy-log"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-decide-strategy" "$bin_dir/wkflw-ntfy-decide-strategy"
    export PATH="$bin_dir:$PATH"
}

@test "iTerm + claude-stop → progressive" {
    result=$(wkflw-ntfy-decide-strategy "iterm" "claude-stop" "")
    [[ "$result" == "progressive" ]]
}

@test "iTerm + claude-notification permission_prompt → desktop-only" {
    result=$(wkflw-ntfy-decide-strategy "iterm" "claude-notification" "permission_prompt")
    [[ "$result" == "desktop-only" ]]
}

@test "iTerm + claude-notification idle_input → progressive" {
    result=$(wkflw-ntfy-decide-strategy "iterm" "claude-notification" "idle_input")
    [[ "$result" == "progressive" ]]
}

@test "iTerm + nushell → progressive" {
    result=$(wkflw-ntfy-decide-strategy "iterm" "nushell" "")
    [[ "$result" == "progressive" ]]
}

@test "macos-gui + any event → desktop-only" {
    result=$(wkflw-ntfy-decide-strategy "macos-gui" "claude-stop" "")
    [[ "$result" == "desktop-only" ]]
}

@test "linux-gui + any event → desktop-only" {
    result=$(wkflw-ntfy-decide-strategy "linux-gui" "claude-stop" "")
    [[ "$result" == "desktop-only" ]]
}

@test "nogui + any event → push-only" {
    result=$(wkflw-ntfy-decide-strategy "nogui" "claude-stop" "")
    [[ "$result" == "push-only" ]]
}
