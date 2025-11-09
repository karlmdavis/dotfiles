#!/usr/bin/env bash
# Shared test utilities for ntfy notification tests

# Setup test environment with mocks
setup_test_env() {
    # Add mocks to PATH
    local mocks_path
    mocks_path="$(pwd)/test/mocks"
    export PATH="$mocks_path:$PATH"

    # Create unique temp directory for this test run
    local temp_dir
    temp_dir="$(mktemp -d)"
    export TEST_TEMP_DIR="$temp_dir"

    # Use test-specific mock log
    export NTFY_MOCK_LOG="${TEST_TEMP_DIR}/ntfy-mock.log"
    touch "$NTFY_MOCK_LOG"

    # Override Claude tmp directory for tests
    export CLAUDE_TMP_DIR="${TEST_TEMP_DIR}/claude-tmp"
    mkdir -p "$CLAUDE_TMP_DIR"

    # Create a temporary HOME/.claude/tmp for testing
    export ORIGINAL_HOME="$HOME"
    export HOME="$TEST_TEMP_DIR/home"
    mkdir -p "$HOME/.claude/tmp"
    mkdir -p "$HOME/.local/bin"

    # Symlink actual scripts to test HOME
    ln -s "$ORIGINAL_HOME/.local/bin/ntfy-"* "$HOME/.local/bin/" 2>/dev/null || true
}

# Cleanup test environment
cleanup_test_env() {
    if [[ -n "${TEST_TEMP_DIR}" ]] && [[ -d "${TEST_TEMP_DIR}" ]]; then
        rm -rf "${TEST_TEMP_DIR}"
    fi

    # Restore original HOME
    if [[ -n "${ORIGINAL_HOME}" ]]; then
        export HOME="$ORIGINAL_HOME"
    fi
}

# Wait for background notification process to complete
wait_for_notification() {
    local max_wait="${1:-5}"
    local elapsed=0

    while [[ $elapsed -lt $max_wait ]]; do
        if [[ -f "$NTFY_MOCK_LOG" ]] && [[ -s "$NTFY_MOCK_LOG" ]]; then
            return 0
        fi
        sleep 0.5
        elapsed=$((elapsed + 1))
    done

    return 1
}

# Create a fake session start file for Claude hooks
create_session_start() {
    local session_id="$1"
    local start_time="${2:-$(($(date +%s) - 200))}"  # Default: 200 seconds ago
    local tty_path="${3:-/dev/ttys001}"

    echo "$start_time $tty_path" > "$HOME/.claude/tmp/session-${session_id}.start"
}
