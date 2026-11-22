# Sessions: inspecting, ending, and creating them, and Zellij's files

The commands up to "Ending and creating sessions" only read state.
None of them changes a session, so they are safe to run against any session, including ones
  holding other people's live work, without asking first.
The commands were checked on Zellij 0.46.0; use them as written, and if one fails, follow "When a
  command here fails" in `SKILL.md`.
The file layout is what 0.46.0 uses and has changed before, so confirm a path by looking (`ls`, or
  the socket path in each server's command line) before building on it.

## What is running

```bash
zellij list-sessions -n
```

- `-n` (`--no-formatting`) drops the color codes; always use it when parsing.
- Exited sessions are marked `(EXITED - attach to resurrect)`; the rest are running.
- Piping the output into `head` can make Zellij panic with a broken pipe.
    Capture it in a variable or a file and cut it down afterwards.

Any session can be queried from outside it:

```bash
zellij --session <name> action list-clients
zellij --session <name> action list-tabs --json --all
zellij --session <name> action list-panes --json --all
zellij --session <name> action dump-layout
zellij --session <name> action dump-screen --pane-id terminal_<n> --full
```

These need no terminal and have not been seen to hang, so don't wrap them in timeouts.
Each one probes every session's socket, so with dozens of sessions a call takes a few hundred
  milliseconds.
A few actions, such as `current-tab-info` and `override-layout`, act on an attached client's active
  tab and do nothing useful for a session nobody is attached to.

## Processes

- Each running session is one `zellij --server <socket path>` process with no terminal; the last
    path component is the session's name (or, for sessions created by 0.46 and later, its id).
- Each attached terminal is a separate client process (`zellij -l welcome`, `zellij attach …`).
- To see which binary a long-running server is using after an upgrade:
    `lsof -a -p <pid> -d txt -Fn | grep Cellar/zellij`.

## Which Claude Code session is in which pane

- `list-panes -c` shows each pane's command; a pane running Claude Code shows the `claude` command
    line, including `--resume <session id>` when it was resumed.
    The column is not proof that it is running: a pane in a resurrected session shows its saved
    command while still waiting at "Waiting to run … <ENTER> run".
    Confirm with `dump-screen` on that pane, or by finding the process.
- `~/.claude/sessions/<pid>.json` records each running Claude Code process's `sessionId`, `name`,
    `cwd`, and `status`.
- Walk a `claude` process's parents (`ps -o ppid=`) up to a `zellij --server` process to learn its
    Zellij session.
- Background sessions run by the Claude daemon are not children of any Zellij server.
    The pane only holds a `claude agents` view of them, and they outlive the pane.

## Files

| What | macOS | Linux |
| --- | --- | --- |
| Cache | `~/Library/Caches/org.Zellij-Contributors.Zellij/` | `~/.cache/zellij/` |
| Sockets | `$TMPDIR/zellij-<uid>/contract_version_1/` | Read it from a server's command line. |
| Log | `$TMPDIR/zellij-<uid>/zellij-log/zellij.log` | Not checked on these machines. |
| Config | `~/.config/zellij/config.kdl` | `~/.config/zellij/config.kdl` |

The log is shared by all sessions.
`/tmp/zellij-*` is the wrong place to look on macOS; `$TMPDIR` is a per-user folder under
  `/var/folders`.

Inside the cache, `contract_version_1/session_info/<folder>/` holds one folder per session:

- `session-metadata.kdl` is rewritten about once a second while the session runs.
    It records the session's `name`, its tabs, every pane (title, `is_plugin`, size, exited), and
    `connected_clients`.
- `session-layout.kdl` is the layout used to resurrect the session, with `initial_contents_<n>` files
    for saved pane contents.
    It is rewritten only when the layout changes, so an old date on it is normal.

Two things about these folders:

- Sessions created before 0.46 have a folder named after the session.
    From 0.46 the folder is a random 12-character hex id, and `session_index.sqlite` maps names to
    ids.
    To find a session's folder, match the `name "<session>"` line at the top of each
    `session-metadata.kdl`; don't build the path from the name.
- Folders named for old versions (`0.43.1/`, `0.44.3/`) are leftovers and hold stale copies.

The file formats are internal to Zellij and undocumented, so treat anything read from them as a hint
  and prefer the `zellij action` queries when the two disagree.
`zellij-gc` follows the same rule; see `private_dot_local/lib/zellij-gc/zellij_gc/collector.py` in the
  dotfiles repo.

## Ending and creating sessions

These change things, so each needs the user's request.

- When the user asks to tidy or clean up sessions, lay out both choices in your reply, because
    they leave the chooser looking different and "clean up" could mean either:
    an exited session can only be deleted;
    a running one can be killed, which stops its programs but leaves it in the chooser as EXITED,
    or deleted with `--force`, which removes it altogether.
    Then ask which sessions, by name, and which of the two, before running anything.
- `kill-all-sessions` and `delete-all-sessions` are the user's to run, from the iTerm2 `zsh` profile
    (a shell outside Zellij), because they also end your own session mid-command.
- Never interrupt a delete once it has started.
- `~/.local/bin/zellij-gc` deletes abandoned sessions for real; `zellij-gc --dry-run` only looks.
- For experiments, create throwaway sessions with an obvious name such as `zz-probe-<something>`,
    and delete only those afterwards.
- To create a session from a script or the Bash tool, use
    `zellij attach --create-background <name>`, which starts it detached.
    Plain `zellij attach <name>` does not work there, because it needs a terminal to draw in.
