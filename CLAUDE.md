# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Important**: Keep this file evergreen.
Avoid adding point-in-time content (current sprint goals, active branches, temporary workarounds)
  that wouldn't make sense if multiple workstreams, PRs, or branches were in progress simultaneously.
Document general principles, workflows, and architecture — not transient project state.

## Overview

This is a dotfiles repository managed by [chezmoi](https://www.chezmoi.io/), a dotfile manager that uses Go templates to handle cross-platform configurations. The repository manages shell configurations, terminal multiplexer settings, editor preferences, and system package installations across macOS and Ubuntu systems.

## Key Commands

### Chezmoi Workflow

Check what would change:
```bash
chezmoi status
chezmoi diff
```

Apply changes to home directory:
```bash
chezmoi apply
```

Edit a managed file (handles templates correctly):
```bash
chezmoi edit <FILE>
```

Add a new file to chezmoi management:
```bash
chezmoi add <FILE>
```

### Important Notes

- **Auto-commit enabled**: Chezmoi is configured to automatically commit and push changes (see `.chezmoi.toml.tmpl`)
- **Template files**: Files ending in `.tmpl` use Go templating. Always use `chezmoi edit` for templated files, never edit them directly in the home directory
- **OS-specific paths**: Nushell config has different paths on macOS vs Linux (see `.chezmoiignore` for OS-specific file application)

## Repository Architecture

### Template System

The repository uses a sophisticated template hierarchy:

1. **Primary templates** (`.chezmoitemplates/`): Shared template content that can be included by multiple files
   - `config.nu` - Main nushell configuration used by both macOS and Linux paths

2. **File templates** (`.tmpl` suffix): Individual files that use Go templating
   - Variables like `.chezmoi.os`, `.chezmoi.osRelease.id` handle OS detection
   - `.isCMS` variable distinguishes personal vs. CMS systems (prompted during init)

3. **OS-specific file handling**: `.chezmoiignore` prevents files from being applied on wrong OS
   - macOS: Uses `~/Library/Application Support/nushell/config.nu`
   - Linux: Uses `~/.config/nushell/config.nu`

### Configuration Files

**Shell Configuration:**
- `dot_bash_profile.tmpl` - Bash login shells: shared PATH/utility setup, sources `~/.bashrc`, then the zellij launcher
- `dot_bashrc.tmpl` - Interactive bash setup (history, completion, aliases, starship); Linux-only niceties gated off macOS
- `dot_zprofile.tmpl` - Zsh login shells: shared PATH/utility setup, then the zellij launcher
- `dot_zshenv` - Sourced for every zsh invocation; minimal (keeps PATH entries unique)
- `dot_zshrc` - Interactive zsh setup (history, completion, aliases, starship); no PATH (see shared snippet)
- `dot_bash_aliases` - Bash aliases
- `.chezmoitemplates/shell-env.sh` - Canonical PATH/utility/env setup shared by the bash and zsh login files
- `.chezmoitemplates/zellij-launch.sh` - Interactive zellij `welcome` launcher shared by bash and zsh
- `.chezmoitemplates/config.nu` - Comprehensive nushell configuration with:
  - PATH management for Homebrew, Cargo, Volta, pipx, and the generic bin dirs (kept in sync with `shell-env.sh`)
  - Starship prompt setup (with lite/full variants based on font support)
  - Helix editor integration
  - Environment-specific setup (CMS vs personal)
- Machine-local overrides (per-host, for tools not installed everywhere; sourced by the shared setup):
  - `dot_config/shell/create_env.local.sh` → `~/.config/shell/env.local.sh` (bash/zsh; e.g. SDKMAN, Docker, GUI apps)
  - `.chezmoitemplates/local.nu` + per-OS `create_local.nu.tmpl` → nushell `local.nu` (same purpose for nu)

**Terminal Multiplexer:**
- `dot_config/zellij/config.kdl.tmpl` - Custom keybindings with vim-style navigation, session serialization enabled, dynamically sets nushell as default shell

**Package Management:**
- `.chezmoidata/system_packages_autoinstall.yaml` - Declarative package manifest for macOS (Homebrew) and Ubuntu (apt + Homebrew)
- `.chezmoiscripts/run_onchange_system_packages_autoinstall.sh.tmpl` - Script that runs when manifest changes, uses `brew bundle` for installation

### Chezmoi Script Placement

Scripts that should run on `chezmoi apply` but should NOT exist as files on the target system
  live in `.chezmoiscripts/` at the repo root.
This includes installers (rustup, `brew bundle`), and dated one-time cleanup scripts
  for state left behind when a feature is removed.
See [`.claude/rules/chezmoi-script-placement.md`](./.claude/rules/chezmoi-script-placement.md)
  for the full rule (when to use `.chezmoiscripts/` vs `private_dot_*/` vs the repo root, and
  the convention of pairing feature removals with dated cleanup scripts).

### Key Design Patterns

**OS Detection Pattern:**
```go
{{ if eq .chezmoi.os "darwin" -}}
# macOS-specific code
{{ else if eq .chezmoi.osRelease.id "ubuntu" -}}
# Ubuntu-specific code
{{ end -}}
```

**Environment-Specific Configuration:**
The system prompts during `chezmoi init` for `systemType` (personal/cms), which sets `.isCMS` variable used throughout templates for environment-specific settings like:
- CMS: Sets `CTKEY_USERNAME` for AWS CLI token management
- CMS: Configures `NODE_EXTRA_CA_CERTS` for Zscaler certificate

**Cross-shell PATH/utility setup:**
One canonical utility list is shared across shells.
Bash and zsh source `.chezmoitemplates/shell-env.sh` from their login files
  (`~/.bash_profile`, `~/.zprofile`), and `.chezmoitemplates/config.nu` mirrors the same list for nushell
  — add a new tool in both places.
PATH lives in the login files (after macOS `path_helper`, which runs in `/etc/zprofile` and `/etc/profile`
  and would otherwise reorder it); the interactive rc files (`~/.bashrc`, `~/.zshrc`) hold no PATH.
Nushell uses `path add` (prepends) vs `++=` (appends); all additions check for directory existence first.
Tools that are NOT in `system_packages_autoinstall.yaml` (i.e. not installed on every system — SDKMAN,
  Docker, GUI apps, etc.) belong in the per-machine local files (`~/.config/shell/env.local.sh` for
  bash/zsh, `local.nu` for nushell), which the shared setup sources — not in the shared snippets.

**Shell startup file order (relevant to where things go):**
- zsh: `~/.zshenv` (always) → *(login)* `~/.zprofile` → *(interactive)* `~/.zshrc` →
    *(login)* `~/.zlogin`.
- bash: login reads `/etc/profile` then `~/.bash_profile`; interactive non-login reads `~/.bashrc`.
- SSH interactive sessions are login shells on both macOS and Linux.
- Non-login interactive shells (e.g. `zsh -i`, or a Linux IDE terminal) don't read the login files, so
    they inherit PATH from their parent process rather than rebuilding it — this is intentional, since
    PATH lives in the login files. A fresh non-login shell with no login ancestor gets only the system
    default PATH; in practice the entry points here (Terminal/iTerm/SSH) are all login shells.

**Auto-launching Zellij:**
Interactive login shells (bash via `~/.bash_profile`, zsh via `~/.zprofile`) exec `zellij -l welcome`
  on any OS via the shared `.chezmoitemplates/zellij-launch.sh`, dropping into the session chooser
  whose panes run nushell.
Safeguards:
- Interactive shells only (`case $- in *i*`) plus a real-tty check (`[ -t 1 ]`), so scripts, `ssh host 'cmd'`,
    scp/rsync, Ansible, cron, launchd, AppleScript, and editor env-resolution probes
    (VS Code/Cursor/Zed/JetBrains/Xcode) are never disturbed.
- IDE integrated terminals skipped by name (`VSCODE_*`, `TERM_PROGRAM`, `ZED_TERM`, `TERMINAL_EMULATOR`).
- `NO_ZELLIJ=1` environment variable opt-out.
- Recursion prevention (checks `$ZELLIJ` variable).
- Fallback to the normal shell if zellij missing.

## Development Toolchain

This repository manages configurations for:
- **Shell**: nushell (primary), bash (compatibility)
- **Prompt**: Starship (with nerd font support detection)
- **Terminal Multiplexer**: Zellij (replaces tmux)
- **Editor**: Helix (replaces vim)
- **Node.js**: Volta for version management
- **Python**: uv for build tooling
- **Package Management**: Homebrew (macOS + Ubuntu)

## Claude Code Configuration

This repository also manages Claude Code configuration for consistent setup across workstations.

### Managed Files

**Global Settings:**
- `~/.claude/settings.json` - Global preferences, plugins, and comprehensive pre-approved permissions
- `~/.claude/settings.local.json` - Machine-specific overrides (minimal, for truly local settings)

**Custom Slash Commands:**
- `~/.claude/commands/pr-quality-loop.md` - CI monitoring and fixing loop
- `~/.claude/commands/pr-merge.md` - Squash merge PR and clean up local branch

**Custom Skills:**
- `~/.claude/skills/using-zellij-docs/` - Ensures version-specific accuracy for Zellij shortcuts and config

**Plugin Configuration:**
- `~/.claude/plugins/known_marketplaces.json` - Plugin marketplace definitions (superpowers)

### Configuration Hierarchy

Claude Code settings follow a precedence hierarchy (highest to lowest):
1. **Enterprise Managed** (cannot be overridden)
2. **Command Line Arguments** (temporary session overrides)
3. **Local Project Settings** (`.claude/settings.local.json` in project, git-ignored)
4. **Shared Project Settings** (`.claude/settings.json` in project, version controlled)
5. **User Settings (Global)** (`~/.claude/settings.json` - managed by chezmoi)

### Global vs Project-Specific Configuration

**Global (chezmoi-managed):**
- Comprehensive pre-approved permissions (git, gh, common dev tools, web domains)
- Personal slash commands and skills
- Plugin marketplace configuration
- Applies across all workstations and projects

**Project-Specific (NOT chezmoi-managed):**
- `.claude/` directories in individual project repos
- Project-specific permissions and workflows
- Team-shared configuration (committed to project repos)

### Permission Philosophy

The global `settings.json` includes a comprehensive allow list compiled from all project-specific permissions:
- **Git operations**: add, commit, log, checkout, etc.
- **GitHub CLI**: pr, run, workflow commands
- **Dev tools**: Rust (cargo), Python (uv), Node (npm, bun), data tools (jq, yq, csv)
- **Web domains**: Documentation sites, package registries
- **Skills**: Superpowers skills (systematic-debugging, brainstorming, receiving-code-review, etc.)
- **Security**: Deny list for sensitive files (.env, credentials, AWS/SSH keys)

This permissive global setup reduces permission prompts while allowing project-specific overrides.

### Slash Command Usage

Available commands after applying chezmoi configuration:
- `/pr-quality-loop` - Iterative CI check monitoring and fixing until all pass
- `/pr-merge` - Squash merge PR and clean up local branch

Commands support bash command interpolation with `!`backticks`` for dynamic context.

## Testing and Quality

### Mise Task Runner

This repository uses mise for task automation and testing.

**Key tasks:**
- `:lint` - Run shellcheck on all bash scripts (V2 wkflw-ntfy scripts)
- `:test` - Run unit tests
- `:ci` - Run complete CI suite (lint + test in parallel)
- `:install-hooks` - Install git pre-commit hooks

**Running tasks:**
```bash
mise run test
mise run ci
```

**Note:** This is a dotfiles repo, not a monorepo. Task names use simple `:task` syntax (no `//` prefixes needed).

### Testing Approach

**Comprehensive unit test coverage:**
- Component isolation testing (config, logging, environment, strategy, markers, escalation)
- Platform-specific tests (macOS window ops, notifications, Linux)
- Mock-based testing for external dependencies

**Test structure:**
- `test/wkflw-ntfy/unit/` - Unit tests using bats framework
- `test/wkflw-ntfy/mocks/` - Mock executables (osascript, terminal-notifier, curl, notify-send)
- `test/wkflw-ntfy/helpers/` - Shared test utilities

**Pre-commit hooks:** Run `:ci` automatically before each commit (lint + test in parallel).

### Notification System Architecture (V2)

The wkflw-ntfy V2 system uses composable bash scripts following Unix philosophy:
- **Core utilities** (`private_dot_local/lib/wkflw-ntfy/core/`): Config, logging, environment detection,
    strategy selection
- **Markers** (`marker/`): Atomic operations for escalation tracking
- **Platform support** (`macos/`, `linux/`): Desktop notifications and window management
- **Push notifications** (`push/`): Mobile push via ntfy.sh
- **Escalation** (`escalation/`): Progressive escalation (desktop → mobile)
- **Hooks** (`hooks/`): Integration with Claude Code and nushell

See `private_dot_local/lib/wkflw-ntfy/README.md` for complete architecture documentation.

## Documentation Standards

### Markdown Formatting Guidelines

All markdown files follow standardized formatting rules:
- One sentence per line for better version control.
- 110-character line wrap limit at natural break points.
- Indent wrapped lines 2 spaces past where text begins (count prefix chars + 2):
  - Regular prose: 2 spaces (no prefix, text at column 1, so indent to column 3).
  - List items (`- ` = 2 chars, text at column 3): 4 spaces (indent to column 5).
  - Checklist items (`- [ ] ` = 6 chars, text at column 7): 8 spaces (indent to column 9).
- End all sentence-like lines with periods, including:
  - Regular prose sentences.
  - List items (bullet points and numbered lists).
  - Checklist items (todo entries).
  - Table cells containing full sentences.
  - Code comments in markdown code blocks (follow language conventions).
- Trailing whitespace removal (except when required by Markdown).
- POSIX line endings.
- Consistent formatting across all documentation files.

**Examples of proper formatting:**

Wrapping regular prose (2 spaces):
```
The quick brown fox
  jumped over the lazy dog.
```

Wrapping list items (4 spaces - aligning with text after `- `):
```
- The quick brown fox
    jumped over the lazy dog.
```

Wrapping checklist items (8 spaces - 2 spaces past text start):
```
- [ ] The quick brown fox
        jumped over the lazy dog.
```

Visual guide for checklist indentation:
```
- [ ] Text starts here at column 7
12345678^ (8 spaces - 2 past where text starts)
```

**Examples of lines that should end with periods:**
- ✅ "This is a prose sentence."
- ✅ "- List item describing a feature."
- ✅ "1. Numbered instruction step."
- ✅ "- [ ] Checklist item describing a task."
- ❌ "This sentence is missing punctuation" (missing period)
- ❌ "- List item without proper ending" (missing period)

### Documentation Organization

See `docs/README.md` for documentation structure and naming conventions.
All dated documents use `YYYY-MM-DD-short-name` format with kebab-case.
