#!/usr/bin/env bats
load '../helpers/test_helpers'


setup() {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR/logs"

    # Generate test session ID
    export TEST_SESSION_ID="2025-11-12T00-00-00-test0001"

    # Create symlinks without executable_ prefix for PATH usage
    local bin_dir="$BATS_TEST_TMPDIR/bin"
    mkdir -p "$bin_dir"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-config" "$bin_dir/wkflw-ntfy-config"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-log" "$bin_dir/wkflw-ntfy-log"
    export PATH="$bin_dir:$PATH"
}

@test "log debug writes to debug log when debug enabled" {
    export WKFLW_NTFY_DEBUG=1
    wkflw-ntfy-log "$TEST_SESSION_ID" debug "test-component" "test message"

    # Check the session-specific log file
    debug_log="$WKFLW_NTFY_STATE_DIR/logs/${TEST_SESSION_ID}.log"
    [ -f "$debug_log" ]
    grep -q "test message" "$debug_log"
    grep -q "test-component" "$debug_log"
}

@test "log debug does nothing when debug disabled" {
    export WKFLW_NTFY_DEBUG=0
    wkflw-ntfy-log "$TEST_SESSION_ID" debug "test-component" "test message"

    debug_log="$WKFLW_NTFY_STATE_DIR/logs/${TEST_SESSION_ID}.log"
    [ ! -f "$debug_log" ]
}

@test "log warning writes to warnings log" {
    wkflw-ntfy-log "$TEST_SESSION_ID" warning "test-component" "test warning"

    warnings_log="$WKFLW_NTFY_STATE_DIR/warnings.log"
    [ -f "$warnings_log" ]
    grep -q "test warning" "$warnings_log"
    grep -q "WARNING" "$warnings_log"
}

@test "log error writes to warnings log" {
    wkflw-ntfy-log "$TEST_SESSION_ID" error "test-component" "test error"

    warnings_log="$WKFLW_NTFY_STATE_DIR/warnings.log"
    [ -f "$warnings_log" ]
    grep -q "test error" "$warnings_log"
    grep -q "ERROR" "$warnings_log"
}
