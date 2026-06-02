#!/usr/bin/env -S /opt/homebrew/bin/uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Workspace-switch HUD (thin launcher shim).

Called from ~/.aerospace.toml keybindings, e.g.:
  alt-n = ['workspace N', 'exec-and-forget ~/.config/aerospace/hud-display-workspace-name.py N']
  alt-shift-n = ['move-node-to-workspace N',
                 'exec-and-forget ~/.config/aerospace/hud-display-workspace-name.py N "→ "']

Resolves the workspace id to its icon/name/hint and shows a brief Hammerspoon HUD (or an osascript
notification fallback). The real logic lives in the shared `aerospace_workspaces` package; pass
`--dry-run` to print the would-be Hammerspoon URL / notification instead of firing it.
"""

import os
import sys

# This is invoked by absolute path (not as an installed module), so the shared package isn't
# importable by default — we add its directory to sys.path explicitly. $AEROSPACE_LIB_DIR overrides
# it, which is also the seam the tests use to point at the source package rather than the applied
# copy. (The SwiftBar plugin shim does the same, since both share this package.)
sys.path.insert(
    0,
    os.environ.get("AEROSPACE_LIB_DIR", os.path.expanduser("~/.local/lib/aerospace-workspaces")),
)

from aerospace_workspaces.hud import main

if __name__ == "__main__":
    main()
