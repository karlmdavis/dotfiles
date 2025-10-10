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
