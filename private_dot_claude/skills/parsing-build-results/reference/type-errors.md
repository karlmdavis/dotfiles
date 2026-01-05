# Type Error Parsing Patterns

## Overview

Patterns for parsing type checker output (mypy, pyright, tsc in check mode, flow).

## Common Patterns

### MyPy (Python)

```
src/api.py:42: error: Item "None" has no attribute "id"  [union-attr]
src/api.py:89: error: Argument 1 to "process" has incompatible type "str | None"; expected "str"  [arg-type]
```

**Extract:**
- **Location**: `src/api.py:42`
- **Type**: "type_check"
- **Messages**: Error description + error code

```toon
type: type_check
location: src/api.py:42
messages[1]:
  |
    error: Item "None" has no attribute "id" [union-attr]
```

### Pyright (Python)

```
src/api.py:42:15 - error: "None" is not a valid type for attribute access (reportOptionalMemberAccess)
src/api.py:89:5 - warning: Type of "user" is partially unknown (reportUnknownVariableType)
```

**Extract:**
- **Location**: `src/api.py:42:15`
- **Type**: "type_check"
- **Messages**: Error description + rule code

### TypeScript (tsc --noEmit)

```
src/api.ts:42:15 - error TS2531: Object is possibly 'null'.

42     return user.id;
                  ~~

src/api.ts:89:5 - error TS2345: Argument of type 'string | undefined' is not assignable to parameter of type 'string'.
```

**Extract:**
- **Location**: `src/api.ts:42:15`
- **Type**: "type_check"
- **Messages**: Error code + description + code snippet

```toon
type: type_check
location: src/api.ts:42
messages[2]:
  |
    error TS2531: Object is possibly 'null'
  |
    42     return user.id;
                      ~~
```

### Flow (JavaScript)

```
Error ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈ src/api.js:42:15

Cannot get user.id because property id is missing in null [1].

    39│ function getUser(user) {
    40│   if (!user) return null;
 [1] 41│   return null;
    42│   return user.id;
           ^^^^^^^^^^^^^^
```

**Extract:**
- **Location**: `src/api.js:42:15`
- **Type**: "type_check"
- **Messages**: Error description

## Severity Handling

Type checkers often report both errors and warnings:

- **error** → Always include in failures
- **warning** / **note** → Include if exit code != 0

Example:
```
src/api.py:42: error: Item "None" has no attribute "id"
src/api.py:89: note: Possible overload variants:
```

Only include the error in failures, skip the note unless it provides crucial context.

## Type Inference Failures

Some type errors show complex type mismatches:

```
src/api.ts:42:5 - error TS2322: Type 'Promise<User | null>' is not assignable to type 'User'.
  Type 'Promise<User | null>' is missing the following properties from type 'User': id, name, email
```

Keep description concise:

```toon
messages[1]:
  |
    error TS2322: Type 'Promise<User | null>' not assignable to 'User'
    Missing properties: id, name, email
```

## Multiple Errors Same Location

Sometimes multiple type errors occur at same location with different aspects:

```
src/api.ts:42:15 - error TS2531: Object is possibly 'null'.
src/api.ts:42:15 - error TS2532: Object is possibly 'undefined'.
```

Combine into single failure:

```toon
type: type_check
location: src/api.ts:42
messages[1]:
  |
    error TS2531/TS2532: Object is possibly 'null' or 'undefined'
```

## Summary Lines

Parse type check summary:

```
Found 3 errors in 2 files.

Errors  Files
     2  src/api.ts:42
     1  src/auth.ts:89
```

Verify you captured all errors mentioned in summary.
