#!/usr/bin/env bats
# Tests for cmd-notify. Run via `mise run test`.
#
# Strategy: drive the helper with --dry-run, which prints the would-be notifier invocation to
# stdout instead of executing it. Each test asserts on substrings of that line. No mocking; the
# script's behavior is deterministic when its env (HOME, platform, icons file) is controlled.

bats_require_minimum_version 1.5.0

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../../private_dot_local/bin/executable_cmd-notify"
    export HOME="$BATS_TEST_TMPDIR/home"
    mkdir -p "$HOME"

    # Empty icons table by default; tests that exercise icon lookup populate it.
    export CMD_NOTIFY_ICONS="$BATS_TEST_TMPDIR/icons.txt"
    : >"$CMD_NOTIFY_ICONS"

    unset CMD_NOTIFY_DISABLE CMD_NOTIFY_THRESHOLD CMD_NOTIFY_PLATFORM
}

# Convenience: assert substring presence in $output.
contains() { [[ "$output" == *"$1"* ]]; }

# --- Happy paths -----------------------------------------------------------------------------

@test "darwin: dispatches terminal-notifier with title, body, group" {
    CMD_NOTIFY_PLATFORM=Darwin run "$SCRIPT" --dry-run "sleep 90" 120 0 "/tmp/work"
    [ "$status" -eq 0 ]
    contains "terminal-notifier"
    contains "-title sleep 90"
    contains "-message succeeded in 2m 0s · work"
    contains "-group cmd-notify:sleep"
}

@test "linux: dispatches notify-send with grouping hint" {
    CMD_NOTIFY_PLATFORM=Linux run "$SCRIPT" --dry-run "sleep 90" 120 0 "/tmp/work"
    [ "$status" -eq 0 ]
    contains "notify-send"
    contains "string:x-canonical-private-synchronous:cmd-notify-sleep"
    # notify-send dry-run prints "<args> <title> <body>" — title and body are last two tokens.
    contains "sleep 90 succeeded in 2m 0s · work"
}

# --- Threshold and blocklist gating ----------------------------------------------------------

@test "skips silently when duration below threshold" {
    CMD_NOTIFY_PLATFORM=Darwin run "$SCRIPT" --dry-run "sleep 30" 30 0 "/tmp"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "skips when threshold env raised above duration" {
    CMD_NOTIFY_THRESHOLD=300 CMD_NOTIFY_PLATFORM=Darwin \
        run "$SCRIPT" --dry-run "sleep 120" 120 0 "/tmp"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "blocklist: skips for nvim" {
    CMD_NOTIFY_PLATFORM=Darwin run "$SCRIPT" --dry-run "nvim foo.txt" 600 0 "/tmp"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "blocklist: skips for claude (TUI session)" {
    CMD_NOTIFY_PLATFORM=Darwin run "$SCRIPT" --dry-run "claude --resume" 1800 0 "/tmp"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "blocklist: strips path before matching (so /usr/bin/vim skips)" {
    CMD_NOTIFY_PLATFORM=Darwin run "$SCRIPT" --dry-run "/usr/bin/vim notes.md" 600 0 "/tmp"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "kill switch: CMD_NOTIFY_DISABLE=1 always skips" {
    CMD_NOTIFY_DISABLE=1 CMD_NOTIFY_PLATFORM=Darwin \
        run "$SCRIPT" --dry-run "cargo build" 600 0 "/tmp"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "empty command skips silently" {
    CMD_NOTIFY_PLATFORM=Darwin run "$SCRIPT" --dry-run "" 600 0 "/tmp"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "non-numeric duration skips silently (defensive)" {
    CMD_NOTIFY_PLATFORM=Darwin run "$SCRIPT" --dry-run "cargo build" "not-a-number" 0 "/tmp"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# --- Title trimming and status -------------------------------------------------------------

@test "trims commands longer than 40 chars with an ellipsis" {
    # 80-char command: 80 'a's
    local long
    long="$(printf 'a%.0s' {1..80})"
    CMD_NOTIFY_PLATFORM=Darwin run "$SCRIPT" --dry-run "$long" 120 0 "/tmp"
    [ "$status" -eq 0 ]
    # Title is the long string truncated to 39 chars + …
    contains "-title $(printf 'a%.0s' {1..39})…"
}

@test "command exactly 40 chars is NOT truncated" {
    local exact
    exact="$(printf 'b%.0s' {1..40})"
    CMD_NOTIFY_PLATFORM=Darwin run "$SCRIPT" --dry-run "$exact" 120 0 "/tmp"
    [ "$status" -eq 0 ]
    contains "-title $exact"
    [[ "$output" != *"…"* ]]
}

@test "exit code 1 produces 'failed (exit 1)' body" {
    CMD_NOTIFY_PLATFORM=Darwin run "$SCRIPT" --dry-run "cargo test" 120 1 "/tmp"
    [ "$status" -eq 0 ]
    contains "failed (exit 1)"
}

@test "exit code 130 (SIGINT) produces 'failed (exit 130)' body" {
    CMD_NOTIFY_PLATFORM=Darwin run "$SCRIPT" --dry-run "cargo test" 120 130 "/tmp"
    [ "$status" -eq 0 ]
    contains "failed (exit 130)"
}

@test "duration formats: seconds-only when < 1 minute (threshold lowered for the test)" {
    CMD_NOTIFY_THRESHOLD=0 CMD_NOTIFY_PLATFORM=Darwin \
        run "$SCRIPT" --dry-run "yes" 5 0 "/tmp"
    [ "$status" -eq 0 ]
    contains "succeeded in 5s"
}

@test "duration formats: hours+minutes for ≥ 1h" {
    CMD_NOTIFY_PLATFORM=Darwin run "$SCRIPT" --dry-run "long-job" 3725 0 "/tmp"
    [ "$status" -eq 0 ]
    contains "succeeded in 1h 2m"
}

# --- cwd basename ---------------------------------------------------------------------------

@test "cwd basename is in the body" {
    CMD_NOTIFY_PLATFORM=Darwin run "$SCRIPT" --dry-run "cargo build" 120 0 "/Users/karl/projects/sneck-app"
    [ "$status" -eq 0 ]
    contains "· sneck-app"
}

@test "cwd of / produces a sensible body" {
    CMD_NOTIFY_PLATFORM=Darwin run "$SCRIPT" --dry-run "rsync -av" 120 0 "/"
    [ "$status" -eq 0 ]
    # Body still references the basename; for / we fall back to "/".
    contains "· /"
}

# --- Special characters ---------------------------------------------------------------------

@test "control characters in command don't break dispatch (newlines collapsed)" {
    # printf %b interprets backslash escapes — embed a literal newline + tab.
    local cmd
    cmd=$(printf 'cargo\ntest\t--all')
    CMD_NOTIFY_PLATFORM=Darwin run "$SCRIPT" --dry-run "$cmd" 120 0 "/tmp"
    [ "$status" -eq 0 ]
    # Dry-run output is a single line: newlines in input were collapsed to spaces.
    [ "$(printf '%s' "$output" | wc -l | tr -d ' ')" = "0" ] \
        || [ "$(printf '%s\n' "$output" | wc -l | tr -d ' ')" = "1" ]
}

@test "shell metacharacters in command are passed through verbatim to dispatch" {
    CMD_NOTIFY_PLATFORM=Darwin \
        run "$SCRIPT" --dry-run 'echo "hello $world"' 120 0 "/tmp"
    [ "$status" -eq 0 ]
    contains 'echo "hello $world'
}

# --- Icon resolution ------------------------------------------------------------------------

@test "uses cached icon when present (no curl, even with URL in table)" {
    mkdir -p "$HOME/.cache/cmd-notify/icons"
    echo "fake-png-bytes" >"$HOME/.cache/cmd-notify/icons/cargo.png"
    echo "cargo=http://example.invalid/should-not-be-fetched.png" >"$CMD_NOTIFY_ICONS"

    # Stub curl in a tempdir-prefixed PATH; if invoked, exits non-zero (test would still pass
    # since helper tolerates failure) but more importantly the stub records its call.
    local stub_dir="$BATS_TEST_TMPDIR/stubs"
    mkdir -p "$stub_dir"
    cat >"$stub_dir/curl" <<'EOF'
#!/usr/bin/env bash
echo "curl-called" >>"$BATS_TEST_TMPDIR/curl.log"
exit 1
EOF
    chmod +x "$stub_dir/curl"
    PATH="$stub_dir:$PATH" CMD_NOTIFY_PLATFORM=Darwin \
        run "$SCRIPT" --dry-run "cargo build" 120 0 "/tmp"
    [ "$status" -eq 0 ]
    contains "-contentImage $HOME/.cache/cmd-notify/icons/cargo.png"
    [ ! -f "$BATS_TEST_TMPDIR/curl.log" ]
}

@test "honors .miss sentinel: no curl, no icon arg" {
    mkdir -p "$HOME/.cache/cmd-notify/icons"
    : >"$HOME/.cache/cmd-notify/icons/cargo.miss"
    echo "cargo=http://example.invalid/cargo.png" >"$CMD_NOTIFY_ICONS"

    local stub_dir="$BATS_TEST_TMPDIR/stubs"
    mkdir -p "$stub_dir"
    cat >"$stub_dir/curl" <<'EOF'
#!/usr/bin/env bash
echo "curl-called" >>"$BATS_TEST_TMPDIR/curl.log"
exit 1
EOF
    chmod +x "$stub_dir/curl"
    PATH="$stub_dir:$PATH" CMD_NOTIFY_PLATFORM=Darwin \
        run "$SCRIPT" --dry-run "cargo build" 120 0 "/tmp"
    [ "$status" -eq 0 ]
    [[ "$output" != *"-contentImage"* ]]
    [ ! -f "$BATS_TEST_TMPDIR/curl.log" ]
}

@test "unknown command in icons file: no fetch, no icon arg" {
    # Empty icons table; cargo not listed.
    CMD_NOTIFY_PLATFORM=Darwin run "$SCRIPT" --dry-run "cargo build" 120 0 "/tmp"
    [ "$status" -eq 0 ]
    [[ "$output" != *"-contentImage"* ]]
}
