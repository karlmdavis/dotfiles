---
name: using-zellij
description: Use for anything involving Zellij, the terminal multiplexer every terminal here runs in - opening, typing into, or reading another pane or tab; listing, inspecting, killing, or resurrecting sessions; answering keybinding, layout, or config questions; diagnosing a stuck pane, dead mouse, or swallowed key; upgrading Zellij; or touching the zellij-welcome launcher or zellij-gc collector. Use it even when the user doesn't say "Zellij" but asks to show or run something "in a new pane", "in the pane next to this one", or "in another tab", and before running any zellij command, because it gives the command forms that work here and several commands end live sessions.
---

# Using Zellij

Every terminal on these machines is nushell inside a Zellij session, so you are almost certainly
  running inside one right now, next to other sessions that hold live work.

## Orient

Run this before any other Zellij command.

```bash
zellij --version; echo "ZELLIJ=${ZELLIJ-unset} session=$ZELLIJ_SESSION_NAME pane=$ZELLIJ_PANE_ID"
```

- `ZELLIJ` is set to `0` inside a session, so test whether it is set, not whether it is truthy.
- `ZELLIJ_SESSION_NAME` is the session you live in; actions aimed at it affect you and the user's
    view of you.
- `ZELLIJ_PANE_ID` is a bare number; the CLI names your pane `terminal_<n>`.

## Core commands

These were checked on Zellij 0.46.0 and have kept the same shape since 0.44.
Use them as written, without reading their help first.

| To | Run |
| --- | --- |
| List sessions | `zellij list-sessions -n` |
| List this session's panes | `zellij action list-panes -t -c -s` |
| List another session's panes | `zellij --session <name> action list-panes -t -c -s` |
| Count a session's attached clients | `zellij --session <name> action list-clients` |
| Open a pane beside yours, without taking focus | `zellij run --near-current-pane --no-focus --direction down --name <name> -- <command>` |
| Type into a pane | `zellij action write-chars --pane-id terminal_<n> '<text>'` |
| Press a key in a pane | `zellij action send-keys --pane-id terminal_<n> "Enter"` |
| Read a pane's screen | `zellij action dump-screen --pane-id terminal_<n>` (add `--full` for scrollback) |
| Close a pane you opened | `zellij action close-pane --pane-id terminal_<n>` |
| Default keybindings | `zellij setup --dump-keybinds default \| grep -n -i <word>` |
| Check a config file | `zellij --config <file> setup --check` |

## When a command here fails, or you need one not listed

Zellij changes quickly, so a command in this skill can go stale.

1. Read the help for that one command (`zellij <command> --help` or
    `zellij action <command> --help`) and use what the installed version says.
    To find a command you don't know the name of, search the list:
    `zellij action --help | grep -i <word>`.
2. If a command or flag written in this skill was wrong for the installed version, tell the user in
    your reply, even though you worked around it: which file and command, what the installed
    version (`zellij --version`) expects instead, and that the skill needs updating.
    Its source is `private_dot_claude/skills/using-zellij/` in the dotfiles repo
    (`~/.local/share/chezmoi`).
    Without that note the next session hits the same error.

Never answer a flag, key, or path from memory when this skill and the help don't cover it; ask the
  binary.

## Keep lookups small

Help and dump output is large, and it stays in context for the rest of the session.

- Search with `grep` or `jq`; don't print whole listings.
    `zellij action --help` and `zellij setup --dump-keybinds default` are about 3,000 tokens each,
    `list-panes --json --all` is larger, and `zellij setup --dump-config` is about 10,000.
- For a job that needs a lot of raw output, such as an inventory of every session's tabs and panes
    or a survey of keybindings, do the collecting in a subagent and have it return only the answer.
    For a single pane or a single key, a subagent costs far more than it saves.

## Sessions hold live work

Other sessions usually contain running Claude Code conversations and long-lived shells.

- `zellij kill-session <name>` ends everything running in a session but keeps its saved layout, so
    it shows as EXITED and can be resurrected.
- `zellij delete-session <name>` removes a session's saved layout for good; with `--force` it also
    kills a running one first.
- When the user asks to tidy sessions, say which of the two you mean and ask which sessions, by
    name, before running either.
- `kill-all-sessions` and `delete-all-sessions` are the user's to run, from the iTerm2 `zsh` profile
    (a shell outside Zellij), because they also end your own session mid-command.
- Never interrupt a delete once it has started.
- `~/.local/bin/zellij-gc` deletes abandoned sessions for real; `zellij-gc --dry-run` only looks.
- For experiments, create throwaway sessions with an obvious name such as `zz-probe-<something>`,
    and delete only those afterwards.
- Reading another session is fine; typing into it or rearranging it needs the user's request.

## Check that it happened

An exit status of 0 proves little with Zellij.
A wrong pane id is accepted silently, an action without `--pane-id` goes to whichever pane has focus
  (usually your own), and a pane whose command exits at once can close at once.
After acting, list the panes again and look.
When the point was for the user to see something, or a fix was meant to change what they see, ask
  them before calling it done.

## References

Read the one that fits the task.

- Showing or running something in another pane or tab:
    [references/panes.md](references/panes.md).
- What sessions, panes, and Claude Code sessions exist, and where Zellij keeps its files:
    [references/sessions.md](references/sessions.md).
- A pane squeezed to nothing, a blank session, a dead mouse, or a key that stopped working:
    [references/troubleshooting.md](references/troubleshooting.md).
- Upgrading Zellij while sessions are running:
    [references/upgrading.md](references/upgrading.md).

## Keybinding, layout, and config questions

- The config (`~/.config/zellij/config.kdl`) is close to default: a theme, session serialization,
    nushell as the default shell, no nested-session prompt, and one `unbind` of `Alt Left` and
    `Alt Right`.
    So the default preset applies apart from those two keys.
    Read the file (it is short) in case this has changed.
- Look a key up in the default preset with the command in the table, searching for the action
    (`Lock`, `SwapLayout`, `NewPane`, `Resize`); never name a key from memory.
    In the dump, `{primary}` is `Ctrl` and `{secondary}` is `Alt`, and each binding sits inside the
    mode it applies in, so give the mode with the key.
- Swap layouts (`Alt [` and `Alt ]`) cycle through presets, not through a history of earlier
    layouts, and no preset makes a stack out of two panes.
    To stack existing panes: `zellij action stack-panes -- terminal_<a> terminal_<b>`.
- Zellij handles its own bindings before the program in the pane sees a key.
    When a key "does nothing" in nushell, Helix, or Claude Code, look for it in Zellij's bindings
    first (`Ctrl g` is both Zellij's lock key and Claude Code's external-editor key).
- Edit the chezmoi source, `dot_config/zellij/config.kdl.tmpl` in the dotfiles repo, not the file in
    `~`.
    Keybinding changes have applied to running sessions without a restart.

## How this setup launches Zellij

Login shells exec the session chooser through `~/.local/bin/zellij-welcome`, which first runs the
  `zellij-gc` collector.
The dotfiles repo's `CLAUDE.md` ("Auto-launching Zellij") and
  `private_dot_local/lib/zellij-gc/CLAUDE.md` are the write-ups; read them before changing either.

- `NO_ZELLIJ=1` in the environment skips the launcher; set it when testing login shells
    (`NO_ZELLIJ=1 zsh -lic '<command>'`), or the test lands in the chooser.
- Over non-interactive SSH to the Linux machines, `zellij` is not on `PATH`; call
    `/home/linuxbrew/.linuxbrew/bin/zellij`.
