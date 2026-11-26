"""zellij-upgrade: upgrade zellij and put every session back where it was.

Run by hand as `zellij-upgrade [--dry-run] [--yes] [--force]`, via the thin shim at
~/.local/bin/zellij-upgrade. The logic lives here so it can be unit-tested with pytest;
`cli.main` is the entry point.
"""
