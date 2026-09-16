#!/usr/bin/env bats
#
# Tests for the `check-mise-usage.sh` pre-tool-call hook (Hermes + Claude Code).
#
# Requirements the script must meet (each has at least one test below):
#   1. Non-shell tools, and shell commands that do not run `uv`, are allowed with `{}`.
#   2. A bare `uv` invocation is blocked when a `mise.toml` exists in `cwd` or any parent.
#   3. `uv` wrapped by `mise exec` or preceded by `mise activate` is allowed.
#   4. A bare `uv` with no `mise.toml` anywhere above `cwd` is allowed.
#   5. On block, stdout is ONE JSON object carrying both contracts (top-level
#      `decision: block` for Hermes, `hookSpecificOutput.permissionDecision: deny` for
#      Claude Code), stderr carries the reason, and the exit status is 2.
#
# Assertion style: bats runs under whatever `bash` is first on PATH, on macOS usually
# the system 3.2, where a failing `[[ ]]` does NOT trip errexit, so a `[[ ]]` that
# isn't a test's last command is silently ignored. Use `[ ]` or the assert_* helpers
# below, never bare `[[ ]]`.

bats_require_minimum_version 1.5.0

setup() {
  REPO="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
  HOOK="$REPO/private_dot_local/lib/executable_check-mise-usage.sh"

  # jq is used by the script and by the assertions. It is in the system package manifest,
  # so a missing one is a broken machine: fail rather than skip.
  command -v jq >/dev/null 2>&1 || { echo "requires jq" >&2; return 1; }

  # A project tree with mise.toml at its root and a nested subdirectory, plus a tree
  # with no mise.toml at all. Both live under the bats tmpdir, whose ancestors
  # (/tmp, /private/tmp, ...) hold no mise.toml, so "no mise.toml above cwd" is real.
  PROJECT="$BATS_TEST_TMPDIR/project"
  mkdir -p "$PROJECT/src/deep"
  : > "$PROJECT/mise.toml"
  PLAIN="$BATS_TEST_TMPDIR/plain/dir"
  mkdir -p "$PLAIN"
}

# Run the hook with a payload built from tool name, command, and cwd; the script is
# POSIX sh and is executed through its own shebang, as both harnesses do.
hook() {
  jq -c -n --arg tool "$1" --arg cmd "$2" --arg cwd "$3" \
    '{tool_name: $tool, tool_input: {command: $cmd}, cwd: $cwd}' | "$HOOK"
}

assert_allowed() {
  [ "$status" -eq 0 ] || { echo "expected exit 0, got $status: $output" >&2; return 1; }
  [ "$output" = "{}" ] || { echo "expected {} on stdout, got: $output" >&2; return 1; }
}

# `run --separate-stderr` puts stdout in $output and stderr in $stderr.
assert_blocked() {
  [ "$status" -eq 2 ] || { echo "expected exit 2, got $status: $output" >&2; return 1; }
  [ "$(printf '%s' "$output" | jq -r '.decision')" = "block" ] \
    || { echo "missing top-level decision=block: $output" >&2; return 1; }
  [ "$(printf '%s' "$output" | jq -r '.hookSpecificOutput.hookEventName')" = "PreToolUse" ] \
    || { echo "missing hookSpecificOutput.hookEventName: $output" >&2; return 1; }
  [ "$(printf '%s' "$output" | jq -r '.hookSpecificOutput.permissionDecision')" = "deny" ] \
    || { echo "missing hookSpecificOutput.permissionDecision=deny: $output" >&2; return 1; }
  local reason
  reason="$(printf '%s' "$output" | jq -r '.reason')"
  [ -n "$reason" ] && [ "$reason" != "null" ] \
    || { echo "empty reason: $output" >&2; return 1; }
  [ "$(printf '%s' "$output" | jq -r '.hookSpecificOutput.permissionDecisionReason')" = "$reason" ] \
    || { echo "permissionDecisionReason differs from reason: $output" >&2; return 1; }
  [ "$stderr" = "$reason" ] \
    || { echo "stderr should carry the reason; got: $stderr" >&2; return 1; }
  [ "${#lines[@]}" -eq 1 ] \
    || { echo "stdout must be exactly one JSON line, got ${#lines[@]}: $output" >&2; return 1; }
}

@test "a non-shell tool is allowed without inspecting the payload" {
  run --separate-stderr hook Read "uv sync" "$PROJECT"
  assert_allowed
}

@test "a shell command that does not run uv is allowed" {
  run --separate-stderr hook Bash "ls -la && cat uv.lock" "$PROJECT"
  assert_allowed
}

@test "an empty command is allowed" {
  run --separate-stderr hook Bash "" "$PROJECT"
  assert_allowed
}

@test "bare uv in a mise project is blocked with both contracts and exit 2" {
  run --separate-stderr hook Bash "uv sync" "$PROJECT"
  assert_blocked
}

@test "Hermes' tool name (terminal) is checked the same as Claude's (Bash)" {
  run --separate-stderr hook terminal "uv run pytest" "$PROJECT"
  assert_blocked
}

@test "uv after a cd prefix in a compound command is blocked" {
  run --separate-stderr hook Bash "cd src && uv run python x.py" "$PROJECT"
  assert_blocked
}

@test "mise.toml in a parent of cwd still blocks" {
  run --separate-stderr hook Bash "uv sync" "$PROJECT/src/deep"
  assert_blocked
}

@test "uv wrapped by mise exec is allowed" {
  run --separate-stderr hook Bash "mise exec -- uv sync" "$PROJECT"
  assert_allowed
}

@test "uv after mise activate is allowed" {
  run --separate-stderr hook Bash 'eval "$(mise activate bash)" && uv sync' "$PROJECT"
  assert_allowed
}

@test "bare uv with no mise.toml above cwd is allowed" {
  run --separate-stderr hook Bash "uv sync" "$PLAIN"
  assert_allowed
}

@test "uv mentioned only as an argument is allowed" {
  run --separate-stderr hook Bash "grep uv README.md" "$PROJECT"
  assert_allowed
}
