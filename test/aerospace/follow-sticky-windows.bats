#!/usr/bin/env bats
#
# Smoke test for the `follow-sticky-windows.py` launcher shim
# (dot_config/aerospace/executable_follow-sticky-windows.py).
#
# The package's pytest suite imports `aerospace_workspaces.sticky` directly, so it never
# exercises the shim's own seams. This drives the shim end to end, through its own
# `uv run --script` header, and pins that:
#   1. $AEROSPACE_LIB_DIR puts the source package on sys.path, so the shim imports and runs.
#   2. With a matching window on another workspace, --dry-run prints the float + move commands.
#   3. With no sticky-windows rules, it exits 0 without printing anything.
#
# `aerospace` is replaced by a fake via $AEROSPACE_BIN that answers `list-windows` with
# canned JSON and fails on anything else, so the test also proves --dry-run issues no
# mutating commands.
#
# Assertion style: bats runs under whatever `bash` is first on PATH, on macOS usually
# the system 3.2, where a failing `[[ ]]` does NOT trip errexit, so a `[[ ]]` that
# isn't a test's last command is silently ignored. Use `[ ]`, never bare `[[ ]]`.

bats_require_minimum_version 1.5.0

setup() {
  REPO="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
  SHIM="$REPO/dot_config/aerospace/executable_follow-sticky-windows.py"

  # uv runs the shim (and every embedded Python mini-project's tests), so a missing one is a
  # broken machine: fail rather than skip.
  command -v uv >/dev/null 2>&1 || { echo "requires uv" >&2; return 1; }

  export AEROSPACE_LIB_DIR="$REPO/private_dot_local/lib/aerospace-workspaces"
  export AEROSPACE_WORKSPACES_YAML="$BATS_TEST_TMPDIR/workspaces.yaml"
  export AEROSPACE_FOCUSED_WORKSPACE="B"
  export AEROSPACE_BIN="$BATS_TEST_TMPDIR/aerospace"
  export PYTHONDONTWRITEBYTECODE=1  # no __pycache__ left in the source package.

  cat > "$AEROSPACE_BIN" <<'EOF'
#!/bin/sh
case "$1" in
  list-windows)
    printf '%s\n' '[{"window-id": 42, "app-bundle-id": "com.example.Popup",' \
      '"window-title": "1 Alert", "workspace": "A", "window-layout": "h_tiles"}]'
    ;;
  *) echo "unexpected aerospace call: $*" >&2; exit 1 ;;
esac
EOF
  chmod +x "$AEROSPACE_BIN"
}

run_shim() {
  uv run --quiet --script "$SHIM" "$@"
}

@test "the shim imports the package via AEROSPACE_LIB_DIR and plans float + move" {
  printf '%s\n' 'sticky-windows:' '  - app-id: com.example.Popup' "    title-regex: 'Alert'" \
    > "$AEROSPACE_WORKSPACES_YAML"
  run --separate-stderr run_shim --dry-run
  [ "$status" -eq 0 ] || { echo "exit $status: $stderr" >&2; return 1; }
  [ "${lines[0]}" = "aerospace layout --window-id 42 floating" ] \
    || { echo "unexpected output: $output" >&2; return 1; }
  [ "${lines[1]}" = "aerospace move-node-to-workspace --window-id 42 B" ] \
    || { echo "unexpected output: $output" >&2; return 1; }
  [ "${#lines[@]}" -eq 2 ]
}

@test "with no sticky-windows rules the shim is a silent no-op" {
  printf '%s\n' 'workspaces: {}' > "$AEROSPACE_WORKSPACES_YAML"
  run --separate-stderr run_shim --dry-run
  [ "$status" -eq 0 ] || { echo "exit $status: $stderr" >&2; return 1; }
  [ -z "$output" ] || { echo "expected no output, got: $output" >&2; return 1; }
}
