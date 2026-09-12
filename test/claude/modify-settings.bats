#!/usr/bin/env bats
#
# Tests for the `modify_settings.json` chezmoi script.
#
# The script must be a byte-exact no-op when the live ~/.claude/settings.json
# differs from the committed settings only by key order (so Claude Code's runtime
# reordering doesn't cause perpetual `chezmoi diff` noise), must revert to the
# committed settings when any managed value actually differs ("chezmoi wins"),
# must carry runtime-owned keys (e.g. `model`, written by `/model`) through from
# the live file, and must union (not replace) list values from the machine-local
# overlay. A broken overlay must fail loudly, naming the overlay file, rather
# than silently dropping settings.

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

# Write the given overlay text to a file and point the script at it.
use_overlay() {
  printf '%s' "$1" > "$BATS_TEST_TMPDIR/overlay.json"
  export CLAUDE_SETTINGS_LOCAL="$BATS_TEST_TMPDIR/overlay.json"
}

# Run the script with the given overlay and empty stdin; print the output.
run_with_overlay() {
  use_overlay "$1"
  sh "$SCRIPT" </dev/null
}

sorted() { printf '%s' "$1" | jq -S .; }

# --- baseline ----------------------------------------------------------------

@test "empty input yields valid committed settings JSON" {
  run sh "$SCRIPT" </dev/null
  [ "$status" -eq 0 ]
  printf '%s' "$output" | jq -e . >/dev/null
}

@test "committed output ends with a trailing newline (matches Claude Code's writer)" {
  sh "$SCRIPT" </dev/null > "$BATS_TEST_TMPDIR/out.json"
  [ "$(tail -c 1 "$BATS_TEST_TMPDIR/out.json" | od -An -c | tr -d ' ')" = '\n' ]
}

@test "key reordering is emitted unchanged (no diff)" {
  # Same data, keys sorted -> a different byte order than the committed file.
  printf '%s' "$DESIRED" | jq -S . > "$BATS_TEST_TMPDIR/reordered.json"
  reordered="$(cat "$BATS_TEST_TMPDIR/reordered.json")"
  [ "$reordered" != "$DESIRED" ]   # sanity: the order really did change

  run sh "$SCRIPT" < "$BATS_TEST_TMPDIR/reordered.json"
  [ "$status" -eq 0 ]
  [ "$output" = "$reordered" ]
}

@test "pass-through is byte-exact, including the trailing newline" {
  # jq emits a trailing newline, as Claude Code does when it rewrites the file.
  # bats `run` and $(...) both strip trailing newlines, so compare files instead.
  printf '%s' "$DESIRED" | jq -S '.model = "claude-fable-5-1[1m]"' > "$BATS_TEST_TMPDIR/live.json"
  sh "$SCRIPT" < "$BATS_TEST_TMPDIR/live.json" > "$BATS_TEST_TMPDIR/out.json"
  cmp "$BATS_TEST_TMPDIR/live.json" "$BATS_TEST_TMPDIR/out.json"
}

@test "a changed value is reverted to the committed settings" {
  printf '%s' "$DESIRED" | jq '.cleanupPeriodDays = 1' > "$BATS_TEST_TMPDIR/changed.json"

  run sh "$SCRIPT" < "$BATS_TEST_TMPDIR/changed.json"
  [ "$status" -eq 0 ]
  [ "$(sorted "$output")" = "$(sorted "$DESIRED")" ]
  [ "$(printf '%s' "$output" | jq .cleanupPeriodDays)" = "$(printf '%s' "$DESIRED" | jq .cleanupPeriodDays)" ]
}

@test "malformed input falls back to the committed settings" {
  printf 'not json' > "$BATS_TEST_TMPDIR/bad.json"

  run --separate-stderr sh "$SCRIPT" < "$BATS_TEST_TMPDIR/bad.json"
  [ "$status" -eq 0 ]
  [ "$(sorted "$output")" = "$(sorted "$DESIRED")" ]
  [[ "$stderr" == *"not a JSON object"* ]]   # the fallback is reported, not silent
}

@test "valid-JSON-but-not-an-object input falls back to the committed settings" {
  for live in '5' '"str"' 'true' '[]' 'null'; do
    printf '%s' "$live" > "$BATS_TEST_TMPDIR/nonobject.json"
    run --separate-stderr sh "$SCRIPT" < "$BATS_TEST_TMPDIR/nonobject.json"
    [ "$status" -eq 0 ]
    [ "$(sorted "$output")" = "$(sorted "$DESIRED")" ]
    [[ "$stderr" == *"not a JSON object"* ]]
  done
}

# --- runtime-owned keys -----------------------------------------------------

@test "a runtime-owned key (model) in the live file is passed through unchanged" {
  printf '%s' "$DESIRED" | jq '.model = "claude-fable-5-1[1m]"' > "$BATS_TEST_TMPDIR/with-model.json"
  with_model="$(cat "$BATS_TEST_TMPDIR/with-model.json")"

  run sh "$SCRIPT" < "$BATS_TEST_TMPDIR/with-model.json"
  [ "$status" -eq 0 ]
  [ "$output" = "$with_model" ]
}

@test "a runtime-owned key survives when a managed value is reverted" {
  printf '%s' "$DESIRED" | jq '.model = "claude-fable-5-1[1m]" | .cleanupPeriodDays = 1' \
    > "$BATS_TEST_TMPDIR/model-and-change.json"

  run sh "$SCRIPT" < "$BATS_TEST_TMPDIR/model-and-change.json"
  [ "$status" -eq 0 ]
  [ "$(printf '%s' "$output" | jq -r .model)" = "claude-fable-5-1[1m]" ]
  [ "$(printf '%s' "$output" | jq .cleanupPeriodDays)" = "$(printf '%s' "$DESIRED" | jq .cleanupPeriodDays)" ]
}

@test "a runtime-owned key is not invented when absent from the live file" {
  run sh "$SCRIPT" </dev/null
  [ "$status" -eq 0 ]
  [ "$(printf '%s' "$output" | jq 'has("model")')" = "false" ]
}

@test "a key that is not runtime-owned is still stripped" {
  printf '%s' "$DESIRED" | jq '.theme = "dark"' > "$BATS_TEST_TMPDIR/with-theme.json"

  run sh "$SCRIPT" < "$BATS_TEST_TMPDIR/with-theme.json"
  [ "$status" -eq 0 ]
  [ "$(printf '%s' "$output" | jq 'has("theme")')" = "false" ]
}

@test "a runtime-owned key declared in the overlay beats the live value" {
  # The overlay is part of the committed side, and committed wins on conflict.
  use_overlay '{"model":"overlay-model"}'
  printf '%s' "$DESIRED" | jq '.model = "live-model"' > "$BATS_TEST_TMPDIR/live.json"

  run sh "$SCRIPT" < "$BATS_TEST_TMPDIR/live.json"
  [ "$status" -eq 0 ]
  [ "$(printf '%s' "$output" | jq -r .model)" = "overlay-model" ]
}

@test "runtime key carry-through and overlay union compose" {
  use_overlay '{"permissions":{"allow":["Bash(virsh list:*)"]}}'
  printf '%s' "$DESIRED" | jq '.model = "claude-fable-5-1[1m]" | .theme = "dark"' > "$BATS_TEST_TMPDIR/live.json"

  run sh "$SCRIPT" < "$BATS_TEST_TMPDIR/live.json"
  [ "$status" -eq 0 ]
  [ "$(printf '%s' "$output" | jq -r .model)" = "claude-fable-5-1[1m]" ]
  [ "$(printf '%s' "$output" | jq 'has("theme")')" = "false" ]
  [ "$(printf '%s' "$output" | jq -c '.permissions.allow[-1]')" = '"Bash(virsh list:*)"' ]
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

@test "overlay lists of objects (hooks) union by deep equality" {
  existing="$(printf '%s' "$DESIRED" | jq -c '.hooks.PreToolUse[0]')"
  new='{"matcher":"Write","hooks":[{"type":"command","command":"/bin/true"}]}'

  out="$(run_with_overlay "{\"hooks\":{\"PreToolUse\":[$existing,$new]}}")"
  [ "$(printf '%s' "$out" | jq '.hooks.PreToolUse | length')" -eq 2 ]
  [ "$(printf '%s' "$out" | jq -c '.hooks.PreToolUse[1]')" = "$new" ]
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

@test "overlay whole-line // comments are ignored" {
  out="$(run_with_overlay '// a comment
{
  // another
  "tui": "classic"
}')"

  [ "$(printf '%s' "$out" | jq -r .tui)" = "classic" ]
}

@test "an overlay containing only comments or whitespace is treated as empty" {
  for text in '' '   ' '// just a comment' '// one
// two
'; do
    use_overlay "$text"
    run sh "$SCRIPT" </dev/null
    [ "$status" -eq 0 ]
    [ "$(sorted "$output")" = "$(sorted "$DESIRED")" ]
  done
}

# --- broken overlays fail loudly, naming the overlay file -----------------

@test "a malformed overlay aborts and names the overlay file" {
  use_overlay '{"tui": "classic",}'

  run sh "$SCRIPT" </dev/null
  [ "$status" -ne 0 ]
  [[ "$output" == *"overlay.json"* ]]
  [[ "$output" != *'"cleanupPeriodDays"'* ]]   # nothing resembling settings was emitted
}

@test "a trailing // comment in the overlay is not supported and aborts" {
  use_overlay '{"tui": "classic" // note
}'

  run sh "$SCRIPT" </dev/null
  [ "$status" -ne 0 ]
  [[ "$output" == *"overlay.json"* ]]
}

@test "an overlay that is not a JSON object aborts instead of wiping settings" {
  for text in 'null' '[]' '"str"' '5'; do
    use_overlay "$text"
    run sh "$SCRIPT" </dev/null
    [ "$status" -ne 0 ]
    [[ "$output" == *"overlay.json"* ]]
    [[ "$output" != *'{}'* ]]
  done
}

@test "an overlay that replaces a committed object or list with another type aborts" {
  for text in '{"permissions": []}' '{"permissions": {"allow": "Bash(x)"}}' '{"voice": 5}'; do
    use_overlay "$text"
    run sh "$SCRIPT" </dev/null
    [ "$status" -ne 0 ]
    [[ "$output" == *"overlay.json"* ]]
  done
}

@test "an overlay may set a committed value to null" {
  # null is the one non-structured value allowed over a structured one: it
  # replaces (jq's `null` scalar), and Claude Code treats a null key as unset.
  out="$(run_with_overlay '{"voice": null}')"
  [ "$(printf '%s' "$out" | jq .voice)" = "null" ]
}
