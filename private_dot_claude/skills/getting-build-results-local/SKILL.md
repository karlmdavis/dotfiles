---
name: getting-build-results-local
description: Run local CI commands and return raw output - reads project CLAUDE.md to find build/test commands, executes them, returns output for parsing
---

# Getting Build Results Local

## Overview

Run the project's local CI commands (build, test, lint, type-check) and return raw output for parsing.

**Core principle:** This is an agent-only skill. Only Claude can read arbitrary project documentation and understand what CI commands to run.

**What it does:**
1. Read project's `CLAUDE.md` or similar documentation
2. Identify primary CI command(s) (build, test, lint, etc.)
3. Run command(s) via Bash tool
4. Capture output and return as TOON

**Output:** Raw build output ready for `parsing-build-results` skill

## When to Use

Use when you need:
- Local pre-commit build verification
- Test results before creating PR
- Quick feedback loop during development

**When NOT to use:**
- Need parsed failures (use `parsing-build-results` after this)
- Project has no documented CI commands
- Running in environment without build tools

## Finding CI Commands

### Step 1: Check CLAUDE.md

Look for sections like:
- "Key Commands"
- "CI"
- "Testing"
- "Development"

Common patterns:
```markdown
## CI

Run the complete CI suite:
```bash
mise run ci
```

## Testing

Run tests:
```bash
npm test
```
```

### Step 2: Check README.md

If CLAUDE.md doesn't exist or doesn't document CI:
```markdown
## Development

Build and test:
```bash
npm run build
npm test
```
```

### Step 3: Check Package Manager Files

If no documentation found, look for:
- `package.json` - "scripts.test", "scripts.ci"
- `Makefile` - "test" or "ci" targets
- `.mise.toml` - task definitions
- `justfile` - recipe names

### Step 4: Infer from Project Type

**Node.js projects:**
```bash
npm test          # Or yarn test, pnpm test
npm run build
```

**Python projects:**
```bash
pytest
python -m pytest
uv run pytest
```

**Rust projects:**
```bash
cargo test
cargo clippy
```

## Running Commands

### Execution Strategy

**If single comprehensive command exists:**
```bash
# Run the one CI command
mise run ci
```

**If multiple commands:**
```bash
# Run sequentially, capture each
npm run lint
npm test
npm run build
```

**Track each command:**
- Record command string
- Record working directory
- Capture full output (stdout + stderr)
- Record exit code
- Record duration

### Error Handling

**Continue on failure:** If multiple commands, run all even if earlier ones fail. We want complete picture of what's broken.

**Timeout:** Set reasonable timeout (e.g., 5 minutes per command). Build shouldn't hang.

## Return Format

Return raw build output in TOON:

```toon
status: completed

ci_commands[2]:
  id: 1
  command: MISE_EXPERIMENTAL=true mise run ':lint'
  cwd: /Users/karl/projects/myapp
  exit_code: 0
  duration_seconds: 12
  raw_output: |
    Running lint task...
    ✓ All files pass linting
    Done in 12s

  id: 2
  command: MISE_EXPERIMENTAL=true mise run ':test'
  cwd: /Users/karl/projects/myapp
  exit_code: 1
  duration_seconds: 33
  raw_output: |
    Running test task...

    FAIL tests/api.test.ts
      ● should handle null user

        TypeError: Cannot read property 'id' of null

          at handler (src/api.ts:89)
          at processUser (src/auth.ts:42)

    Tests: 1 failed, 47 passed, 48 total
    Done in 33s
```

## Integration with Parsing

After getting raw output, use `parsing-build-results` skill:

```markdown
Use parsing-build-results skill to parse the raw output above.
Changed files (for relatedness analysis):
- src/api.ts
- tests/api.test.ts
```

The parsing skill will extract structured failures and determine which are related to current changes.

## Common CI Command Patterns

### Mise Task Runner

```bash
# Single comprehensive task
mise run ci

# Or individual tasks
mise run ':lint'
mise run ':test'
mise run ':build'
```

### NPM/Yarn/Pnpm

```bash
# Check package.json for "scripts.ci"
npm run ci

# Or individual scripts
npm run lint
npm test
npm run type-check
npm run build
```

### Make

```bash
# Check Makefile for 'ci' or 'test' target
make ci
# Or
make test
```

### Cargo (Rust)

```bash
cargo test
cargo clippy
cargo build --release
```

### Poetry/uv (Python)

```bash
uv run pytest
uv run black --check .
uv run mypy .
```

## Usage Pattern

This is an agent-only skill. Caller provides working directory, agent figures out and runs CI commands.

**Example caller pattern:**
```markdown
Use Task tool with subagent_type='general-purpose':

"Use the getting-build-results-local skill to run local CI commands.
Working directory: /Users/karl/projects/myapp

Read CLAUDE.md to find CI commands, run them, and return raw output
in TOON format."
```

## Integration with Other Skills

**Used by:**
- `getting-feedback-local` - Orchestrates local feedback
- `/pr-address-feedback-local` command - Pre-PR verification
- `/pr-address-feedback-remote` command - Pre-commit verification

**Provides output to:**
- `parsing-build-results` - Parses raw output into structured failures

## Common Mistakes

**Not reading documentation**
- **Problem:** Guess CI commands, miss project-specific setup
- **Fix:** Always check CLAUDE.md, README.md, package files first

**Running only partial CI**
- **Problem:** Miss failures in other areas (e.g., run tests but not lint)
- **Fix:** Look for comprehensive "ci" command or run all relevant commands

**Stopping on first failure**
- **Problem:** Don't see full picture of what's broken
- **Fix:** Run all commands, track which failed

**Not capturing stderr**
- **Problem:** Miss error output
- **Fix:** Capture both stdout and stderr

## Special Cases

### Docker-based CI

If CI runs in Docker:
```bash
# Look for docker-compose setup
docker-compose run test

# Or Dockerfile with test target
docker build --target test .
```

### Remote/Cloud CI Only

If project only has remote CI (e.g., GitHub Actions only):
- Note in output that local CI not available
- Return status: "no_local_ci"
- Recommend using `getting-feedback-remote` instead

### Interactive Commands

If CI command requires user input:
- Look for non-interactive flags
- Check if CI mode can be enabled
- Document limitation in output

## Environment Setup

**Before running CI:**

Check if environment setup needed:
```bash
# Install dependencies if needed
npm install
cargo build
uv sync
```

Look for setup instructions in CLAUDE.md or README.md.

## Quick Reference

| Project Type | Likely CI Command |
|--------------|-------------------|
| Node.js | `npm test`, `npm run ci` |
| Rust | `cargo test`, `cargo clippy` |
| Python | `pytest`, `uv run pytest` |
| Task Runner | `mise run ci`, `make test` |
| Monorepo | Check workspace docs |

## Example Documentation Patterns

**Pattern 1: Explicit CI command**
```markdown
## CI

Run complete CI suite:
```bash
mise run ci
```
```

**Pattern 2: Individual commands**
```markdown
## Testing

- Lint: `npm run lint`
- Tests: `npm test`
- Type check: `npm run type-check`
```

**Pattern 3: Script file**
```markdown
## CI

Run `scripts/ci.sh` for full CI suite.
```
