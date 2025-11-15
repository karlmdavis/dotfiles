#!/usr/bin/env bats

load '../helpers/test_helpers'

setup() {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR"
    export WKFLW_NTFY_DEBUG=0

    # Create symlink for the Python script
    local bin_dir="$BATS_TEST_TMPDIR/bin"
    mkdir -p "$bin_dir"
    ln -sf "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/macos/wkflw-ntfy-zellij-clients.py" "$bin_dir/wkflw-ntfy-zellij-clients.py"
    export PATH="$bin_dir:$PATH"
}

@test "zellij-clients script is executable" {
    [ -x "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/macos/wkflw-ntfy-zellij-clients.py" ]
}

@test "zellij-clients requires PID argument" {
    run "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/macos/wkflw-ntfy-zellij-clients.py" "test-session"
    [ "$status" -eq 1 ]
    # Usage message goes to stderr
    [[ "$stderr" == *"Usage"* ]] || [[ "$output" == *"Usage"* ]]
}

@test "zellij-clients rejects invalid PID" {
    run "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/macos/wkflw-ntfy-zellij-clients.py" "test-session" "not-a-number"
    [ "$status" -eq 1 ]
    # Output should be valid JSON with error
    echo "$output" | jq -e '.error' > /dev/null
    echo "$output" | jq -e '.error' | grep -q "Invalid PID"
}

@test "zellij-clients handles non-existent PID" {
    run "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/macos/wkflw-ntfy-zellij-clients.py" "test-session" 999999
    [ "$status" -eq 1 ]
    # Output should be valid JSON with error
    echo "$output" | jq -e '.error' > /dev/null
    echo "$output" | jq -e '.error' | grep -q "not found"
}

@test "zellij-clients returns non-zero for non-server process" {
    # Test with current bash process (definitely not a zellij server)
    run "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/macos/wkflw-ntfy-zellij-clients.py" "test-session" $$
    [ "$status" -eq 1 ]
    # Output should be valid JSON
    echo "$output" | jq -e '.origin' > /dev/null
    # Classifier should not be zellij-server
    classifier=$(echo "$output" | jq -r '.origin.classifier')
    [ "$classifier" != "zellij-server" ]
}

@test "zellij-clients outputs valid JSON structure" {
    # Test with any PID (use init process which always exists)
    run "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/macos/wkflw-ntfy-zellij-clients.py" "test-session" 1
    # Should output valid JSON regardless of success/failure
    echo "$output" | jq -e '.origin' > /dev/null
    echo "$output" | jq -e '.origin.pid' > /dev/null
    echo "$output" | jq -e '.origin.command != null or .error != null' > /dev/null
    # Classifier field exists (can be null)
    echo "$output" | jq -e 'has("origin")' > /dev/null
}

@test "zellij-clients finds server if one exists" {
    # Try to find a zellij server process
    server_pid=$(ps aux | grep "zellij.*--server" | grep -v grep | head -1 | awk '{print $2}')

    if [ -z "$server_pid" ]; then
        skip "No zellij server found"
    fi

    run "$WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/macos/wkflw-ntfy-zellij-clients.py" "test-session" "$server_pid"
    [ "$status" -eq 0 ]

    # Verify it's classified as a server
    classifier=$(echo "$output" | jq -r '.origin.classifier')
    [ "$classifier" = "zellij-server" ]

    # Verify session name is present
    session_name=$(echo "$output" | jq -r '.origin.zellij_session')
    [ -n "$session_name" ]
    [ "$session_name" != "null" ]

    # Verify clients array exists (may be empty)
    echo "$output" | jq -e '.origin.clients' > /dev/null
}
