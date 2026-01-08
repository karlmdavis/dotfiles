---
name: parsing-build-results
description: Parse raw build/test logs into structured failures - extracts commands, failures, locations, and determines if related to current changes
context: fork
---

# Parsing Build Results

## Overview

Parse raw build output (from local CI or GitHub workflows) into structured TOON format with extracted failures, file locations, and relatedness analysis.

Core principle: This is an agent-only skill. No script can parse arbitrary build output as well as Claude can reason about unstructured logs.

**Input:** Raw build logs (from `getting-build-results-local` or `getting-build-results-remote`)

Output: Structured TOON with CI commands, failures, and recommendations

## When to Use

Use when you need to:
- Parse build/test output into actionable failures
- Extract file:line locations from error messages
- Determine which failures are related to current changes
- Get structured failure data for main context

When NOT to use:
- Need to fetch logs (use getting-build-results-* skills first)
- Already have structured test results

## Concrete Example

**Input (raw build log from npm test):**

```
> npm test

PASS tests/utils.test.ts
  ✓ should format dates correctly (5ms)
  ✓ should handle null inputs (2ms)

FAIL tests/api.test.ts
  ✓ should validate request body
  ✕ should handle null user (15ms)

  ● should handle null user

    TypeError: Cannot read property 'id' of null

      42 |   const handler = (user) => {
      43 |     return user.id;
         |                 ^
      44 |   }
         |
      at handler (src/api.ts:43)
      at processRequest (src/api.ts:89)

Tests: 1 failed, 3 passed, 4 total
Time: 2.5s
```

**Changed files (provided by caller):**
- src/api.ts
- tests/api.test.ts

**Output (parsed TOON):**

```toon
status: fail_related

ci_commands[1]:
  id: 1
  command: npm test
  exit_code: 1
  duration_seconds: 3

failures[1]:
  type: test
  location: tests/api.test.ts:42
  source_command_id: 1
  related_to_changes: true
  reasoning: |
    Test file tests/api.test.ts was modified in the current changeset.
    The failure is in code that was changed.
  messages[2]:
    |
      FAIL tests/api.test.ts
        ✕ should handle null user
    |
      TypeError: Cannot read property 'id' of null
        at handler (src/api.ts:43)

recommendation: fix_related_first
```

## What to Extract

### 1. CI Commands

Identify what commands were run. Look for:
- Task runner invocations (`npm test`, `cargo build`, `mise run :test`)
- CI tool output (`==> Running task: build`)
- Shell commands in logs

For each command, extract:
- **id** - Sequential number (1, 2, 3...)
- **command** - The actual command string
- **cwd** - Working directory if available
- **exit_code** - 0 for success, non-zero for failure
- **duration_seconds** - How long it ran (if available)

### 2. Failures

For each failure, extract:
- **type** - "test", "lint", "build", "type_check", "other"
- **location** - File path and line number (`src/api.ts:42`)
- **source_command_id** - Which CI command produced this failure
- **related_to_changes** - Boolean (see below)
- **reasoning** - Why you determined relatedness
- **messages** - List of error message snippets (not full logs)

### 3. Relatedness Analysis

CRITICAL: Determine if each failure is related to the current changes.

**How to determine:**
- Read the failure location (file:line)
- Compare against changed files (use `git diff` or context provided by caller)
- If failure is in a changed file → `related_to_changes: true`
- If failure is in unchanged file → `related_to_changes: false`

**Note:** Caller provides the context for what changed (either staged changes or branch changes).

### 4. Recommendation

Based on failures, return one of:
- **all_passed** - No failures
- **fix_related_first** - Some failures are related to changes, fix those first
- **unrelated_failures** - All failures are in unchanged code
- **mixed** - Both related and unrelated failures

## Parsing Strategies

For detailed parsing patterns by error type, see the reference files:

**Test failures**: See [reference/test-failures.md](reference/test-failures.md) for Jest, pytest, cargo test patterns
**Lint errors**: See [reference/lint-errors.md](reference/lint-errors.md) for ESLint, clippy, ruff patterns
**Build errors**: See [reference/build-errors.md](reference/build-errors.md) for tsc, cargo, gcc patterns
**Type errors**: See [reference/type-errors.md](reference/type-errors.md) for mypy, pyright, Flow patterns

### Quick Reference

For most cases, look for these common patterns:

**File:line locations:**
- `src/api.ts:42` or `src/api.ts(42,15)` (TypeScript)
- `--> src/main.rs:42:9` (Rust)
- `src/api.py:42:` (Python)

**Error indicators:**
- Lines starting with "error:", "Error:", "FAIL", "FAILED"
- Stack traces with "at [location]"
- Compiler output with `-->` or `error[E...]`

**Extract from each failure:**
1. **Type**: test/lint/build/type_check based on command
2. **Location**: First file:line reference found
3. **Messages**: Key error lines (2-3 snippets max, not full output)

## Return Format

Return structured TOON output:

```toon
status: fail_related

ci_commands[2]:
  id: 1
  command: MISE_EXPERIMENTAL=true mise run ':lint'
  cwd: /Users/karl/projects/myapp
  exit_code: 0
  duration_seconds: 12

  id: 2
  command: MISE_EXPERIMENTAL=true mise run ':test'
  cwd: /Users/karl/projects/myapp
  exit_code: 1
  duration_seconds: 33

failures[2]:
  type: test
  location: tests/api.test.ts:42
  source_command_id: 2
  related_to_changes: true
  reasoning: |
    This test failure is in tests/api.test.ts which was modified in
    the current changeset (added new test case).
  messages[2]:
    |
      FAIL tests/api.test.ts
        ● should handle null user
    |
      TypeError: Cannot read property 'id' of null
        at handler (src/api.ts:89)

  type: lint
  location: src/utils.ts:15
  source_command_id: 1
  related_to_changes: false
  reasoning: |
    This lint error is in src/utils.ts which was not modified in the
    current changeset. This is a pre-existing issue.
  messages[1]:
    |
      warning: unused variable 'result'
        --> src/utils.ts:15:9

recommendation: fix_related_first
```

## Status Field Values

- **all_passed** - No failures found
- **fail_related** - One or more failures related to changes
- **fail_unrelated** - Failures only in unchanged code
- **fail_mixed** - Both related and unrelated failures

## Common Patterns

### Multiple Commands in One Log

If logs show sequential commands:
```
==> Running task: lint
[lint output]
==> Running task: test
[test output]
```

Create separate `ci_commands` entries for each.

### Stack Traces

For stack traces, include the first few lines in `messages`, not the entire trace:
```messages[2]:
  |
    TypeError: Cannot read property 'id' of null
      at handler (src/api.ts:89)
  |
    at processUser (src/auth.ts:42)
```

### Discontiguous Errors

Use the `messages` list for non-adjacent error snippets:
```messages[3]:
  |
    Error in src/api.ts:42
  |
    Caused by: Database connection failed
  |
    Help: Check DATABASE_URL environment variable
```

## Integration with Other Skills

Used by:
- `getting-feedback-local` - Parses local build output
- `getting-feedback-remote` - Parses GitHub workflow logs

**Dependencies:**
- Requires raw logs from `getting-build-results-local` or `getting-build-results-remote`
- Requires context about changed files (provided by caller)

## Usage Pattern

**Context:** This skill uses `context: fork` to always run in isolated subagent context.

This is an agent-only skill. Caller provides:
1. Raw build logs
2. Context about changed files (git diff or file list)

Agent parses logs and returns structured TOON.

**Example caller pattern:**
```
Use Task tool with subagent_type='general-purpose':

"Parse the following build output using the parsing-build-results skill.
Changed files in this PR: src/api.ts, tests/api.test.ts

Raw build output:
[paste logs here]

Return structured TOON output with failures and relatedness analysis."
```

## Common Mistakes

**Including full logs in messages**
- Problem: Makes output too verbose
- Fix: Extract only key error lines, not full traces

**Not analyzing relatedness**
- Problem: Caller can't prioritize fixes
- Fix: Always compare failure locations to changed files

**Missing file:line locations**
- Problem: Hard to find where to fix
- Fix: Parse stack traces and error messages for locations

**Wrong failure type**
- Problem: Misleading categorization
- Fix: Use test/lint/build/type_check based on error source

## Edge Cases

**No failures found but exit code non-zero:**
- Look for infrastructure failures (out of memory, timeout, etc.)
- Return type: "other" with available context

**Can't extract file location:**
- Use best available info (test name, error message)
- Leave location as generic description

**Multiple failures in same file:**
- Create separate failure entries for each
- Include line numbers to distinguish

**Uncertain about relatedness:**
- Be conservative: mark as `related_to_changes: true`
- Explain uncertainty in reasoning field
