# Contributing to Dotfiles

## Development Tools

This repository uses [mise](https://mise.jdx.dev/) as a task runner for linting and testing.

### Prerequisites

- **mise** - Tool version manager and task runner
- **shellcheck** - Bash script linter (installed via mise)
- **bats-core** - Bash testing framework (installed via mise)
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

- `:lint` - Run shellcheck on all bash scripts
- `:test` - Run all E2E tests (bash + nushell)
- `:test-bash` - Run bash script tests only
- `:test-nu` - Run nushell hook tests only
- `:ci` - Run complete CI suite (lint + test in parallel)
- `:install-hooks` - Install git pre-commit hooks

**Running tasks:**
```bash
mise run lint
mise run test
mise run ci
```

**Note:** This repo uses simple task names (`:lint`, `:test`) without `//` prefixes. No special quoting needed in any shell.

## Testing

This project follows a **minimal E2E testing approach** focused on happy paths:

### Test Strategy

- **E2E Tests (Happy Path Only):** Test complete workflows with mocked external dependencies
- **No Unit Tests:** Scripts are integration-focused; E2E coverage is sufficient
- **Mocked Dependencies:** ntfy, iTerm2/AppleScript, ioreg (idle detection)

### Running Tests

**Run all tests:**
```bash
mise run test
```

**Run specific test suites:**
```bash
mise run test-bash   # Claude hook tests (bats)
mise run test-nu     # Nushell hook tests
```

**Test files:**
- `test/test_claude_hooks.bats` - Tests for Claude Code notification scenarios
- `test/test_nushell_hooks.nu` - Tests for nushell command notifications
- `test/mocks/` - Mock executables for ntfy, osascript, ioreg
- `test/test_helpers.bash` - Shared test utilities

### Test Coverage

Tests focus on critical notification paths:
1. **Claude unfocused → notify:** User away when Claude finishes long work
2. **Claude focused → no notify:** User watching when Claude finishes
3. **Nushell long command:** Notification after long shell command completes

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

Shellcheck validates all bash scripts in:
- `private_dot_local/bin/executable_ntfy-*.sh`
- `run_once_ntfy-generate-topic.sh`
- `test/test_helpers.bash`
- `test/mocks/*`

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
