# Build Error Parsing Patterns

## Overview

Patterns for parsing compiler/build tool output (tsc, cargo build, gcc, javac, etc.).

## Common Patterns

### TypeScript Compiler (tsc)

```
src/api.ts(42,15): error TS2531: Object is possibly 'null'.
src/auth.ts(89,5): error TS2345: Argument of type 'string | undefined' is not assignable to parameter of type 'string'.
```

**Extract:**
- **Location**: `src/api.ts:42` (convert parentheses to colon)
- **Type**: "type_check" (tsc is primarily type checking)
- **Messages**: Error code + description

```toon
type: type_check
location: src/api.ts:42
messages[1]:
  |
    error TS2531: Object is possibly 'null'
```

### Cargo Build (Rust)

```
error[E0425]: cannot find value `user` in this scope
  --> src/main.rs:42:9
   |
42 |         user.id
   |         ^^^^ not found in this scope

error: aborting due to previous error
```

**Extract:**
- **Location**: `src/main.rs:42`
- **Type**: "build"
- **Messages**: Error code + description

### GCC/Clang (C/C++)

```
src/main.c:42:15: error: use of undeclared identifier 'user'
        return user->id;
               ^
1 error generated.
```

**Extract:**
- **Location**: `src/main.c:42`
- **Type**: "build"
- **Messages**: Error description + code snippet

### Javac (Java)

```
src/Main.java:42: error: cannot find symbol
        return user.id;
               ^
  symbol:   variable user
  location: class Main
1 error
```

**Extract:**
- **Location**: `src/Main.java:42`
- **Type**: "build"
- **Messages**: Error type + symbol info

### Webpack/Vite (JavaScript bundlers)

```
ERROR in ./src/api.ts 42:15
Module not found: Error: Can't resolve './user' in '/Users/karl/project/src'
```

**Extract:**
- **Location**: `src/api.ts:42`
- **Type**: "build"
- **Messages**: Module resolution error

## Code Snippets

Include code snippet if provided, but keep it brief (1-2 lines):

```toon
messages[2]:
  |
    error[E0425]: cannot find value 'user' in this scope
  |
    42 |         user.id
       |         ^^^^ not found in this scope
```

## Multi-line Errors

Some compilers show multi-line error messages with helpful context:

```
error[E0308]: mismatched types
  --> src/api.rs:42:5
   |
42 |     user
   |     ^^^^ expected `Option<User>`, found `User`
   |
   = help: try wrapping the expression in `Some`
```

Include help text if valuable:

```toon
messages[2]:
  |
    error[E0308]: mismatched types
    expected Option<User>, found User
  |
    help: try wrapping in Some
```

## Multiple Errors in Same File

Create separate failure entries:

```toon
failures[2]:
  type: build
  location: src/api.rs:42
  messages[1]:
    |
      error[E0425]: cannot find value 'user'

  type: build
  location: src/api.rs:89
  messages[1]:
    |
      error[E0308]: mismatched types
```

## Build Summary

Parse build result summary:

```
error: could not compile `myapp` due to 2 previous errors
```

Verify you captured all errors mentioned in summary.
