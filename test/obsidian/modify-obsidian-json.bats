#!/usr/bin/env bats
#
# Tests for the `modify_obsidian.json` chezmoi script.
#
# Requirements the script must meet (each has at least one test below):
#   1. Turn on `cli`, whether it is missing or false.
#   2. When `cli` is already on, emit the live bytes unchanged, so Obsidian's own
#      rewrites never cause `chezmoi diff` noise.
#   3. Leave every other key (notably the vault list) intact.
#   4. With no file yet, create one with just `cli` on.
#
# Assertion style: bats may run under the system bash 3.2, where a failing `[[ ]]`
# that isn't a test's last command is silently ignored. Use `[ ]`.

bats_require_minimum_version 1.5.0

setup() {
  REPO="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
  SCRIPT="$REPO/private_Library/private_Application Support/private_obsidian/modify_obsidian.json"

  # jq is in the system package manifest, so a missing one is a broken machine: fail
  # rather than skip, or the pre-commit hook would pass with zero assertions run.
  command -v jq >/dev/null 2>&1 || { echo "requires jq" >&2; return 1; }
}

modify() {
  printf '%s' "$1" | sh "$SCRIPT"
}

@test "turns cli on when it is missing" {
  run -0 modify '{"vaults":{}}'
  [ "$output" = '{"vaults":{},"cli":true}' ]
}

@test "turns cli on when it is false" {
  run -0 modify '{"vaults":{},"cli":false}'
  [ "$output" = '{"vaults":{},"cli":true}' ]
}

@test "emits the live bytes unchanged when cli is already on" {
  live='{ "cli": true,
  "vaults": {"a1": {"path": "/x", "ts": 1, "open": true}} }'
  run -0 modify "$live"
  [ "$output" = "$live" ]
}

@test "keeps the vault list intact" {
  run -0 modify '{"vaults":{"a1":{"path":"/Users/me/notes","ts":1772556762956,"open":true}}}'
  [ "$(printf '%s' "$output" | jq -c '.vaults')" = '{"a1":{"path":"/Users/me/notes","ts":1772556762956,"open":true}}' ]
  [ "$(printf '%s' "$output" | jq '.cli')" = 'true' ]
}

@test "creates the file with just cli on when there is none" {
  run -0 modify ''
  [ "$output" = '{"cli":true}' ]
}
