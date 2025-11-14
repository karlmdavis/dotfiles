#!/usr/bin/env bats
load '../helpers/test_helpers'


setup() {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR/markers"
    export WKFLW_NTFY_DEBUG=0

    # Generate test session ID
    export TEST_SESSION_ID="2025-11-12T00-00-00-test0001"

    # Create symlinks without executable_ prefix for PATH usage
    local bin_dir="$BATS_TEST_TMPDIR/bin"
    mkdir -p "$bin_dir"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-config" "$bin_dir/wkflw-ntfy-config"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-log" "$bin_dir/wkflw-ntfy-log"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/marker/wkflw-ntfy-marker-create" "$bin_dir/wkflw-ntfy-marker-create"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/marker/wkflw-ntfy-marker-check" "$bin_dir/wkflw-ntfy-marker-check"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/marker/wkflw-ntfy-marker-delete" "$bin_dir/wkflw-ntfy-marker-delete"
    export PATH="$bin_dir:$PATH"
}

@test "marker-create creates file with correct name pattern" {
    marker_path=$(wkflw-ntfy-marker-create "$TEST_SESSION_ID" "claude-stop" "/test/dir")

    [ -f "$marker_path" ]
    # Check it uses the session ID as the filename
    [[ "$marker_path" == *"$TEST_SESSION_ID" ]]
}

@test "marker-create writes JSON payload" {
    marker_path=$(wkflw-ntfy-marker-create "$TEST_SESSION_ID" "nushell" "/home/user/project")

    grep -q '"event_type": "nushell"' "$marker_path"
    grep -q '"cwd": "/home/user/project"' "$marker_path"
    grep -q '"pid": ' "$marker_path"
}

@test "marker-check returns 0 for existing marker" {
    marker_path=$(wkflw-ntfy-marker-create "$TEST_SESSION_ID" "test" "/test")
    wkflw-ntfy-marker-check "$TEST_SESSION_ID"
}

@test "marker-check returns 1 for missing marker" {
    run wkflw-ntfy-marker-check "nonexistent-session-id"
    [ "$status" -eq 1 ]
}

@test "marker-delete removes marker file" {
    marker_path=$(wkflw-ntfy-marker-create "$TEST_SESSION_ID" "test" "/test")
    [ -f "$marker_path" ]

    wkflw-ntfy-marker-delete "$TEST_SESSION_ID"
    [ ! -f "$marker_path" ]
}

@test "marker-delete returns 1 if marker already deleted" {
    test_session="test-marker-session"
    marker_path="$WKFLW_NTFY_STATE_DIR/markers/$test_session"
    touch "$marker_path"

    # First delete succeeds (returns 0)
    wkflw-ntfy-marker-delete "$test_session"

    # Second delete fails (returns 1 - marker already gone)
    run wkflw-ntfy-marker-delete "$test_session"
    [ "$status" -eq 1 ]
}
