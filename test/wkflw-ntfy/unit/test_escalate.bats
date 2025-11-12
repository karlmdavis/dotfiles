#!/usr/bin/env bats

load '../helpers/test_helpers'

setup() {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR/markers"
    export WKFLW_NTFY_DEBUG=0
    export WKFLW_NTFY_TOPIC="test-topic"
    export WKFLW_NTFY_ESCALATION_DELAY=0  # No delay in tests
    setup_mocks

    # Create symlinks without executable_ prefix for PATH usage
    local bin_dir="$BATS_TEST_TMPDIR/bin"
    mkdir -p "$bin_dir"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-config" "$bin_dir/wkflw-ntfy-config"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-log" "$bin_dir/wkflw-ntfy-log"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/marker/wkflw-ntfy-marker-create" "$bin_dir/wkflw-ntfy-marker-create"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/marker/wkflw-ntfy-marker-check" "$bin_dir/wkflw-ntfy-marker-check"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/marker/wkflw-ntfy-marker-delete" "$bin_dir/wkflw-ntfy-marker-delete"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/push/wkflw-ntfy-push" "$bin_dir/wkflw-ntfy-push"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/escalation/wkflw-ntfy-escalate-worker" "$bin_dir/wkflw-ntfy-escalate-worker"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/escalation/wkflw-ntfy-escalate-spawn" "$bin_dir/wkflw-ntfy-escalate-spawn"
    export PATH="$bin_dir:$PATH"
}

@test "escalate-worker sends push if marker still exists" {
    marker_path=$(wkflw-ntfy-marker-create "test" "/test")

    wkflw-ntfy-escalate-worker "$marker_path" "Test Title" "Test body"

    # Marker should be deleted
    [ ! -f "$marker_path" ]

    # Push should be sent
    assert_mock_called "curl"
}

@test "escalate-worker exits silently if marker deleted (user acknowledged)" {
    marker_path="$WKFLW_NTFY_STATE_DIR/markers/nonexistent-marker"

    wkflw-ntfy-escalate-worker "$marker_path" "Test Title" "Test body"

    # Push should NOT be sent
    assert_mock_not_called "curl"
}

@test "escalate-spawn starts background worker" {
    marker_path=$(wkflw-ntfy-marker-create "test" "/test")

    # Spawn worker (should return immediately)
    wkflw-ntfy-escalate-spawn "$marker_path" "Test Title" "Test body"

    # Wait for worker to delete marker (with timeout)
    timeout=30  # 3 seconds max
    elapsed=0
    while [ -f "$marker_path" ] && [ $elapsed -lt $timeout ]; do
        sleep 0.1
        elapsed=$((elapsed + 1))
    done

    # Marker should be gone (worker ran)
    [ ! -f "$marker_path" ]

    # Push should be sent
    assert_mock_called "curl"
}

@test "escalate-worker cleans up callback script if dismissed" {
    marker_path=$(wkflw-ntfy-marker-create "test" "/test")
    callback_script="$WKFLW_NTFY_STATE_DIR/callback-test"
    touch "$callback_script"

    wkflw-ntfy-escalate-worker "$marker_path" "Test Title" "Test body" "$callback_script"

    # Marker should be deleted
    [ ! -f "$marker_path" ]

    # Callback script should be cleaned up
    [ ! -f "$callback_script" ]

    # Push should be sent
    assert_mock_called "curl"
}

@test "escalate-worker cleans up callback script if acknowledged" {
    marker_path=$(wkflw-ntfy-marker-create "test" "/test")
    callback_script="$WKFLW_NTFY_STATE_DIR/callback-test"
    touch "$callback_script"

    # Delete marker first (simulating user clicked notification)
    wkflw-ntfy-marker-delete "$marker_path"

    wkflw-ntfy-escalate-worker "$marker_path" "Test Title" "Test body" "$callback_script"

    # Callback script should still be cleaned up
    [ ! -f "$callback_script" ]

    # Push should NOT be sent
    assert_mock_not_called "curl"
}
