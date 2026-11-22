# Upgrading Zellij

This is the procedure used for 0.45.1 → 0.46.0 on macOS on 2026-11-22, which went cleanly.
The shape of it should hold for later upgrades.
Read the new version's release notes for anything that changes the picture, and if a command here
  fails, follow "When a command here fails" in `SKILL.md`.

## What makes it safe

- `brew upgrade zellij` replaces the binary on disk and restarts nothing.
    Every running session keeps its old server until that session ends.
- The dotfiles' package script runs `brew bundle --no-upgrade`, so `chezmoi apply` never upgrades
    Zellij on its own.
- Killing a session keeps its saved layout, and the new version resurrected layouts saved by the
    old one.

## Before

1. Read the release notes for the new version, and check whether the `zellij-gc` collector and the
    config still fit it (`zellij --config <rendered config> setup --check` with the new binary, and
    `zellij-gc --dry-run` after the upgrade).
2. Back up the session cache (`contract_version_1/` under the cache folder; see
    [sessions.md](sessions.md)) and the old binary into a dated folder under `~/.local/state/`.
3. Record what is running: sessions, their tabs and panes, and the Claude Code session in each pane
    with its directory and session id, so the user can resume each with `claude --resume <id>`.
    [sessions.md](sessions.md) says where that information comes from.

## Upgrade

```bash
HOMEBREW_NO_INSTALL_CLEANUP=1 brew upgrade zellij
```

The flag keeps the old version's files on disk while old servers are still running from them.
Afterwards, check that `zellij --version` shows the new version, that the same server processes are
  still running, and that `zellij-gc --dry-run` reports no unparsed lines.

## Cutover, which is the user's to run

It ends every program inside Zellij, including the Claude Code session doing the upgrade.

1. The user brings each Claude Code session to a stopping point and exits it.
    Background sessions run by the Claude daemon are separate; they are stopped from `claude agents`.
2. From the iTerm2 `zsh` profile (a shell outside Zellij), the user runs `zellij kill-all-sessions`.
3. The user reopens each session from the chooser, types in it before switching to another (see the
    resurrection bug in [troubleshooting.md](troubleshooting.md)), and resumes Claude Code.
4. Once no old server remains, `brew cleanup zellij` removes the old version.

## Rollback

`brew unlink zellij`, then link the backed-up binary at Homebrew's `bin/zellij`.
A lost layout can be opened from the backup with
  `zellij --layout <backup>/session_info/<folder>/session-layout.kdl -s <name>`.

## Other machines

Repeat per machine.
On Linux the cache is `~/.cache/zellij/` and Homebrew lives in `/home/linuxbrew/.linuxbrew/`.
