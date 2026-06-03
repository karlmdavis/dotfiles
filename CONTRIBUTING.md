# Contributing to Dotfiles

## Development Tools

This repository uses [mise](https://mise.jdx.dev/) as a task runner for linting and testing.

### Prerequisites

- **mise** - Tool version manager and task runner
- **shellcheck** - Bash script linter (installed via mise)
- **bats-core** - Bash testing framework (installed via mise)
- **uv** - Runs the embedded Python mini-projects' pytest suites as an ephemeral (no persistent
    pytest tool); installed via the package manifest.
- **nushell** - Shell with testing support (installed via system package manager)

### Initial Setup

1. **Install mise:**
   ```bash
   curl https://mise.run | sh
   ```

2. **Install dependencies:**
   ```bash
   mise install
   ```

3. **Install git hooks:**
   ```bash
   mise install-hooks
   ```

## Using Mise Tasks

**Discover available tasks:**
```bash
mise tasks
```

**Task reference:**

- `:lint` - Run shellcheck on managed bash scripts
- `:test` - Run unit tests
- `:ci` - Run complete CI suite (lint + test in parallel)
- `:install-hooks` - Install git pre-commit hooks

**Running tasks:**
```bash
mise run lint
mise run test
mise run ci
```

**Note:** Top-level tasks use simple names (`:lint`, `:test`). The repo is also a mise monorepo:
  embedded mini-projects under `private_dot_local/lib/*` carry their own `mise.toml`, and the root
  `:test` cascades into them via `//<path>:<task>` (e.g.
  `//private_dot_local/lib/cmd-notify:test`).

## Testing

Two test idioms coexist: **bats** under `test/` for shell/template helpers, and **pytest** for the
  embedded Python mini-projects (`private_dot_local/lib/*/tests/`), the latter run as a `uv`
  ephemeral via the mise monorepo.

### Running Tests

**Run all tests:**
```bash
mise run test
```

**Run with linting:**
```bash
mise run ci                 # Lint + test in parallel
```

**Test structure:**
- `private_dot_local/lib/cmd-notify/tests/` - Long-running command notifier (pytest).
    Drives the helper with `--dry-run` / env seams and asserts on the would-be notifier
    invocation; no external mocks needed.
- `private_dot_local/lib/aerospace-workspaces/tests/` - AeroSpace workspace indicator + HUD
    (pytest).
- `test/claude/` - Tests for the Claude Code `modify_settings.json.tmpl` merge script (bats).

## Pre-commit Hooks

Pre-commit hooks automatically run `:ci` (lint + test) before each commit:
- Shellcheck validation for all bash scripts
- E2E tests for notification scenarios

**Skip hooks for WIP commits:**
```bash
git commit --no-verify
```

## Linting

**Run shellcheck:**
```bash
mise run lint
```

Shellcheck validates the managed bash scripts listed in `mise.toml`'s `[tasks.lint]` block —
  currently `.chezmoiscripts/run_install_rustup.sh`.
(The Python mini-projects are covered by their pytest suites, not shellcheck.)

## Chezmoi Workflow

**Check what would change:**
```bash
chezmoi status
chezmoi diff
```

**Apply changes to home directory:**
```bash
chezmoi apply
```

**Edit a managed file (handles templates correctly):**
```bash
chezmoi edit <FILE>
```

**Add a new file to chezmoi management:**
```bash
chezmoi add <FILE>
```

**Important notes:**
- **Auto-commit enabled**: Chezmoi is configured to automatically commit and push changes
    (see `.chezmoi.toml.tmpl`).
- **Template files**: Files ending in `.tmpl` use Go templating.
  Always use `chezmoi edit` for templated files, never edit them directly in the home directory.
- **OS-specific paths**: Nushell config has different paths on macOS vs Linux
    (see `.chezmoiignore` for OS-specific file application).

## Development Workflow

For solo dotfiles management:

1. Make changes to dotfiles
2. Run `mise ci` to validate locally
3. Commit changes (hooks will run automatically)
4. Chezmoi auto-commits and pushes (if configured)

For collaborative changes (if using PRs):

1. Create feature branch
2. Make changes and commit
3. Run `mise ci` to validate
4. Push and create PR
5. Merge after review

## Troubleshooting

### Testing Issues

**Tests failing:**
- Ensure mise dependencies are installed: `mise install`.
- Check that system nushell is available: `which nu`.
- Run tests individually to isolate failures.

**Shellcheck warnings:**
- Fix issues reported by shellcheck.
- Use shellcheck directives sparingly (e.g., `# shellcheck disable=SC2016`).

**Mock not working:**
- Ensure mocks are executable: `chmod +x test/mocks/*`.
- Check PATH is set correctly in tests.
- Verify mock environment variables are exported.

### Chezmoi Issues

**Template syntax errors:**
```bash
# Test template rendering
chezmoi execute-template < path/to/file.tmpl
```

**Unwanted files being managed:**
```bash
# Check .chezmoiignore for exclusions
chezmoi status
```

**Conflicts between local and managed files:**
```bash
# See what would change
chezmoi diff

# Force apply only with explicit user approval (overwrites local changes)
chezmoi apply --force
```

## Getting Help

- See `CLAUDE.md` for project guidelines and architecture.
- See `README.md` for setup and usage instructions.
- Check `docs/` for additional documentation.
- Open an issue for bugs or feature requests.
