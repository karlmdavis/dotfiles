The dotfiles of Karl M. Davis
=============================

This repo contains my dotfiles: the configuration/settings files used on the systems I login to.
I manage these files using [chezmoi](https://www.chezmoi.io/).

On a new system, run the following to install and initialize this whole setup:

    $ brew install chezmoi
    $ chezmoi init karlmdavis

That will automatically find and clone this `karlmdavis/dotfiles` repository from GitHub
  to `~/.local/share/chezmoi/` on the local system.

To push out the files in this repo to your home directory as dotfiles, run:

    $ chezmoi status
    $ chezmoi diff
    $ chezmoi apply

To manage a new file with chezmoi, run:

    $ chezmoi add <FILE>

Please note: chezmoi supports templating of files using Golang templates.
Do not edit a templated file directly, unless you want to deal with merging your changes later.
Instead, run this:

    $ chezmoi edit <FILE>

I've set chezmoi to automatically commit and push any changes to its managed files.
There's obviously a surprise vs. consistency tradeoff there, but I think it's the safer move.
See `[.chezmoi.toml.tmpl](./.chezmoi.toml.tmpl)` to adjust that, if needed.

Scripts that should run on `chezmoi apply` but should not exist as files on the target system
  (installers, dated one-time cleanup scripts, etc.) live in `.chezmoiscripts/`.
See [`.claude/rules/chezmoi-script-placement.md`](./.claude/rules/chezmoi-script-placement.md)
  for the placement rule.

## Long-Running Command Notifications

Interactive shells (nu, bash, zsh) fire a desktop notification when a command takes longer than
  `CMD_NOTIFY_THRESHOLD` seconds (default 60).
The notification shows the command (trimmed to 40 chars), success/failure, duration, and the
  current directory's basename.
Repeated runs of the same command collapse via the platform's grouping mechanism.

The helper is `~/.local/bin/cmd-notify`.
Source: `private_dot_local/bin/executable_cmd-notify`.
Shell wiring lives in `.chezmoitemplates/config.nu` (nu), `dot_bashrc.tmpl` (bash), and
  `dot_zshrc` (zsh).

Per-command icons are optional.
Edit `~/.local/share/cmd-notify/icons.txt` (`key=url`, one per line) and the helper fetches
  them lazily on first sight, caching to `~/.cache/cmd-notify/icons/`.

Disable temporarily with `CMD_NOTIFY_DISABLE=1`.
Disable per-shell by removing the relevant hook block.

Claude Code's own "needs attention" / "task done" notifications are handled by its native
  settings (`preferredNotifChannel: "iterm2_with_bell"`, mobile push, etc.), configured in
  `private_dot_claude/modify_settings.json.tmpl` — no custom hook scripts.

## License

This project is licensed under the [GNU General Public License, Version 3](./LICENSE).

