#!/usr/bin/env bats
load '../helpers/test_helpers'


setup() {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR/markers"
    export WKFLW_NTFY_DEBUG=0

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
    marker_path=$(wkflw-ntfy-marker-create "claude-stop" "/test/dir")

    [ -f "$marker_path" ]
    [[ "$marker_path" == *"claude-stop-"* ]]
    # Check it has a PID suffix (numeric)
    basename=$(basename "$marker_path")
    [[ "$basename" =~ -[0-9]+$ ]]
}

@test "marker-create writes JSON payload" {
    marker_path=$(wkflw-ntfy-marker-create "nushell" "/home/user/project")

    grep -q '"event_type": "nushell"' "$marker_path"
    grep -q '"cwd": "/home/user/project"' "$marker_path"
    grep -q '"pid": ' "$marker_path"
}

@test "marker-check returns 0 for existing marker" {
    marker_path=$(wkflw-ntfy-marker-create "test" "/test")
    wkflw-ntfy-marker-check "$marker_path"
}

@test "marker-check returns 1 for missing marker" {
    run wkflw-ntfy-marker-check "/nonexistent/marker"
    [ "$status" -eq 1 ]
}

@test "marker-delete removes marker file" {
    marker_path=$(wkflw-ntfy-marker-create "test" "/test")
    [ -f "$marker_path" ]

    wkflw-ntfy-marker-delete "$marker_path"
    [ ! -f "$marker_path" ]
}

@test "marker-delete is idempotent" {
    marker_path="$WKFLW_NTFY_STATE_DIR/markers/test-marker"
    touch "$marker_path"

    wkflw-ntfy-marker-delete "$marker_path"
    wkflw-ntfy-marker-delete "$marker_path"  # Should not error
}
