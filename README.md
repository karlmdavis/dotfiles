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

## Repository Map

**Repo meta and chezmoi meta:**

```
.
├── .chezmoi.toml.tmpl           # chezmoi init prompts + auto-commit/push config
├── .chezmoidata/                # data injected into .tmpl files (e.g. package manifest)
├── .chezmoiignore               # OS-conditional skip patterns
├── .chezmoiscripts/             # run-only scripts; not installed. See .claude/rules/file-placement.md
├── .chezmoitemplates/           # shared template partials (shell-env.sh, config.nu, ...)
├── .claude/                     # agent config for this repo
│   └── rules/                   # short, decisive guidance files for agents
├── .githooks/pre-commit         # runs `mise run ci` before each commit
├── .mise.toml                   # task runner: lint, test, ci, install-hooks
├── CLAUDE.md                    # repo-level guidance for Claude Code
├── CONTRIBUTING.md
├── LICENSE
├── README.md                    # you are here
├── docs/                        # design docs and notes (see docs/README.md)
└── test/                        # bats tests
```

Everything else (the `dot_*`, `private_dot_*`, and `private_Library/` entries) is one of the
  managed configs below.

**chezmoi source-state prefixes**, used in the paths below:

- `dot_<name>` → installed to `~/.<name>`.
- `private_dot_<name>` → same, but the source is restricted to user-only read (used for
    sensitive trees: SSH, Claude config).
- `executable_<name>` → installed with the executable bit set.
- `<name>.tmpl` → rendered through Go templates (`{{ }}` interpolation, OS conditionals).

### Apps / Configs Managed

#### Shells & Prompts

- [Bash](https://www.gnu.org/software/bash/):
    [`~/.bashrc`](dot_bashrc.tmpl),
    see also: [`~/.bash_profile`](dot_bash_profile.tmpl),
    [`~/.bash_aliases`](dot_bash_aliases).
- [Nushell](https://www.nushell.sh/):
    [`~/.config/nushell/config.nu` shared partial](.chezmoitemplates/config.nu),
    see also: [per-machine local stub](.chezmoitemplates/local.nu).
- [Starship](https://starship.rs/):
    [`~/.config/starship.toml`](dot_config/starship.toml),
    see also: [lite (no-nerd-font) variant](dot_config/starship-lite.toml).
- [Zsh](https://www.zsh.org/):
    [`~/.zshrc`](dot_zshrc),
    see also: [`~/.zprofile`](dot_zprofile.tmpl),
    [`~/.zshenv`](dot_zshenv).

#### Terminal & Windowing

- [AeroSpace](https://nikitabobko.github.io/AeroSpace/guide) (macOS tiling WM):
    [`~/.aerospace.toml`](dot_aerospace.toml.tmpl).
- [Hammerspoon](https://www.hammerspoon.org/) (macOS automation):
    [`~/.hammerspoon/`](dot_hammerspoon/).
- [iTerm2](https://iterm2.com/) color schemes:
    [`~/.iterm2-color-schemes/`](dot_iterm2-color-schemes/).
- [tmux](https://github.com/tmux/tmux):
    [`~/.tmux.conf`](dot_tmux.conf).
- [Zellij](https://zellij.dev/):
    [`~/.config/zellij/`](dot_config/zellij/),
    see also: [login-shell launch helper](.chezmoitemplates/zellij-launch.sh).

#### Development Tools and Editors

- [Claude Code](https://docs.claude.com/en/docs/claude-code/overview):
    [`~/.claude/settings.json` template](private_dot_claude/modify_settings.json.tmpl),
    see also: [plugins / marketplaces / MCPs](private_dot_claude/plugins/).
- [Helix](https://helix-editor.com/):
    [`~/.config/helix/`](dot_config/helix/).
- [Vim](https://www.vim.org/):
    [`~/.vimrc`](dot_vimrc).

#### Other Tools

- [Git](https://git-scm.com/):
    [`~/.gitconfig`](dot_gitconfig.tmpl).
- [PostgreSQL psql](https://www.postgresql.org/docs/current/app-psql.html):
    [`~/.psqlrc`](dot_psqlrc).
- [Rust toolchain](https://www.rust-lang.org/) (installer only):
    [`.chezmoiscripts/run_install_rustup.sh`](.chezmoiscripts/run_install_rustup.sh).

#### System Ops

- [SSH](https://www.openssh.com/):
    [`~/.ssh/`](private_dot_ssh/).
- [System packages (Homebrew + apt)](https://brew.sh/):
    [manifest](.chezmoidata/system_packages_autoinstall.yaml),
    see also: [installer](.chezmoiscripts/run_onchange_system_packages_autoinstall.sh.tmpl).

#### Embedded Mini-Projects

Custom development authored here; each could plausibly be broken out into its own repo.

- `cmd-notify` (long-running command notifier):
    [`~/.local/bin/cmd-notify`](private_dot_local/bin/executable_cmd-notify),
    see also: [icon URL map](private_dot_local/share/cmd-notify/icons.txt),
    [tests](test/cmd-notify/).
- Custom Claude skills:
    [`private_dot_claude/skills/`](private_dot_claude/skills/).
- Custom Claude slash commands:
    [`private_dot_claude/commands/`](private_dot_claude/commands/).

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

