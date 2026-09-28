#!/usr/bin/env bats
#
# Tests for the `zellij-welcome` wrapper, and for the iTerm2 profile command that runs it.
#
# Requirements the wrapper must meet (each has at least one test below):
#   1. `--check` exits 0 without starting anything.
#   2. It hands over to `zellij -l welcome`.
#   3. It starts `zellij-gc` in the background and does not wait for it.
#   4. It still launches zellij when `zellij-gc` is not installed.
#   5. Nothing the collector prints reaches the terminal.
#   6. A collector that fails leaves its status and output in `last-failure.log`; one that
#      succeeds leaves nothing.
#
# No mocks: the wrapper runs through its own shebang in a throwaway HOME, against stand-in
# `zellij` and `zellij-gc` executables that record how they were called.
#
# Assertion style: see test/claude/check-mise-usage.bats. Use `[ ]`, never bare `[[ ]]`.

bats_require_minimum_version 1.5.0

setup() {
  REPO="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"

  export HOME="$BATS_TEST_TMPDIR/home"
  unset XDG_STATE_HOME
  STATE="$HOME/.local/state/zellij-gc"
  mkdir -p "$HOME/.local/bin" "$BATS_TEST_TMPDIR/bin"
  cp "$REPO/private_dot_local/bin/executable_zellij-welcome" "$HOME/.local/bin/zellij-welcome"
  chmod +x "$HOME/.local/bin/zellij-welcome"
  WELCOME="$HOME/.local/bin/zellij-welcome"

  # Stand-in zellij: first on PATH, so the wrapper never reaches a real one.
  export RECORD="$BATS_TEST_TMPDIR/record"
  mkdir -p "$RECORD"
  cat > "$BATS_TEST_TMPDIR/bin/zellij" <<'EOF'
#!/bin/sh
echo "$*" > "$RECORD/zellij-args"
echo "zellij stand-in ran"
EOF
  chmod +x "$BATS_TEST_TMPDIR/bin/zellij"
  export PATH="$BATS_TEST_TMPDIR/bin:/usr/bin:/bin"
}

# Install a stand-in collector whose body is the given shell text.
install_gc() {
  printf '#!/bin/sh\n%s\n' "$1" > "$HOME/.local/bin/zellij-gc"
  chmod +x "$HOME/.local/bin/zellij-gc"
}

# Wait (up to 5 seconds) for a file that a background process is expected to write.
wait_for() {
  for _ in $(seq 50); do
    [ -e "$1" ] && return 0
    sleep 0.1
  done
  echo "timed out waiting for $1" >&2
  return 1
}

@test "--check exits 0 and starts nothing" {
  install_gc 'echo ran > "$RECORD/gc-ran"'
  run "$WELCOME" --check
  [ "$status" -eq 0 ]
  [ -z "$output" ]
  sleep 0.5
  [ ! -e "$RECORD/gc-ran" ]
  [ ! -e "$RECORD/zellij-args" ]
}

@test "hands over to zellij -l welcome" {
  install_gc 'exit 0'
  run "$WELCOME"
  [ "$status" -eq 0 ]
  [ "$(cat "$RECORD/zellij-args")" = "-l welcome" ]
}

@test "starts the collector in the background without waiting for it" {
  install_gc 'sleep 2; echo "$PATH" > "$RECORD/gc-path"'
  SECONDS=0
  run "$WELCOME"
  [ "$status" -eq 0 ]
  [ "$SECONDS" -lt 2 ]
  [ ! -e "$RECORD/gc-path" ]

  wait_for "$RECORD/gc-path"
  # Homebrew's bin, where there is one, leads the collector's PATH (and only the collector's).
  for brew_bin in /opt/homebrew/bin /home/linuxbrew/.linuxbrew/bin; do
    if [ -d "$brew_bin" ]; then
      [ "$(cat "$RECORD/gc-path")" = "$brew_bin:$PATH" ]
      break
    fi
  done
}

@test "still launches zellij when the collector is not installed" {
  run "$WELCOME"
  [ "$status" -eq 0 ]
  [ "$(cat "$RECORD/zellij-args")" = "-l welcome" ]
}

@test "nothing the collector prints reaches the terminal" {
  install_gc 'echo to-stdout; echo to-stderr >&2; echo done > "$RECORD/gc-done"; exit 1'
  run "$WELCOME"
  [ "$status" -eq 0 ]
  [ "$output" = "zellij stand-in ran" ]
  wait_for "$RECORD/gc-done"
}

@test "a failed collector leaves its status and output in last-failure.log" {
  install_gc 'echo "uv: command not found" >&2; exit 127'
  run "$WELCOME"
  wait_for "$STATE/last-failure.log"
  run cat "$STATE/last-failure.log"
  [ "${#lines[@]}" -eq 2 ]
  case "${lines[0]}" in *" zellij-gc exited 127") ;; *) false ;; esac
  [ "${lines[1]}" = "uv: command not found" ]
  # Written whole and renamed into place, so no partial files are left beside it.
  [ "$(ls "$STATE")" = "last-failure.log" ]
}

@test "a successful collector leaves nothing behind" {
  install_gc 'echo noise >&2; echo done > "$RECORD/gc-done"'
  run "$WELCOME"
  wait_for "$RECORD/gc-done"
  sleep 0.3
  [ ! -e "$STATE" ]
}

@test "the iTerm2 profile command runs the wrapper" {
  command -v jq >/dev/null 2>&1 || { echo "requires jq" >&2; return 1; }
  profile="$REPO/private_Library/private_Application Support/iTerm2/DynamicProfiles/zellij.json"
  command="$(jq -r '.Profiles[0].Command' "$profile")"

  install_gc 'echo ran > "$RECORD/gc-ran"'
  # iTerm2 splits the command into words much as a shell does, so a shell stands in for it.
  run sh -c "$command"
  [ "$status" -eq 0 ]
  [ "$(cat "$RECORD/zellij-args")" = "-l welcome" ]
  wait_for "$RECORD/gc-ran"
}
