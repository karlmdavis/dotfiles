#!/usr/bin/env bats
#
# Tests for the `modify_settings.json` chezmoi script.
#
# The script must be a no-op when the live ~/.claude/settings.json differs from
# the committed settings only by key order (so Claude Code's runtime reordering
# doesn't cause perpetual `chezmoi diff` noise), and must revert to the committed
# settings when any value actually differs ("chezmoi wins").

setup() {
  REPO="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
  SRC="$REPO/private_dot_claude/modify_settings.json.tmpl"

  if ! command -v chezmoi >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
    skip "requires chezmoi and jq"
  fi

  # Render the templated modify_ script to a runnable shell script.
  SCRIPT="$BATS_TEST_TMPDIR/modify_settings"
  chezmoi execute-template < "$SRC" > "$SCRIPT"

  # The committed ("desired") settings are what the script emits for empty stdin.
  DESIRED="$(printf '' | sh "$SCRIPT")"
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
