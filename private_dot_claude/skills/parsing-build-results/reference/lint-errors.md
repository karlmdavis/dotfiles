# Lint Error Parsing Patterns

## Overview

Patterns for parsing linter output (eslint, clippy, ruff, etc.).

## Common Patterns

### ESLint (JavaScript/TypeScript)

```
/Users/karl/project/src/api.ts
  42:15  error  'user' is possibly 'null'  @typescript-eslint/no-unnecessary-condition
  89:5   warning  Missing error handler  no-unsafe-optional-chaining
```

**Extract:**
- **Location**: `src/api.ts:42` (and `:89` for second)
- **Type**: "lint"
- **Messages**: Rule violation description

```toon
type: lint
location: src/api.ts:42
messages[1]:
  |
    error: 'user' is possibly 'null'
    (@typescript-eslint/no-unnecessary-condition)
```

### Clippy (Rust)

```
warning: unused import in src/simulator.rs
  --> src/simulator.rs:5:5
   |
 5 | use std::collections::HashMap;
   |     ^^^^^^^^^^^^^^^^^^^^^^^^^
   |
   = note: `#[warn(unused_imports)]` on by default
```

**Extract:**
- **Location**: `src/simulator.rs:5`
- **Type**: "lint"
- **Messages**: Warning type + code snippet

### Ruff (Python)

```
src/api.py:42:5: F841 Local variable 'user' is assigned but never used
src/api.py:89:15: E711 Comparison to None should be 'if cond is None:'
```

**Extract:**
- **Location**: `src/api.py:42` (and `:89` for second)
- **Type**: "lint"
- **Messages**: Error code + description

### Shellcheck (Bash)

```
script.sh:15:5: warning: SC2086: Double quote to prevent globbing
script.sh:42:10: error: SC2155: Declare and assign separately
```

**Extract:**
- **Location**: `script.sh:15`
- **Type**: "lint"
- **Messages**: Error code + description

## Severity Levels

Map linter severity to failure importance:

- **error** → Include in failures
- **warning** → Include if exit code != 0, or if many warnings
- **info** / **note** → Usually skip, unless blocking CI

## Auto-fixable Issues

Some linters note auto-fixable issues:

```
15:5  error  Missing semicolon  semi  (fixable)
```

Note in messages if auto-fix available:

```toon
messages[1]:
  |
    error: Missing semicolon (auto-fixable)
```

## Multiple Files

When linter reports errors across multiple files, create separate failure entries per file:

```toon
failures[3]:
  type: lint
  location: src/api.ts:42
  messages[1]:
    |
      error: 'user' is possibly 'null'

  type: lint
  location: src/auth.ts:15
  messages[1]:
    |
      warning: unused variable 'token'

  type: lint
  location: tests/api.test.ts:89
  messages[1]:
    |
      error: Missing await on async call
```

## Summary Lines

Parse linter summary to confirm count:

```
✖ 3 problems (2 errors, 1 warning)
  1 error and 0 warnings potentially fixable with --fix
```

Verify you captured all errors/warnings that caused non-zero exit.
