---
name: using-ios-xcresult-artifacts
description: Use when analyzing iOS test xcresult bundles from happy-focus project - extracts test failures, screenshots, and diagnostics from xcresult format used by Xcode/xcodebuild
---

# Using iOS xcresult Artifacts

## Overview

Analyze xcresult bundles from iOS tests in the happy-focus project to extract failures, logs, and diagnostics.

**Core principle:** xcresult is a binary format. Use `xcrun xcresulttool` to extract JSON, then parse.

**Project context:** happy-focus iOS tests create xcresult artifacts in CI that contain:
- Test pass/fail results
- Screenshots from UI tests
- Console output
- Crash logs (if app crashed during tests)

## When to Use

Use after downloading iOS test artifacts from CI when you need:
- Detailed test failure information
- Screenshots from failing UI tests
- App crash logs
- Console output from test runs

**Prerequisite:** Use `getting-pr-artifacts` to download the xcresult first.

## xcresult Structure

```
Test-HappyFocus-{date}.xcresult/
├── database.sqlite3          # Test metadata
├── Data/
│   ├── data.0~{hash}        # Binary test data
│   └── refs.0~{hash}        # Binary references
└── (other binary files)
```

## Extracting Information

### Step 1: Get Root Object

```bash
XCRESULT_PATH="/path/to/Test-HappyFocus-2025.11.27_06-25-45-+0000.xcresult"

# Get root test summary
xcrun xcresulttool get object --legacy --format json \
  --path "$XCRESULT_PATH" > root.json
```

### Step 2: Find Test Failures

```bash
# Extract test failure summaries
cat root.json | jq -r '.issues.testFailureSummaries._values[]? | {
  test: .testCaseName._value,
  message: .message._value,
  file: .documentLocationInCreatingWorkspace.url._value
}'
```

### Step 3: Get Detailed Test Results

```bash
# Get tests reference ID
TESTS_REF=$(cat root.json | jq -r '.actions._values[0].actionResult.testsRef.id._value')

# Get test details
xcrun xcresulttool get object --legacy --format json \
  --path "$XCRESULT_PATH" \
  --id "$TESTS_REF" > tests.json
```

### Step 4: Extract Specific Test Details

```bash
# Example: Find testHealthCheckE2E details
cat tests.json | jq -r '.summaries._values[0].testableSummaries._values[0].tests._values[0].subtests._values[0].subtests._values[0].subtests._values[] | select(.name._value == "testHealthCheckE2E()") | .summaryRef.id._value'

# Then get that summary
xcrun xcresulttool get object --legacy --format json \
  --path "$XCRESULT_PATH" \
  --id "{summary-ref-id}" > test-detail.json
```

### Step 5: Extract Screenshots/Attachments

```bash
# List activities that might have screenshots
cat test-detail.json | jq -r '.activitySummaries._values[]? | {
  title: .title._value,
  hasAttachments: (.attachments._values | length > 0)
}'

# Extract attachment (if present)
# Note: Attachments are stored as binary references
# May need to export using xcresulttool export
xcrun xcresulttool export --type file \
  --path "$XCRESULT_PATH" \
  --id "{attachment-id}" \
  --output-path screenshot.png
```

## Common Test Failure Patterns in happy-focus

### Pattern 1: App Launch Timeout

**Error:** `Failed to get background assertion for target app`

**What to check:**
```bash
# Look for .task or .onAppear issues
# Check if app is making network calls during launch
# Look for ContentView startup logs
```

**Related files:**
- `ios/HappyFocus/HappyFocus/ContentView.swift`
- `ios/HappyFocus/HappyFocus/Services/HealthService.swift`

### Pattern 2: Backend Connection Issues

**Error:** `Connection refused` or `Backend health check failed`

**What to check:**
```bash
# Check if backend was running during test
# Look for "Waiting for backend" messages
# Check backend startup logs in CI
```

**Related files:**
- `ios/HappyFocus/HappyFocusUITests/HappyFocusUITests.swift` (line 17: waitForBackendReady)

### Pattern 3: Formatting Issues

**Error:** `Diff in {file}` from cargo fmt

**What to check:**
```bash
# Run cargo fmt locally
# Check import ordering in Rust files
```

**Common culprit:** Import order in workstation Rust code

## Quick Analysis Script

```bash
#!/bin/bash
# Quick xcresult failure analysis

XCRESULT="$1"

echo "=== Test Failures ==="
xcrun xcresulttool get object --legacy --format json --path "$XCRESULT" | \
  jq -r '.actions._values[0].actionResult.issues.testFailureSummaries._values[]? |
    "\(.testCaseName._value): \(.message._value)"'

echo ""
echo "=== Test Duration ==="
# TODO: Parse duration from test metadata
# xcrun xcresulttool get object --legacy --format json --path "$XCRESULT" | \
#   jq -r '.actions._values[0].actionResult.testsRef | ...'

echo ""
echo "=== Activities ==="
# Extract test activities to see where it got stuck
# (More complex - requires getting test summaries)
```

## Return Format

When analyzing xcresult in a subagent, return:

```markdown
iOS Test Results Analysis (from xcresult):

## Failed Tests

### testHealthCheckE2E (44.69s)
**Error:** Failed to get background assertion for target app with pid 8823: Timed out while acquiring background assertion.

**Location:** `ios/HappyFocus/HappyFocusUITests/HappyFocusUITests.swift:85`

**Test Activities:**
1. Start Test (0.00s)
2. Set Up (0.93s) - Backend check passed ✓
3. Launch app (1.26s) - Started but never completed
4. [43 second gap - no activity logged]
5. Tear Down (44.32s) - After timeout

**Probable Cause:** App hung during launch, likely in ContentView .task block making network request.

**Suggested Fix:**
- Check `ContentView.swift:30-32` (.task modifier)
- Consider deferring network call or adding timeout

## Screenshots

No screenshots captured (test failed before reaching screenshot steps).

## Console Output

[Key console messages if available in xcresult]

---

**Full xcresult location:** {path}
**Analyze further:** Use xcrun xcresulttool commands above
```

## Common Mistakes

**Not using --legacy flag**
- **Problem:** xcresulttool get object fails without --legacy in newer Xcode
- **Fix:** Always use `--legacy --format json`

**Trying to parse binary Data files**
- **Problem:** Files in Data/ are binary, not text
- **Fix:** Use xcresulttool, don't cat the files

**Not checking test activities**
- **Problem:** Miss where test actually got stuck
- **Fix:** Always check activitySummaries to see test progression

## Quick Reference

| Task | Command |
|------|---------|
| Get root object | `xcrun xcresulttool get object --legacy --format json --path {path}` |
| Get specific object | Add `--id "{id}"` to above command |
| Extract failures | `jq '.issues.testFailureSummaries._values[]'` |
| Export attachment | `xcrun xcresulttool export --type file --path {path} --id {id}` |
| List all IDs | `jq '.. | .id?._value? | select(. != null)'` (recursive search) |

## Integration

**Use after:** `getting-pr-artifacts` downloads the xcresult bundle

**Common workflow:**
1. `getting-pr-artifacts` - Get download command
2. Download: `gh run download {run-id} -n ios-e2e-test-results -D /tmp`
3. `using-ios-xcresult-artifacts` - Analyze the bundle
4. Return findings to main context

## Xcode Version Notes

**happy-focus CI uses:** Xcode 26.0.1 (as of 2025-11-08)

**xcresulttool location:** `/Applications/Xcode_26.0.1.app/Contents/Developer/usr/bin/xcresulttool`

**Format changes:** Apple occasionally changes xcresult format. If parsing fails, check Xcode release notes.
