#!/usr/bin/env bats
#
# Tests for how `dot_aerospace.toml.tmpl` renders the per-machine data in
# ~/.config/aerospace/workspaces.yaml.
#
# Requirements the template must meet (each has at least one test below):
#   1. With no `sticky-windows` rules (no workspaces.yaml, or one without the key), the
#      exec-on-workspace-change hook is the SwiftBar refresh alone, so machines without rules
#      pay nothing per workspace switch.
#   2. With rules, the hook runs follow-sticky-windows.py first, then the SwiftBar refresh.
#   3. `window-rules` still render as [[on-window-detected]] blocks alongside sticky rules.
#
# Rendering uses `chezmoi execute-template` with HOME pointed at a temp dir, which is what
# `.chezmoi.homeDir` (and so the template's workspaces.yaml lookup) resolves from, and an
# empty config so this machine's chezmoi data doesn't leak in.
#
# Assertion style: bats runs under whatever `bash` is first on PATH, on macOS usually
# the system 3.2, where a failing `[[ ]]` does NOT trip errexit, so a `[[ ]]` that
# isn't a test's last command is silently ignored. Use `[ ]` or the assert_* helpers
# below, never bare `[[ ]]`.

bats_require_minimum_version 1.5.0

setup() {
  REPO="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
  TEMPLATE="$REPO/dot_aerospace.toml.tmpl"

  # chezmoi is what applies this repo at all, so a missing one is a broken machine: fail
  # rather than skip.
  command -v chezmoi >/dev/null 2>&1 || { echo "requires chezmoi" >&2; return 1; }

  FAKE_HOME="$BATS_TEST_TMPDIR/home"
  mkdir -p "$FAKE_HOME/.config/aerospace"
  CONFIG="$BATS_TEST_TMPDIR/chezmoi.toml"
  : > "$CONFIG"
}

# Render the template against $FAKE_HOME; output lands in $output.
render() {
  HOME="$FAKE_HOME" chezmoi --config "$CONFIG" --source "$REPO" execute-template < "$TEMPLATE"
}

write_workspaces_yaml() {
  printf '%s\n' "$1" > "$FAKE_HOME/.config/aerospace/workspaces.yaml"
}

assert_contains() {   # assert_contains "$haystack" "$needle"
  case "$1" in *"$2"*) return 0 ;; esac
  echo "expected to contain: $2" >&2
  echo "actual: $1" >&2
  return 1
}

assert_not_contains() {   # assert_not_contains "$haystack" "$needle"
  case "$1" in *"$2"*) echo "expected NOT to contain: $2" >&2; return 1 ;; esac
  return 0
}

SWIFTBAR_ONLY_HOOK="exec-on-workspace-change = ['/bin/bash', '-c', \"open -g 'swiftbar://refreshallplugins'\"]"
STICKY_HOOK="\"~/.config/aerospace/follow-sticky-windows.py; open -g 'swiftbar://refreshallplugins'\"]"

@test "no workspaces.yaml: the hook is the SwiftBar refresh alone" {
  run --separate-stderr render
  [ "$status" -eq 0 ] || { echo "render failed: $stderr" >&2; return 1; }
  assert_contains "$output" "$SWIFTBAR_ONLY_HOOK"
  assert_not_contains "$output" "follow-sticky-windows"
}

@test "workspaces.yaml without sticky-windows: the hook is the SwiftBar refresh alone" {
  write_workspaces_yaml 'workspaces:
  C:
    name: Comms'
  run --separate-stderr render
  [ "$status" -eq 0 ] || { echo "render failed: $stderr" >&2; return 1; }
  assert_contains "$output" "$SWIFTBAR_ONLY_HOOK"
  assert_not_contains "$output" "follow-sticky-windows"
}

@test "an empty sticky-windows list is treated as no rules" {
  write_workspaces_yaml 'sticky-windows: []'
  run --separate-stderr render
  [ "$status" -eq 0 ] || { echo "render failed: $stderr" >&2; return 1; }
  assert_contains "$output" "$SWIFTBAR_ONLY_HOOK"
  assert_not_contains "$output" "follow-sticky-windows"
}

@test "sticky-windows rules: the hook runs the sticky script, then the SwiftBar refresh" {
  write_workspaces_yaml 'sticky-windows:
  - app-id: com.example.Popup'
  run --separate-stderr render
  [ "$status" -eq 0 ] || { echo "render failed: $stderr" >&2; return 1; }
  assert_contains "$output" "$STICKY_HOOK"
  assert_not_contains "$output" "$SWIFTBAR_ONLY_HOOK"
  # Exactly one hook definition (a duplicate key would be a TOML error in AeroSpace).
  [ "$(printf '%s\n' "$output" | grep -c '^exec-on-workspace-change')" -eq 1 ]
}

@test "window-rules still render alongside sticky-windows" {
  write_workspaces_yaml 'window-rules:
  - app-id: com.example.Chat
    workspace: C
  - app-id: com.example.Mail
    title-regex: "[Cc]alendar"
    workspace: S
sticky-windows:
  - app-id: com.example.Popup'
  run --separate-stderr render
  [ "$status" -eq 0 ] || { echo "render failed: $stderr" >&2; return 1; }
  assert_contains "$output" "$STICKY_HOOK"
  [ "$(printf '%s\n' "$output" | grep -c '^\[\[on-window-detected\]\]')" -eq 2 ]
  assert_contains "$output" "if.app-id = 'com.example.Chat'"
  assert_contains "$output" "if.window-title-regex-substring = '[Cc]alendar'"
  assert_contains "$output" "run = 'move-node-to-workspace S'"
}
