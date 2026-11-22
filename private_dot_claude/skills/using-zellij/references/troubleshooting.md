# Troubleshooting

Each entry records what was actually seen to work, and what was tried and did not, with the
  version it was seen on.
Commands are examples from that version; confirm them with `--help` on the installed one.
Whatever the fault, a fix counts as working only when the user says so.

## A session attaches to a blank screen, or a pane is squeezed to one row

Seen on 0.44.3 after a session was resurrected.

Diagnose from another session:

```bash
zellij --session <name> action list-panes --json --all   # Look at pane_rows and pane_content_rows.
zellij --session <name> action dump-layout
zellij --session <name> action dump-screen --pane-id terminal_<n>
```

Also read the log (see [sessions.md](sessions.md) for its path).

- Worked: `zellij --session <name> action next-swap-layout --tab-id <id>`, which forces the tab to be
    laid out again.
- Did not work: `toggle-fullscreen --pane-id` on a tab with a single pane.
- Tabs resurrected from an empty `tab { }` block come back without the tab bar and status bar; the
    saved layout was already damaged, so recreate the tab.

## The mouse stops working in one tab or window

- Worked: close that iTerm2 tab, open a new one, and attach to the same session again.
- Did not work: re-sending mouse-enable escape sequences to the terminal, and `reset`.
    iTerm2 reporting that mouse reporting is on does not show that it works.

## A Zellij key stops working in one window

Seen with the lock key.
The config was correct and the key worked in a new window.

- Worked: detach and attach again from a new window.
- Did not work: `reset`.

## A key does nothing inside a program

Zellij handles its own bindings before passing keys to the pane.

- List what is bound: the live config, plus the installed version's default keybindings
    (`zellij setup --help` says how to print them; on 0.46.0 it is `--dump-keybinds default`, where
    earlier versions printed them with `--dump-config`).
- `Alt Left` and `Alt Right` are already unbound in the config for this reason.
    Zellij 0.45 read only the first global `unbind` node, so further keys went on that same line.
- A known overlap: `Ctrl g` is Zellij's default lock key and Claude Code's external-editor key.

## A session was resurrected and then disappeared

Upstream bug zellij-org/zellij#5889, still open at 0.46.0: a resurrected session that has had no
  input can be deleted when the client switches to another session.
After resurrecting a session, type in it before switching away.

## A pane opened from the CLI is not there

See the traps in [panes.md](panes.md): the command exited at once and the pane closed with it, the
  command was not found because the pane lacks the login `PATH`, or the pane id was wrong.
