#!/usr/bin/env bats
#
# Tests for the Claude Code status line script (`statusline-command.sh`).
#
# Requirements the script must meet (each has at least one test below):
#   1. Segments come out most important first: location, context gauge, 5-hour gauge,
#      lines changed, model (effort), fast badge. Claude Code truncates from the right.
#   2. Location is the repo, with `[wt:<name>]` only inside a linked worktree; the
#      directory is shown only as a fallback when there is no repo.
#   3. Lines changed is omitted until something has changed.
#   4. Fields Claude Code already displays itself (session name, PR) and the worktree
#      branch never appear.
#   5. Optional fields may all be absent without breaking the line.
#
# Assertion style: bats runs under whatever `bash` is first on PATH, on macOS usually
# the system 3.2, where a failing `[[ ]]` does NOT trip errexit, so a `[[ ]]` that
# isn't a test's last command is silently ignored. Use `[ ]` or the helpers below,
# never bare `[[ ]]`.

bats_require_minimum_version 1.5.0

setup() {
  REPO="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
  SCRIPT="$REPO/private_dot_claude/statusline-command.sh"

  command -v jq >/dev/null 2>&1 || { echo "requires jq" >&2; return 1; }

  # Every field the script reads, plus the ones it must ignore.
  FULL='{
    "session_name": "my-session",
    "model": {"display_name": "Fable 5.1"},
    "workspace": {
      "current_dir": "/home/me/src/proj/sub",
      "git_worktree": "wt1",
      "repo": {"owner": "octo", "name": "dotfiles"}
    },
    "context_window": {"used_percentage": 42.4},
    "effort": {"level": "high"},
    "fast_mode": true,
    "rate_limits": {"five_hour": {"used_percentage": 91}},
    "cost": {"total_lines_added": 156, "total_lines_removed": 23},
    "pr": {"number": 48, "review_state": "approved"},
    "worktree": {"branch": "worktree-wt1"}
  }'
}

# Run the script on a JSON payload (invoked with bash, as settings.json does) and leave
# the line in $output with its colour escapes stripped.
statusline() {
  run bash "$SCRIPT" <<<"$1"
  [ "$status" -eq 0 ] || { echo "expected exit 0, got $status: $output" >&2; return 1; }
  output="$(printf '%s' "$output" | sed $'s/\033\\[[0-9;]*m//g')"
}

assert_line_is() {
  [ "$output" = "$1" ] || { echo "expected: $1" >&2; echo "got:      $output" >&2; return 1; }
}

assert_contains() {
  case "$output" in
    *"$1"*) ;;
    *) echo "expected to contain '$1': $output" >&2; return 1 ;;
  esac
}

refute_contains() {
  case "$output" in
    *"$1"*) echo "expected not to contain '$1': $output" >&2; return 1 ;;
  esac
}

@test "full payload renders every segment in priority order" {
  statusline "$FULL"
  assert_line_is "octo/dotfiles [wt:wt1]  ctx:42%  5h:91%  +156/-23  Fable 5.1 (high)  ⚡fast"
}

@test "directory is hidden when a repo is present" {
  statusline "$FULL"
  refute_contains "proj"
}

@test "directory is the fallback when there is no repo" {
  statusline "$(jq 'del(.workspace.repo)' <<<"$FULL")"
  assert_contains "…/src/proj/sub"
  refute_contains "octo"
}

@test "worktree suffix appears only inside a linked worktree" {
  statusline "$(jq 'del(.workspace.git_worktree)' <<<"$FULL")"
  assert_contains "octo/dotfiles  ctx:42%"
  refute_contains "[wt:"
}

@test "lines changed is omitted when nothing has changed" {
  statusline "$(jq '.cost = {"total_lines_added": 0, "total_lines_removed": 0}' <<<"$FULL")"
  assert_contains "5h:91%  Fable 5.1 (high)"

  statusline "$(jq 'del(.cost)' <<<"$FULL")"
  assert_contains "5h:91%  Fable 5.1 (high)"
}

@test "lines changed shows when only one side is non-zero" {
  statusline "$(jq '.cost = {"total_lines_added": 0, "total_lines_removed": 7}' <<<"$FULL")"
  assert_contains "+0/-7"
}

@test "session name, PR, and worktree branch never appear" {
  statusline "$FULL"
  refute_contains "my-session"
  refute_contains "#48"
  refute_contains "worktree-wt1"
}

@test "minimal payload still renders" {
  statusline '{"model": {"display_name": "Opus"}, "workspace": {"current_dir": "/tmp"}}'
  assert_contains "/tmp"
  assert_contains "Opus"
  refute_contains "ctx:"
  refute_contains "fast"
}
