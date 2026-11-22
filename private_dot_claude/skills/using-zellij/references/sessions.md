# Inspecting sessions and Zellij's files

Everything here is read-only.
The commands are examples that worked on Zellij 0.46.0, and the file layout is what that version
  uses; both have changed before.
Confirm commands with `--help`, and confirm paths by looking (`ls`, and the socket path in each
  server's command line) before building on them.

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

## Creating sessions without a terminal

Attaching needs a terminal, so a script cannot create a session that way.
`zellij attach --help` lists an option that creates a detached session in the background instead
  (`--create-background` on 0.46.0).
