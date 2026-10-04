#!/usr/bin/env -S /opt/homebrew/bin/uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""SketchyBar plugin: AeroSpace workspace strip (thin launcher shim).

The real logic lives in the `aerospace_workspaces` package at ~/.local/lib/aerospace-workspaces,
shared with the SwiftBar plugin and the workspace-switch HUD. This file is just the entry point
SketchyBar runs, as the `workspaces` item's script in ~/.config/sketchybar/sketchybarrc, which
passes the colours for the strip; `--dry-run` prints the would-be `sketchybar` command instead of
running it.
"""

import os
import sys

# SketchyBar runs this by absolute path with a minimal PATH, so the shared package isn't
# pip-installed/importable by default — we put its directory on sys.path explicitly. The location
# is overridable via $AEROSPACE_LIB_DIR, which is also the seam the tests use to point at the
# source package instead of the applied copy.
sys.path.insert(
    0,
    os.environ.get("AEROSPACE_LIB_DIR", os.path.expanduser("~/.local/lib/aerospace-workspaces")),
)

from aerospace_workspaces.sketchybar import main

if __name__ == "__main__":
    main()
