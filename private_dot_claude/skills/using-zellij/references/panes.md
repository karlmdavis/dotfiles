# Driving panes and tabs from the shell

The commands are the ones in the skill's core table, checked on Zellij 0.46.0.
Use them as written; if one fails, follow "When a command here fails" in `SKILL.md`.

## Find the right pane

```bash
zellij action list-panes -t -c -s
```

- Your own pane is `terminal_$ZELLIJ_PANE_ID`.
    "The pane next to this one" is another terminal pane in the same tab as yours.
    If more than one fits, ask which.
- Look at the `COMMAND` column before typing into a pane.
    Characters go to whatever program is there, so a shell command belongs only in a pane sitting
    at a shell prompt.

## Type into a pane that is already open

```bash
zellij action write-chars --pane-id terminal_3 'hx README.md'
zellij action send-keys --pane-id terminal_3 "Enter"
```

- Sending text and pressing Enter are separate commands.
- `send-keys` takes key names: `"Enter"`, `"Ctrl c"`, `"Esc"`.
- The panes' shell is nushell, so write nushell syntax, or start the line with `zsh -lc '…'`.

## Open a new pane

```bash
zellij run --near-current-pane --no-focus --direction down --name review -- /opt/homebrew/bin/hx README.md
```

- `--near-current-pane` puts it in your tab, next to your pane.
    Without it the pane opens wherever the user's focus is, which may be another tab.

- It prints the new pane's id (`terminal_<n>`).
    Use that id for every later step, never a guessed one.
- `--direction down` or `right` makes a split; `--stacked` stacks it with the current pane;
    `--floating` floats it; `--cwd <dir>` sets its directory.
- The command does not get the login `PATH` and is not run through a shell.
    Use absolute paths, or wrap it as `-- zsh -lc '<command>'`.
- `--no-focus` leaves the user's cursor where it was.
    Without it the new pane takes focus, and in a stack your own pane collapses to its title bar
    while the user is reading it.
- When the command exits, the pane stays open showing its exit status.
    Avoid `--close-on-exit` unless nobody needs the output: a command that fails at once then takes
    its error message with it, and the pane is simply gone.
- For a shell the user and you will share, open `-- zsh -l` and type into it, so it stays open
    between commands.
- A new tab instead: `zellij action new-tab --name <name> --cwd <dir> -- <command>`, which prints
    the tab's id.

## Read a pane

```bash
zellij action dump-screen --pane-id terminal_3          # What is visible now.
zellij action dump-screen --pane-id terminal_3 --full   # Including scrollback.
```

- This works on a pane collapsed in a stack.
- Pipe it through `tail` or `grep`; a full scrollback can be long.
- To wait for a prompt, poll until the expected text appears; a slow tool's first start can take
    over a minute before printing anything.

## Afterwards

- Close only panes you opened (`zellij action close-pane --pane-id terminal_<n>`).
    If the point was to show the user something, leave it open and say that it is.
- List the panes again to confirm the result, and when the pane was for the user's eyes, ask
    whether they can see it.
    Two past sessions reported a pane as shown when it had already closed.

## Other traps

- **Worktree-isolated sessions.**
    Claude Code's worktree guard has refused compound `zellij` commands, such as ones that mix in a
    shell name or build pane ids from variables in a loop.
    Send one plain command per call with literal pane ids.
- **Prompts that spend money or change data.**
    When a shared pane asks a consequential question, the user answers it, not you.
- **Other sessions.**
    `zellij --session <name> action …` reaches another session.
    Reading from it is fine; typing into it or rearranging it needs the user's request.
