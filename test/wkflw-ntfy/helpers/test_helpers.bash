#!/usr/bin/env bash
# Test helpers for wkflw-ntfy tests

# Deploy scripts with chezmoi to temp directory (runs once per test file)
setup_file() {
    # Use BATS_FILE_TMPDIR which is set during setup_file
    export WKFLW_NTFY_TEST_DIR="$BATS_FILE_TMPDIR/deployed"

    # Create destination directory
    mkdir -p "$WKFLW_NTFY_TEST_DIR"

    # Deploy wkflw-ntfy scripts to temp directory
    # This gives us the actual deployed file structure (without executable_ prefix)
    local repo_root
    repo_root="$(git rev-parse --show-toplevel)"

    # Use --source to specify source directory explicitly
    # This prevents chezmoi from looking at the actual home directory
    chezmoi apply --source "$repo_root" --destination "$WKFLW_NTFY_TEST_DIR"

    # BATS will automatically clean up $BATS_FILE_TMPDIR when tests complete
}

# Setup mock environment
setup_mocks() {
    export MOCK_LOG_DIR="$BATS_TEST_TMPDIR/logs"
    mkdir -p "$MOCK_LOG_DIR"

    # Create symlinks without executable_ prefix
    local mock_bin_dir="$BATS_TEST_TMPDIR/mock-bin"
    mkdir -p "$mock_bin_dir"
    ln -sf "$PWD/test/wkflw-ntfy/mocks/executable_terminal-notifier" "$mock_bin_dir/terminal-notifier"
    ln -sf "$PWD/test/wkflw-ntfy/mocks/executable_osascript" "$mock_bin_dir/osascript"
    ln -sf "$PWD/test/wkflw-ntfy/mocks/executable_curl" "$mock_bin_dir/curl"
    ln -sf "$PWD/test/wkflw-ntfy/mocks/executable_notify-send" "$mock_bin_dir/notify-send"
    export PATH="$mock_bin_dir:$PATH"

    # Clear old logs
    rm -f "$MOCK_LOG_DIR"/*.log
}

# Assertions
assert_file_exists() {
    [ -f "$1" ] || {
        echo "File not found: $1" >&2
        return 1
    }
}

assert_file_contains() {
    grep -q "$2" "$1" || {
        echo "File $1 does not contain: $2" >&2
        echo "Contents:" >&2
        cat "$1" >&2
        return 1
    }
}

assert_mock_called() {
    local mock_name="$1"
    local mock_log="$MOCK_LOG_DIR/$mock_name.log"
    [ -f "$mock_log" ] || {
        echo "Mock $mock_name was not called (no log file)" >&2
        return 1
    }
}

assert_mock_not_called() {
    local mock_name="$1"
    local mock_log="$MOCK_LOG_DIR/$mock_name.log"
    [ ! -f "$mock_log" ] || {
        echo "Mock $mock_name should not have been called" >&2
        echo "Log contents:" >&2
        cat "$mock_log" >&2
        return 1
    }
}
