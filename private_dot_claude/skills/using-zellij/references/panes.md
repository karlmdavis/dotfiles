# Driving panes and tabs from the shell

The commands here are examples that worked on Zellij 0.46.0.
Before using one, find it in `zellij --help` or `zellij action --help` and read its own `--help`:
  flags have been added and renamed between versions, and newer actions may do the job better.
The lessons under each heading are what past sessions learned the hard way, and they outlast the
  flags.

## The steps, and what to look up for each

| Step | Look in the help for | 0.46.0 example |
| --- | --- | --- |
| See the panes | An action that lists panes, and its options for tab, command, and state | `zellij action list-panes -t -c -s` |
| Type into a pane | Actions that write characters, send keys, or paste | `zellij action write-chars --pane-id terminal_3 'ls'` |
| Press a key | The send-keys action | `zellij action send-keys --pane-id terminal_3 "Enter"` |
| Open a pane | The `run` command | `zellij run --no-focus --name review -- <command>` |
| Open a tab | The new-tab action | `zellij action new-tab --name review -- <command>` |
| Read a pane | An action that dumps a pane's screen | `zellij action dump-screen --pane-id terminal_3 --full` |
| Follow a pane | The `subscribe` command | `zellij subscribe --pane-id terminal_3` |
| Close a pane | The close-pane action | `zellij action close-pane --pane-id terminal_3` |

## Finding the right pane

- Your own pane is `terminal_$ZELLIJ_PANE_ID`.
    "The pane next to this one" is another terminal pane in the same tab as yours.
    If more than one fits, ask which.
- Look at what each pane is running before typing into it.
    Characters go to whatever program is there, so a shell command belongs only in a pane sitting
    at a shell prompt.

## Typing

- Name the target pane on every command.
    Without one, the action goes to the focused pane, which is usually your own.
- The panes' shell is nushell, so write nushell syntax, or start the line with `zsh -lc '…'`.
- Sending text and pressing Enter are separate actions.

## Opening

- A command started in a new pane does not get the login `PATH` and is not run through a shell.
    Use absolute paths (`/opt/homebrew/bin/hx`) or wrap it as `zsh -lc '<command>'`.
- A new pane takes focus unless told not to, and in a stack that collapses your own pane to its
    title bar while the user is reading it.
    Look in the help for an option that leaves focus alone; where the installed version has none,
    move focus back to your own pane with the focus action afterwards.
- The opening command prints the new pane's id.
    Capture it and use it for every later step, never a guessed id.
- Avoid the close-on-exit option unless nobody needs the output.
    A command that fails at once then takes its error message with it, and the pane is simply gone.
- For a shell the user and you will share, open a login shell and type into it, so that it stays
    open between commands.

## Reading and waiting

- Dumping the screen works on a pane collapsed in a stack.
- To wait for a prompt, poll the dump until the expected text appears; a first start of a slow tool
    can take over a minute before printing anything.
- A subscription runs until stopped, so start it in the background.

## Afterwards

- Close only panes you opened.
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
    A global option on `zellij` targets another session by name.
    Reading from it is fine; typing into it or rearranging it needs the user's request.
