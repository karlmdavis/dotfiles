# zellij-upgrade

Upgrading Zellij ends every session, and with them every shell and Claude Code session inside.
`~/.local/bin/zellij-upgrade` upgrades Zellij with Homebrew and then puts everything back.
It is a thin shim (source: `private_dot_local/bin/executable_zellij-upgrade`) over the
  `zellij_upgrade` package in this directory.

```
zellij-upgrade [--dry-run] [--yes] [--force]
```

- It first records what is running and shows it: the Zellij sessions, the Claude Code session in
    each pane, and, with iTerm2 open, which sessions share a window and which AeroSpace workspace
    each window is on.
    It asks before ending anything (`--yes` skips the question), and does nothing when Homebrew has
    no newer Zellij (`--force` restarts everything anyway).
- Started inside Zellij, it carries on from outside it: in a new iTerm2 window of the `zsh` profile,
    or as a detached process where there is no iTerm2.
- It waits until no Claude session is mid-turn, upgrades, ends every session, and brings each back:
    in iTerm2 windows on their workspaces on a Mac with iTerm2 open, and detached in the background
    elsewhere.
    A session that does not come back is recreated from its backed-up layout.
- Each Claude session is resumed by typing into a shell in its pane: `cd` to its folder, then
    `claude <its flags> --resume <id>`.
    Claude is never made a pane's own command.
    The pane the command was started from is resumed last, and told where the report is.
- What cannot be resumed is found beforehand and listed as a problem: a session that never took a
    turn (it has no saved conversation), a pane whose title matches no single Claude session, and
    two Claude panes in one tab.
    Those panes are left at a shell.
- Everything is kept under `~/.local/state/zellij-upgrade/<time>/` (or
    `$XDG_STATE_HOME/zellij-upgrade/`): `inventory.json`, `run.log`, `report.md`, a copy of
    Zellij's saved sessions, and the binary from before the upgrade.
- The old Zellij version is removed (`brew cleanup zellij`) only when everything came back.
    Otherwise the exit status is 1 and the report says, for each pane, what to type by hand.
- Preview with `zellij-upgrade --dry-run`, which changes nothing.

iTerm2 windows are opened with the `zellij` profile but with its command replaced by
  `zellij attach <session>`, because the profile's own command always opens the chooser.

How the steps are ordered, and why, is set out in `zellij_upgrade/cli.py`; how panes are matched to
  Claude sessions is in `zellij_upgrade/inventory.py`.

The tests are in `tests/` here.
They run the real command against stand-ins for every program it calls (`tests/fake_tools.py`).
Run them, with the linters, by `mise run ci` from the repo root.
