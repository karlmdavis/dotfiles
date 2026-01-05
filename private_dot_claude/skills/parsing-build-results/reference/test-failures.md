# Test Failure Parsing Patterns

## Overview

Patterns for parsing test framework output (Jest, pytest, cargo test, etc.).

## Common Patterns

### Jest/Vitest (JavaScript/TypeScript)

```
FAIL tests/api.test.ts
  ● should handle null user
    TypeError: Cannot read property 'id' of null
      at handler (src/api.ts:89)
      at processUser (src/auth.ts:42)
```

**Extract:**
- **Location**: `tests/api.test.ts` (primary) + stack trace locations
- **Type**: "test"
- **Messages**: Test name + error type + stack trace (first 2-3 lines)

```toon
type: test
location: tests/api.test.ts
messages[2]:
  |
    FAIL tests/api.test.ts
      ● should handle null user
  |
    TypeError: Cannot read property 'id' of null
      at handler (src/api.ts:89)
```

### Pytest (Python)

```
FAILED tests/test_api.py::test_null_user - AssertionError: Expected user to exist
    def test_null_user():
        user = None
>       assert user.id == 123
E       AttributeError: 'NoneType' object has no attribute 'id'

tests/test_api.py:42: AttributeError
```

**Extract:**
- **Location**: `tests/test_api.py:42`
- **Type**: "test"
- **Messages**: Test name + assertion failure + line reference

### Cargo Test (Rust)

```
running 48 tests
test api::test_null_user ... FAILED

failures:

---- api::test_null_user stdout ----
thread 'api::test_null_user' panicked at 'assertion failed: user.is_some()', src/api.rs:42:5
```

**Extract:**
- **Location**: `src/api.rs:42`
- **Type**: "test"
- **Messages**: Test name + panic message

### Go Test

```
--- FAIL: TestNullUser (0.00s)
    api_test.go:42: Expected user to exist, got nil
FAIL
FAIL    github.com/user/project/api     0.012s
```

**Extract:**
- **Location**: `api_test.go:42`
- **Type**: "test"
- **Messages**: Test name + failure message

## Stack Trace Handling

Include first 2-3 lines of stack trace, not the full trace:

```toon
messages[2]:
  |
    TypeError: Cannot read property 'id' of null
      at handler (src/api.ts:89)
  |
    at processUser (src/auth.ts:42)
```

**Don't include:**
- Internal framework stack frames
- Node modules stack frames
- Full 20+ line stack traces

## Multiple Failures in Same File

Create separate failure entries for each test:

```toon
failures[2]:
  type: test
  location: tests/api.test.ts:42
  messages[1]:
    |
      ✕ should handle null user

  type: test
  location: tests/api.test.ts:58
  messages[1]:
    |
      ✕ should validate email format
```

## Test Summary Lines

Parse summary to confirm failure count:

```
Tests: 2 failed, 47 passed, 49 total
```

Use this to verify you captured all failures.
