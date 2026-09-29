# zellij-gc

Closing a terminal at the Zellij welcome chooser leaves its session running until the machine
  restarts.
`~/.local/bin/zellij-welcome` (source: `private_dot_local/bin/executable_zellij-welcome`) runs
  `~/.local/bin/zellij-gc` on every launch, before it opens the chooser, to delete such sessions.
`zellij-gc` is a thin shim (source: `private_dot_local/bin/executable_zellij-gc`) over the `zellij_gc`
  package in this directory.

- It deletes only sessions that are running, have no clients and no terminal panes, show nothing
    but the welcome screen, and are older than `ZELLIJ_GC_MIN_AGE_HOURS` (default 1).
    A session's name plays no part, and EXITED (resurrectable) sessions are never touched.
- Every doubt keeps the session, and nothing is deleted that cannot be put on record.
- A usual launch shows nothing.
    One with sessions to look into names each on the terminal as it goes, and Ctrl-C skips the rest.
- What it did is recorded under `~/.local/state/zellij-gc/` (or `$XDG_STATE_HOME/zellij-gc/`):
    `gc.log` for every run, and `last-failure.log` for the most recent run that failed.
- Preview with `zellij-gc --dry-run`, which also says why each other session would be kept.
- Disable real runs by setting `ZELLIJ_GC_DISABLE` to any non-empty value; the preview still works.

How it decides, and why it is built as it is, is set out in `zellij_gc/collector.py`.

The tests are in `tests/` here, and those for the wrapper are in `test/zellij/` at the repo root.
Run both, with the linters, by `mise run ci` from the repo root.
