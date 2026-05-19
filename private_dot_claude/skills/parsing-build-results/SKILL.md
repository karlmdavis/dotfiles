---
name: parsing-build-results
description: Parse logs and other outputs from failed builds into structured failures - extracts the failures, lines relevant to them from the specified logs and other outputs, and the commands that failed.
user_invocable: false
---

# Parsing Build Results

## Overview

I would like you to parse the logs and other outputs
  from failed builds into structured issues, extracting:
  any problems evidenced in them,
  all lines from the logs and other outputs that are relevant to those issues,
  and the relevant commands that were run.
You should return this extracted analysis in a structured TOON format.

You should have access to the following context when using this skill:

- The source code that the build was run from and against.
- The commands that were run during the build.
- The contents of, paths for, and/or URLs for to the log
    and other outputs/artifacts from the failed build.
  - For remote builds (e.g., GitHub Actions workflows),
      the agent may need to fetch those logs/artifacts first.
    When doing so, be sure to either stream their contents,
      or save them as temporary files and clean them up afterward,
      before you return the TOON-formatted output.

If this is missing or otherwise unavailable,
  you should stop and report an error to the user,
  as it is not possible to proceed without it.

## TOON Format Overview

Many steps will produce and/or consume TOON-formatted data,
  which is a structured data format suited for use by agents.
TOON is similar to JSON and YAML but uses 2-space indents and arrays show length and fields.
Here's a small toy example:

```toon
context:
  task: Our favorite hikes together
  location: Boulder
  season: spring_2025
friends[3]: ana,luis,sam
hikes[3]{id,name,distanceKm,elevationGain,companion,wasSunny}:
  1,Blue Lake Trail,7.5,320,ana,true
  2,Ridge Overlook,9.2,540,luis,false
  3,Wildflower Loop,5.1,180,sam,true
```

## Concrete Examples

### Example: NPM Build with Test Failure

The agent is considering a failed NPM build of a JavaScript project
  with the following console output snippet:

```bash
$ npm test

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

**TOON Output:**

```toon
build_issues[1]:
  - description: "Improper handling of null user in API tests leading to TypeError"
    type: test
    source_locations[2]:
      - src/api.ts:71
      - tests/api.test.ts:42
    relevant_commands[1]{command,cwd,exit_code}:
      npm test,/path/to/project,1
    relevant_output[2]:
      - snippet: |
          FAIL tests/api.test.ts
            ✕ should handle null user (15ms)
        source: console_output
        source_line_number_start: 7
      - snippet:  |
          TypeError: Cannot read property 'id' of null
            at handler (src/api.ts:71)
        source: console_output
        source_line_number_start: 11
      - snippet: |
          <testcase classname="tests.api" name="should handle null user">
            <failure message="TypeError: Cannot read property 'id' of null">
              at handler (src/api.ts:71)
            </failure>
          </testcase>
        source: ./reports/junit_report.xml
        source_line_number_start: 15
```

### Example: Mise Build with Lint and Compiler Errors

The agent is considering a failed Mise build of a Rust project
  with the following GitHub Actions log:

```bash
2026-01-24T22:09:20.5534917Z Current runner version: '2.331.0'
... (omitted early log/steps for brevity) ...
2026-01-24T22:09:35.0143654Z ##[group]Run mise run ci
2026-01-24T22:09:35.0143916Z [36;1mmise run ci[0m
2026-01-24T22:09:35.0173937Z shell: /usr/bin/bash -e {0}
2026-01-24T22:09:35.0174161Z env:
2026-01-24T22:09:35.0174343Z   CARGO_HOME: /home/runner/.cargo
2026-01-24T22:09:35.0174582Z   CARGO_INCREMENTAL: 0
2026-01-24T22:09:35.0174788Z   CARGO_TERM_COLOR: always
2026-01-24T22:09:35.0174994Z   MISE_LOG_LEVEL: info
2026-01-24T22:09:35.0175406Z   GITHUB_TOKEN: ***
2026-01-24T22:09:35.0175731Z   MISE_TRUSTED_CONFIG_PATHS: /home/runner/work/fancy_rust_app/fancy_rust_app
2026-01-24T22:09:35.0176095Z   MISE_YES: 1
2026-01-24T22:09:35.0176268Z ##[endgroup]
2026-01-24T22:09:35.0374687Z [0m[34m[build][0m [1m$ cargo build --release[0m
2026-01-24T22:09:35.0408489Z [0m[35m[lint][0m [1m$ cargo clippy -- -D warnings[0m
2026-01-24T22:09:35.1570228Z [0m[34m[build][0m [1m[92m   Compiling[0m fancy_rust_app v0.1.0 (/home/runner/work/fancy_rust_app/fancy_rust_app)
2026-01-24T22:09:35.1782984Z [0m[34m[build][0m [1m[91merror[0m[1m: unused variable: `unused_variable`[0m
2026-01-24T22:09:35.1784347Z [0m[34m[build][0m  [1m[94m--> [0msrc/main.rs:2:9
2026-01-24T22:09:35.1785277Z [0m[34m[build][0m   [1m[94m|[0m
2026-01-24T22:09:35.1786581Z [0m[34m[build][0m [1m[94m2[0m [1m[94m|[0m     let unused_variable = 42;  // Clippy will warn about unused variable
2026-01-24T22:09:35.1788606Z [0m[34m[build][0m   [1m[94m|[0m         [1m[91m^^^^^^^^^^^^^^^[0m [1m[91mhelp: if this is intentional, prefix it with an underscore: `_unused_variable`[0m
2026-01-24T22:09:35.1789899Z [0m[34m[build][0m   [1m[94m|[0m
2026-01-24T22:09:35.1799289Z [0m[34m[build][0m   [1m[94m= [0m[1mnote[0m: `-D unused-variables` implied by `-D warnings`
2026-01-24T22:09:35.1800953Z [0m[34m[build][0m   [1m[94m= [0m[1mhelp[0m: to override `-D warnings` add `#[allow(unused_variables)]`
2026-01-24T22:09:35.1804755Z [0m[34m[build][0m 
2026-01-24T22:09:35.1842960Z [0m[34m[build][0m [1m[91merror[0m: could not compile `fancy_rust_app` (bin "fancy_rust_app") due to 1 previous error
2026-01-24T22:09:35.2384288Z [0m[35m[lint][0m [1m[92m    Checking[0m fancy_rust_app v0.1.0 (/home/runner/work/fancy_rust_app/fancy_rust_app)
2026-01-24T22:09:35.2658035Z [0m[35m[lint][0m [1m[91merror[0m[1m: unused variable: `unused_variable`[0m
2026-01-24T22:09:35.2658862Z [0m[35m[lint][0m  [1m[94m--> [0msrc/main.rs:2:9
2026-01-24T22:09:35.2659401Z [0m[35m[lint][0m   [1m[94m|[0m
2026-01-24T22:09:35.2660308Z [0m[35m[lint][0m [1m[94m2[0m [1m[94m|[0m     let unused_variable = 42;  // Clippy will warn about unused variable
2026-01-24T22:09:35.2661782Z [0m[35m[lint][0m   [1m[94m|[0m         [1m[91m^^^^^^^^^^^^^^^[0m [1m[91mhelp: if this is intentional, prefix it with an underscore: `_unused_variable`[0m
2026-01-24T22:09:35.2662870Z [0m[35m[lint][0m   [1m[94m|[0m
2026-01-24T22:09:35.2663703Z [0m[35m[lint][0m   [1m[94m= [0m[1mnote[0m: `-D unused-variables` implied by `-D warnings`
2026-01-24T22:09:35.2664853Z [0m[35m[lint][0m   [1m[94m= [0m[1mhelp[0m: to override `-D warnings` add `#[allow(unused_variables)]`
2026-01-24T22:09:35.2665662Z [0m[35m[lint][0m 
2026-01-24T22:09:35.2679388Z [0m[35m[lint][0m [1m[91merror[0m[1m: manual implementation of an assign operation[0m
2026-01-24T22:09:35.2680265Z [0m[35m[lint][0m  [1m[94m--> [0msrc/main.rs:4:5
2026-01-24T22:09:35.2680811Z [0m[35m[lint][0m   [1m[94m|[0m
2026-01-24T22:09:35.2681615Z [0m[35m[lint][0m [1m[94m4[0m [1m[94m|[0m     x = x + 5;  // Clippy will warn about unnecessary mut
2026-01-24T22:09:35.2682692Z [0m[35m[lint][0m   [1m[94m|[0m     [1m[91m^^^^^^^^^[0m [1m[91mhelp: replace it with: `x += 5`[0m
2026-01-24T22:09:35.2683439Z [0m[35m[lint][0m   [1m[94m|[0m
2026-01-24T22:09:35.2685040Z [0m[35m[lint][0m   [1m[94m= [0m[1mhelp[0m: for further information visit https://rust-lang.github.io/rust-clippy/rust-1.93.0/index.html#assign_op_pattern
2026-01-24T22:09:35.2693581Z [0m[35m[lint][0m   [1m[94m= [0m[1mnote[0m: `-D clippy::assign-op-pattern` implied by `-D warnings`
2026-01-24T22:09:35.2694991Z [0m[35m[lint][0m   [1m[94m= [0m[1mhelp[0m: to override `-D warnings` add `#[allow(clippy::assign_op_pattern)]`
2026-01-24T22:09:35.2695802Z [0m[35m[lint][0m 
2026-01-24T22:09:35.2743107Z [0m[35m[lint][0m [1m[91merror[0m: could not compile `fancy_rust_app` (bin "fancy_rust_app") due to 2 previous errors
2026-01-24T22:09:35.2791547Z [2mFinished in 242.9ms[0m
2026-01-24T22:09:35.2793245Z [0m[34m[build][0m [31mERROR[0m task failed
2026-01-24T22:09:35.2823204Z ##[error]Process completed with exit code 101.
... (omitted later log/steps for brevity) ...
```

The `mise run ci` build ran two commands:
  `cargo build --release` and `cargo clippy -- -D warnings`,
  and both produced errors.
The log output shows the relevant error messages
  and their locations in the source code
  but does not include the exit codes for the failed commands,
  only the exit code for the entire mise run.

Note that GitHub Actions log lines are prefixed with timestamps
  and often contain ANSI color codes.

**TOON Output:**

```toon
build_issues[2]:
  - description: "Unused variable `sprocket` in src/main.rs:2"
    type: lint
    source_locations[1]:
      - src/main.rs:2
    relevant_commands[2]{command,cwd,exit_code}:
      cargo clippy -- -D warnings,/home/runner/work/fancy_rust_app/fancy_rust_app,
      cargo build --release,/home/runner/work/fancy_rust_app/fancy_rust_app,
    relevant_output[2]:
      - snippet: |
          [lint] error: unused variable: `sprocket`
          [lint]  --> src/main.rs:2:9
          [lint]   |
          [lint] 2 |     let sprocket = 42;  // Clippy will warn about unused variable
          [lint]   |         ^^^^^^^^ help: if this is intentional, prefix it with an underscore: `_sprocket`
          [lint]   |
          [lint]   = note: `-D unused-variables` implied by `-D warnings`
          [lint]   = help: to override `-D warnings` add `#[allow(unused_variables)]`
        source: https://github.com/cool_user/fancy_rust_app/commit/c4a3d81c7fd46b52c95aeba4d3e705ac08551c93/checks/61374132898/logs
        source_line_number_start: 1015
      - snippet: |
          [build] error: unused variable: `sprocket`
          [build]  --> src/main.rs:2:9
          [build]   |
          [build] 2 |     let sprocket = 42;  // Clippy will warn about unused variable
          [build]   |         ^^^^^^^^ help: if this is intentional, prefix it with an underscore: `_sprocket`
          [build]   |
          [build]   = note: `-D unused-variables` implied by `-D warnings`
          [build]   = help: to override `-D warnings` add `#[allow(unused_variables)]`
        source: https://github.com/cool_user/fancy_rust_app/commit/c4a3d81c7fd46b52c95aeba4d3e705ac08551c93/checks/61374132898/logs
        source_line_number_start: 1026
  - description: "Manual implementation of an assign operation in src/main.rs:4"
    type: lint
    source_locations[1]:
      - src/main.rs:4
    relevant_commands[1]{command,cwd,exit_code}:
      cargo clippy -- -D warnings,/home/runner/work/fancy_rust_app/fancy_rust_app,
    relevant_output[1]:
      - snippet: |
          [lint] error: manual implementation of an assign operation
          [lint]  --> src/main.rs:4:5
          [lint]   |
          [lint] 4 |     x = x + 5;  // Clippy will warn about unnecessary mut
          [lint]   |     ^^^^^^^^^ help: replace it with: `x += 5`
          [lint]   |
          [lint]   = help: for further information visit https://rust-lang.github.io/rust-clippy/rust-1.93.0/index.html#assign_op_pattern
          [lint]   = note: `-D clippy::assign-op-pattern` implied by `-D warnings`
          [lint]   = help: to override `-D warnings` add `#[allow(clippy::assign_op-pattern)]`
        source: https://github.com/cool_user/fancy_rust_app/commit/c4a3d81c7fd46b52c95aeba4d3e705ac08551c93/checks/61374132898/logs
        source_line_number_start: 1035
```

Note how the "Unused variable" issue
  combines both the lint and build command outputs,
  since both commands evidenced that same issue.

## What to Extract

You should extract the following information
  for each failure found during your analysis...

### 1. Failure Metadata

- **`description`**:
  A brief human-readable description of the failure,
    including the test name or build step that failed,
    and the file and line number if applicable.
- **`type`**:
  The type of failure: one of "test", "lint", "build", "type_check", or "other".
- **`source_locations`**:
  The file paths and line numbers where the failure occurred,
    in the format `path/to/file:line_number`.
  If multiple locations are relevant,
    list them all,
    ordering them with the most relevant first.

### 2. Build Commands

Identify what commands were run. Look for:

- Task runner invocations (`npm test`, `cargo build`, `mise run :test`).
- CI tool output (`==> Running task: build`).
- Shell commands in logs.

For each command, extract:

- **`command`**: The actual command string.
- **`cwd`**: Working directory if available.
- **`exit_code`**: The exit code of the command, if available.

### 3. Relevant Output Snippets

From the logs and other outputs,
  extract snippets that are relevant to each failure.
These would include any of the following that are present:

- Error messages.
- Stack traces.
- Compiler output lines.
- Test failure summaries.
- Lint error lines.
- Type error messages.
- Any other lines that help explain the failure.
  
For each such snippet, extract:

- **`snippet`**: The actual, raw text snippet.
- **`source`**: The source of the snippet.
  - For console logs that were captured by the agent locally
      and not saved to a file,
      use `console_output`.
  - For logs or other files that are available locally,
      use the file path relative to the repository root, e.g.:
    - `./reports/junit_report.xml`
  - For URLs, use the URL string, e.g.:
    - `https://api.github.com/repos/cool_user/neat_npm_project/actions/runs/123456789/logs`
    - `https://github.com/cool_user/neat_npm_project/actions/artifacts/123/test-results.xml`
- **`source_line_number_start`**: The starting line number of the snippet in its source.

### Quick Reference

For most cases, look for these common patterns:

**File and line locations:**

- TypeScript: `src/api.ts:42` or `src/api.ts(42,15)`.
- Rust: `--> src/main.rs:42:9`.
- Python: `src/api.py:42:`.

**Error indicators:**

- Lines starting with "error:", "Error:", "FAIL", "FAILED", "✕", "●", "WARNING" and similar.
  - Builds are oftentime run in a mode that treats warnings as errors.
- Stack traces with "at [location]".
- Compiler output with `-->` or `error[E...]`.

**Extract from each failure:**

1. **Type**: `test`/`lint`/`build`/`type_check`, based on command.
2. **Location**: First file:line reference found.
3. **Messages**: Key error lines (2-3 snippets max, not full output).

## Common Patterns

### Stack Traces

For stack traces, include only the relevant in `relevant_output`, not the entire trace:

```relevant_output[2]:
     - snippet: |
         TypeError: Cannot read property 'id' of null
           at handler (src/api.ts:89)
       source: console_output
       source_line_number_start: 128
     - snippet: |
         at processUser (src/auth.ts:42)
       source: console_output
       source_line_number_start: 135  
```

### Discontiguous Errors

Use separate `relevant_output` entries for non-adjacent error snippets:

```relevant_output[3]:
     - snippet: |
         Error in src/api.ts:42
       source: console_output
       source_line_number_start: 130
     - snippet: |
         Caused by: Database connection failed
       source: console_output
       source_line_number_start: 140
     - snippet: |
         Help: Check DATABASE_URL environment variable
       source: console_output
       source_line_number_start: 150
```

## Common Mistakes

**Including full logs in messages:**

- Problem: Makes output too verbose.
- Fix: Extract only key error lines, not full traces.

**Missing source and `source_line_number_start` locations:**

- Problem: Hard to find where to fix.
- Fix: Parse stack traces and error messages for locations.

**Wrong failure type:**

- Problem: Misleading categorization.
- Fix: Use test/lint/build/type_check based on error source.

## Edge Cases

**No failures found but exit code non-zero:**

- Look for infrastructure failures (out of memory, timeout, etc.).
- Return type: "other" with available context.

**Multiple failures in same file:**

- Create separate failure entries for each.
- Include line numbers to distinguish.
