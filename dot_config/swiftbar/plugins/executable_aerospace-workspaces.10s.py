#!/usr/bin/env -S /opt/homebrew/bin/uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""SwiftBar plugin: AeroSpace workspace indicator (thin launcher shim).

The real logic lives in the `aerospace_workspaces` package at ~/.local/lib/aerospace-workspaces,
which the SwiftBar plugin and the workspace-switch HUD share. This file is just the entry point
SwiftBar runs every 10s (its `.10s.` filename sets the interval; an aerospace
`exec-on-workspace-change` push refreshes it instantly on switches).

The SwiftBar metadata directives below MUST live on this plugin file (SwiftBar reads them from the
file it runs), not in the package.
"""

# <swiftbar.hideAbout>true</swiftbar.hideAbout>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideLastUpdated>true</swiftbar.hideLastUpdated>
# <swiftbar.hideDisablePlugin>true</swiftbar.hideDisablePlugin>
# <swiftbar.hideSwiftBar>true</swiftbar.hideSwiftBar>

import os
import sys

# SwiftBar runs this by absolute path under launchd with a minimal PATH, so the shared package
# isn't pip-installed/importable by default — we put its directory on sys.path explicitly. The
# location is overridable via $AEROSPACE_LIB_DIR, which is also the seam the tests use to point at
# the source package instead of the applied copy.
sys.path.insert(
    0,
    os.environ.get("AEROSPACE_LIB_DIR", os.path.expanduser("~/.local/lib/aerospace-workspaces")),
)

from aerospace_workspaces.swiftbar import main

if __name__ == "__main__":
    main()
