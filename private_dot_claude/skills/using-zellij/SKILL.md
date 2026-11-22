---
name: using-zellij
description: Use for anything involving Zellij, the terminal multiplexer every terminal here runs in - opening, typing into, or reading another pane or tab; listing, inspecting, killing, or resurrecting sessions; answering keybinding, layout, or config questions; diagnosing a stuck pane, dead mouse, or swallowed key; upgrading Zellij; or touching the zellij-welcome launcher or zellij-gc collector. Use it even when the user doesn't say "Zellij" but asks to show or run something "in a new pane", "in the pane next to this one", or "in another tab", and before running any zellij command, because its commands, flags, keys, and files change with nearly every release and several commands end live sessions.
---

# Using Zellij

Every terminal on these machines is nushell inside a Zellij session, so you are almost certainly
  running inside one right now, next to other sessions that hold live work.
Zellij is both a tool you can drive and the floor you are standing on.

This skill deliberately holds few commands.
Zellij changes quickly, so the installed binary's own help is the reference, and what is written
  here is the part the help cannot tell you: how to ask it, what is dangerous, and what has gone
  wrong before on this setup.

## 1. Orient

Run this before any other Zellij command.

```bash
zellij --version; echo "ZELLIJ=${ZELLIJ-unset} session=$ZELLIJ_SESSION_NAME pane=$ZELLIJ_PANE_ID"
```

- `ZELLIJ` is set to `0` inside a session, so test whether it is set, not whether it is truthy.
- `ZELLIJ_SESSION_NAME` is the session you live in.
    Killing it, or sending it layout actions, affects you and the user's view of you.
- `ZELLIJ_PANE_ID` is a bare number; the CLI names your pane `terminal_<n>`.

## 2. Ask the binary, every time

Before using a command, naming a key, or relying on a file path, look it up in the version that is
  installed.
Memory and this skill's examples are both older than the binary.

| To learn | Ask |
| --- | --- |
| What commands exist | `zellij --help` |
| What can be done to panes, tabs, and sessions | `zellij action --help` |
| A command's flags, and what it prints | `zellij <command> --help`, `zellij action <command> --help` |
| What can be dumped or checked | `zellij setup --help` |
| Whether a config file is valid | `zellij --config <file> setup --check` |
| Behavior the help doesn't cover | Upstream at the installed tag (below) |

Read the list of actions before deciding something can't be done; each release adds some, and the
  one you need may be new.
Help text often states what a command prints (a pane id, a tab id), which is what makes it
  scriptable.

For anything the help leaves open, read the source or release notes at the tag that matches
  `zellij --version`, not the website, which documents only the newest release:

```bash
gh api repos/zellij-org/zellij/releases/tags/v<version> -q .body
gh api "repos/zellij-org/zellij/contents/<path>?ref=v<version>" -q .content | base64 -d
```

Why this is a rule and not a suggestion: answers from memory have been wrong here again and again.
Agents invented shortcuts, used a `--no-focus` flag the installed version did not have yet, looked
  for cache folders by a name that 0.46 replaced with a random id, and asked for default keybindings
  with a command that had stopped printing them.

## 3. Sessions hold live work

Other sessions usually contain running Claude Code conversations and long-lived shells.

- Killing a session ends everything running in it but keeps its saved layout, so it can be
    resurrected.
    Deleting a session also destroys the saved layout.
    Check the current names of both kinds of command in `zellij --help`.
- Run a kill or delete only when the user has asked for exactly that.
    Killing all sessions also ends your own session mid-command, so that one is the user's to run,
    from the iTerm2 `zsh` profile (a shell outside Zellij).
- Never interrupt a delete once it has started.
- `~/.local/bin/zellij-gc` deletes abandoned sessions for real; `zellij-gc --dry-run` only looks.
- For experiments, create throwaway sessions with an obvious name such as `zz-probe-<something>`,
    and delete only those afterwards.
- Reading another session is fine.
    Typing into it or rearranging it needs the user's request.

## 4. Check that it happened

An exit status of 0 proves little with Zellij.
A wrong pane id is accepted silently, an action without a pane id goes to whichever pane has focus
  (usually your own), and a pane whose command exits at once can close at once.
After acting, list the panes again and look.
When the point was for the user to see something, or a fix was meant to change what they see, ask
  them before calling it done; several past "fixes" were declared from indirect evidence and were
  wrong.

## What to read next

Each reference holds the lessons for one kind of task, with commands shown as examples checked on a
  stated version.
Where an example and `--help` disagree, `--help` is right.

- Showing or running something in another pane or tab:
    [references/panes.md](references/panes.md).
- Finding out what sessions, panes, and Claude Code sessions exist, or where Zellij keeps its files:
    [references/sessions.md](references/sessions.md).
- A pane squeezed to nothing, a blank session, a dead mouse, or a key that stopped working:
    [references/troubleshooting.md](references/troubleshooting.md).
- Upgrading Zellij while sessions are running:
    [references/upgrading.md](references/upgrading.md).

## Keybinding, layout, and config questions

- Never name a key from memory.
    Read the live config (`~/.config/zellij/config.kdl`) and print the defaults that the installed
    version would apply; `zellij setup --help` says how, and the option has changed between
    versions.
    Give the mode as well as the key.
- The config here is close to default: a theme, session serialization, nushell as the default shell,
    no nested-session prompt, and one `unbind` line.
    So the default keybindings apply apart from what that line removes.
    Read the file for the current details; this summary may have aged.
- Edit the chezmoi source, `dot_config/zellij/config.kdl.tmpl` in the dotfiles repo, not the file in
    `~`, and check a rendered copy with `setup --check`.
    Keybinding changes have applied to running sessions without a restart.
- Zellij handles its own bindings before the program in the pane sees a key.
    When a key "does nothing" in nushell, Helix, or Claude Code, look for it in Zellij's bindings
    first.
- Swap layouts are presets to cycle through, not a history of earlier layouts, so cycling does not
    bring back an arrangement the user had before.

## How this setup launches Zellij

Login shells exec the session chooser through `~/.local/bin/zellij-welcome`, which first runs the
  `zellij-gc` collector.
The dotfiles repo's `CLAUDE.md` ("Auto-launching Zellij") and
  `private_dot_local/lib/zellij-gc/CLAUDE.md` are the write-ups; read them before changing either.
Two facts come up often:

- `NO_ZELLIJ=1` in the environment skips the launcher; set it when testing login shells
    (`NO_ZELLIJ=1 zsh -lic '<command>'`), or the test lands in the chooser.
- Over non-interactive SSH to the Linux machines, `zellij` is not on `PATH`; call
    `/home/linuxbrew/.linuxbrew/bin/zellij`.
