# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
- `dot_bash_profile.tmpl` - On Ubuntu, auto-launches zellij session with nushell; macOS left largely untouched
- `dot_bash_aliases` - Bash aliases
- `.chezmoitemplates/config.nu` - Comprehensive nushell configuration with:
  - PATH management for Homebrew, Cargo, Volta, Docker, Java (SDKMAN)
  - Starship prompt setup (with lite/full variants based on font support)
  - Helix editor integration
  - Environment-specific setup (CMS vs personal)

**Terminal Multiplexer:**
- `dot_config/zellij/config.kdl.tmpl` - Custom keybindings with vim-style navigation, session serialization enabled, dynamically sets nushell as default shell

**Package Management:**
- `.chezmoidata/system_packages_autoinstall.yaml` - Declarative package manifest for macOS (Homebrew) and Ubuntu (apt + Homebrew)
- `run_onchange_system_packages_autoinstall.sh.tmpl` - Script that runs when manifest changes, uses `brew bundle` for installation

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

**Nushell Path Management:**
Config uses `path add` (prepends) vs `++=` (appends) for careful PATH ordering. All path additions check for directory existence before adding.

**Auto-launching Zellij:**
On Ubuntu login shells, `.bash_profile` automatically exec's `zellij -l welcome` with safeguards for:
- Non-interactive shells (scp, Ansible)
- `NO_ZELLIJ=1` environment variable opt-out
- Recursion prevention (checks `$ZELLIJ` variable)
- Fallback to bash if zellij missing

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
