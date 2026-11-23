#!/usr/bin/env bats
#
# Tests for the commands of the iTerm2 remote-host profiles (`karl-<host>.json`).
#
# Requirements each profile's command must meet (each has a test below):
#   1. It connects with `ssh`, not `mosh`, to that profile's own host, asking for a terminal.
#      (mosh redraws the screen from its own model and drops escape sequences it does not know,
#      so agent status and notifications from the remote zellij never reach iTerm2.)
#   2. When `ssh` ends because the connection was lost (exit status 255), it says so and
#      connects again, so the tab survives the laptop being offline.
#   3. When the remote session ends for any other reason, it stops, so the tab can close.
#
# No mocks: the command is read from the profile and run as iTerm2 would run it, against
# stand-in `ssh` and `sleep` executables that record how they were called.
#
# Assertion style: see test/claude/check-mise-usage.bats. Use `[ ]`, never bare `[[ ]]`.

bats_require_minimum_version 1.5.0

setup() {
  REPO="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
  PROFILES="$REPO/private_Library/private_Application Support/iTerm2/DynamicProfiles"
  command -v jq >/dev/null 2>&1 || { echo "requires jq" >&2; return 1; }

  export RECORD="$BATS_TEST_TMPDIR/record"
  mkdir -p "$RECORD" "$BATS_TEST_TMPDIR/bin"

  # Stand-in ssh: records each call's arguments, and exits with the next status listed in
  # $RECORD/statuses (0 once the list runs out).
  cat > "$BATS_TEST_TMPDIR/bin/ssh" <<'STUB'
#!/bin/sh
echo "$*" >> "$RECORD/ssh-calls"
calls="$(wc -l < "$RECORD/ssh-calls" | tr -d ' ')"
status="$(sed -n "${calls}p" "$RECORD/statuses" 2>/dev/null)"
exit "${status:-0}"
STUB
  # Stand-in sleep: records the wait instead of waiting.
  cat > "$BATS_TEST_TMPDIR/bin/sleep" <<'STUB'
#!/bin/sh
echo "$*" >> "$RECORD/sleeps"
STUB
  chmod +x "$BATS_TEST_TMPDIR/bin/ssh" "$BATS_TEST_TMPDIR/bin/sleep"
  PATH="$BATS_TEST_TMPDIR/bin:$PATH"
}

# Runs the command of karl-<host>.json. iTerm2 splits the command into words much as a shell
# does, so a shell stands in for it.
run_profile() {
  run sh -c "$(jq -r '.Profiles[0].Command' "$PROFILES/karl-$1.json")"
}

ssh_call_count() {
  wc -l < "$RECORD/ssh-calls" | tr -d ' '
}

@test "each remote profile connects with ssh to its own host and asks for a terminal" {
  for host in eddings mantis scaleway-mini; do
    rm -f "$RECORD/ssh-calls"
    run_profile "$host"
    [ "$status" -eq 0 ]
    [ "$(ssh_call_count)" -eq 1 ]
    grep -q -- "-t " "$RECORD/ssh-calls"
    grep -q -- "karl@$host\.tail26736d\.ts\.net\$" "$RECORD/ssh-calls"
    if grep -q mosh "$PROFILES/karl-$host.json"; then return 1; fi
  done
}

@test "a lost connection is reported and retried until ssh ends normally" {
  printf '255\n255\n0\n' > "$RECORD/statuses"
  run_profile scaleway-mini
  [ "$status" -eq 0 ]
  [ "$(ssh_call_count)" -eq 3 ]
  [ "$(wc -l < "$RECORD/sleeps" | tr -d ' ')" -eq 2 ]
  [ "${lines[0]}" = "[ssh] Connection lost; retrying in 5 seconds (Ctrl-C to give up)." ]
}

@test "a remote session that ends with its own failure status is not retried" {
  printf '1\n' > "$RECORD/statuses"
  run_profile scaleway-mini
  [ "$status" -eq 0 ]
  [ "$(ssh_call_count)" -eq 1 ]
  [ ! -e "$RECORD/sleeps" ]
}
