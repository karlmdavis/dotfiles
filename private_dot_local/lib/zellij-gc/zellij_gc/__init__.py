"""zellij-gc: garbage-collect zellij sessions abandoned at the welcome screen.

Invoked in the background by ~/.local/bin/zellij-welcome each time the welcome chooser is launched:
  zellij-gc [--dry-run]
via the thin shim at ~/.local/bin/zellij-gc. The logic lives here so it can be unit-tested with
pytest; `gc.main` is the entry point.
"""
