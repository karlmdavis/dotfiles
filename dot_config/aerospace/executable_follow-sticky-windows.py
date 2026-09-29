#!/usr/bin/env -S /opt/homebrew/bin/uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Sticky windows (thin launcher shim).

Called from `exec-on-workspace-change` in ~/.aerospace.toml, which only wires it in on machines
whose ~/.config/aerospace/workspaces.yaml declares `sticky-windows:` rules.

Floats every matching window and moves it onto the newly focused workspace, emulating the
show-on-all-workspaces option AeroSpace lacks. The real logic lives in the shared
`aerospace_workspaces` package; pass `--dry-run` to print the would-be `aerospace` commands instead.
"""

import os
import sys

# This is invoked by absolute path (not as an installed module), so the shared package isn't
# importable by default — we add its directory to sys.path explicitly. $AEROSPACE_LIB_DIR overrides
# it, which is also the seam the tests use to point at the source package rather than the applied
# copy. (The HUD and SwiftBar plugin shims do the same, since all three share this package.)
sys.path.insert(
    0,
    os.environ.get("AEROSPACE_LIB_DIR", os.path.expanduser("~/.local/lib/aerospace-workspaces")),
)

from aerospace_workspaces.sticky import main

if __name__ == "__main__":
    main()
