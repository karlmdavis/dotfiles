#!/usr/bin/env bats
#
# Tests for the `modify_settings.json` chezmoi script.
#
# The script must be a no-op when the live ~/.claude/settings.json differs from
# the committed settings only by key order (so Claude Code's runtime reordering
# doesn't cause perpetual `chezmoi diff` noise), must revert to the committed
# settings when any managed value actually differs ("chezmoi wins"), must carry
# runtime-owned keys (e.g. `model`, written by `/model`) through from the live
# file, and must union (not replace) list values from the machine-local overlay.

setup() {
  REPO="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
  SRC="$REPO/private_dot_claude/modify_settings.json.tmpl"

  if ! command -v chezmoi >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
    skip "requires chezmoi and jq"
  fi

  # Render the templated modify_ script to a runnable shell script.
  SCRIPT="$BATS_TEST_TMPDIR/modify_settings"
  chezmoi execute-template < "$SRC" > "$SCRIPT"

  # Point the machine-local overlay at a nonexistent file so the tests never read
  # the host's real ~/.claude/settings.local.json.
  export CLAUDE_SETTINGS_LOCAL="$BATS_TEST_TMPDIR/no-such-overlay.json"

  # The committed ("desired") settings are what the script emits for empty stdin.
  DESIRED="$(printf '' | sh "$SCRIPT")"
}

# Run the script with the given overlay JSON and empty stdin; print the output.
run_with_overlay() {
  printf '%s' "$1" > "$BATS_TEST_TMPDIR/overlay.json"
  CLAUDE_SETTINGS_LOCAL="$BATS_TEST_TMPDIR/overlay.json" sh "$SCRIPT" </dev/null
}

@test "empty input yields valid committed settings JSON" {
  run sh "$SCRIPT" </dev/null
  [ "$status" -eq 0 ]
  printf '%s' "$output" | jq -e . >/dev/null
}

@test "key reordering is emitted unchanged (no diff)" {
  # Same data, keys sorted -> a different byte order than the committed file.
  printf '%s' "$DESIRED" | jq -S . > "$BATS_TEST_TMPDIR/reordered.json"
  reordered="$(cat "$BATS_TEST_TMPDIR/reordered.json")"
  [ "$reordered" != "$DESIRED" ]   # sanity: the order really did change

  run sh "$SCRIPT" < "$BATS_TEST_TMPDIR/reordered.json"
  [ "$output" = "$reordered" ]     # live bytes passed through untouched
}

@test "a changed value is reverted to the committed settings" {
  printf '%s' "$DESIRED" | jq '.cleanupPeriodDays = 1' > "$BATS_TEST_TMPDIR/changed.json"

  run sh "$SCRIPT" < "$BATS_TEST_TMPDIR/changed.json"
  # Output equals the committed settings, not the changed input.
  [ "$(printf '%s' "$output" | jq -S .)" = "$(printf '%s' "$DESIRED" | jq -S .)" ]
  [ "$(printf '%s' "$output" | jq .cleanupPeriodDays)" = "$(printf '%s' "$DESIRED" | jq .cleanupPeriodDays)" ]
}

@test "malformed input falls back to the committed settings" {
  printf 'not json' > "$BATS_TEST_TMPDIR/bad.json"

  run sh "$SCRIPT" < "$BATS_TEST_TMPDIR/bad.json"
  [ "$(printf '%s' "$output" | jq -S .)" = "$(printf '%s' "$DESIRED" | jq -S .)" ]
}

# --- runtime-owned keys -----------------------------------------------------

@test "a runtime-owned key (model) in the live file is passed through unchanged" {
  printf '%s' "$DESIRED" | jq '.model = "claude-fable-5-1[1m]"' > "$BATS_TEST_TMPDIR/with-model.json"
  with_model="$(cat "$BATS_TEST_TMPDIR/with-model.json")"

  run sh "$SCRIPT" < "$BATS_TEST_TMPDIR/with-model.json"
  [ "$output" = "$with_model" ]    # live bytes passed through untouched
}

@test "a runtime-owned key survives when a managed value is reverted" {
  printf '%s' "$DESIRED" | jq '.model = "claude-fable-5-1[1m]" | .cleanupPeriodDays = 1' \
    > "$BATS_TEST_TMPDIR/model-and-change.json"

  run sh "$SCRIPT" < "$BATS_TEST_TMPDIR/model-and-change.json"
  [ "$(printf '%s' "$output" | jq -r .model)" = "claude-fable-5-1[1m]" ]
  [ "$(printf '%s' "$output" | jq .cleanupPeriodDays)" = "$(printf '%s' "$DESIRED" | jq .cleanupPeriodDays)" ]
}

@test "a runtime-owned key is not invented when absent from the live file" {
  run sh "$SCRIPT" </dev/null
  [ "$(printf '%s' "$output" | jq 'has("model")')" = "false" ]
}

@test "a key that is not runtime-owned is still stripped" {
  printf '%s' "$DESIRED" | jq '.theme = "dark"' > "$BATS_TEST_TMPDIR/with-theme.json"

  run sh "$SCRIPT" < "$BATS_TEST_TMPDIR/with-theme.json"
  [ "$(printf '%s' "$output" | jq 'has("theme")')" = "false" ]
}

# --- machine-local overlay --------------------------------------------------

@test "overlay list entries are appended to the committed list" {
  out="$(run_with_overlay '{"permissions":{"allow":["Bash(virsh list:*)"]}}')"

  expected="$(printf '%s' "$DESIRED" | jq -c '.permissions.allow + ["Bash(virsh list:*)"]')"
  [ "$(printf '%s' "$out" | jq -c .permissions.allow)" = "$expected" ]
}

@test "overlay list entries already in the committed list are not duplicated" {
  first="$(printf '%s' "$DESIRED" | jq -c '.permissions.allow[0]')"
  out="$(run_with_overlay "{\"permissions\":{\"allow\":[$first]}}")"

  [ "$(printf '%s' "$out" | jq -c .permissions.allow)" = "$(printf '%s' "$DESIRED" | jq -c .permissions.allow)" ]
}

@test "the legacy empty-lists overlay does not wipe the committed lists" {
  out="$(run_with_overlay '{"permissions":{"allow":[],"deny":[],"ask":[]}}')"

  [ "$(printf '%s' "$out" | jq -c .permissions.allow)" = "$(printf '%s' "$DESIRED" | jq -c .permissions.allow)" ]
  [ "$(printf '%s' "$out" | jq -c .permissions.deny)" = "$(printf '%s' "$DESIRED" | jq -c .permissions.deny)" ]
}

@test "overlay scalars replace committed scalars" {
  out="$(run_with_overlay '{"tui":"classic"}')"

  [ "$(printf '%s' "$out" | jq -r .tui)" = "classic" ]
  # Sibling managed keys are untouched.
  [ "$(printf '%s' "$out" | jq .cleanupPeriodDays)" = "$(printf '%s' "$DESIRED" | jq .cleanupPeriodDays)" ]
}

@test "overlay nested objects merge recursively" {
  out="$(run_with_overlay '{"voice":{"mode":"toggle"}}')"

  [ "$(printf '%s' "$out" | jq -r .voice.mode)" = "toggle" ]
  [ "$(printf '%s' "$out" | jq .voice.enabled)" = "$(printf '%s' "$DESIRED" | jq .voice.enabled)" ]
}

@test "overlay JSONC line comments are ignored" {
  out="$(run_with_overlay '// a comment
{
  // another
  "tui": "classic"
}')"

  [ "$(printf '%s' "$out" | jq -r .tui)" = "classic" ]
}
