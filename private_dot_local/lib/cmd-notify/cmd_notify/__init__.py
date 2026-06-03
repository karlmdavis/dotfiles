"""cmd-notify: desktop notification when a long-running command completes.

Invoked from shell hooks (nu/bash/zsh) as
  cmd-notify [--dry-run] <command_text> <duration_seconds> <exit_code> <cwd>
via the thin shim at ~/.local/bin/cmd-notify. The logic lives here so it can be unit-tested with
pytest; `notify.main` is the entry point and `icons.resolve` handles the optional icon cache/fetch.
"""
