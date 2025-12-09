---
name: getting-pr-workflow-results
description: Use when needing workflow job results and log commands from PR - automatically waits for workflows to complete, then returns job summaries with gh commands to retrieve logs without loading large logs into context
---

# Getting PR Workflow Results

## Overview

Get workflow job results and provide commands to retrieve logs, without loading logs into main context.

**Core principle:** Return job summaries + retrieval commands, not actual logs. Let main agent decide what to fetch.

**Automatic dependency:** This skill automatically waits for workflows to complete before fetching results.

## When to Use

Use when you need:
- Summary of which jobs passed/failed
- Commands to retrieve specific job logs
- Suggestions for searching logs (grep patterns)

**When NOT to use:**
- Need to actually read logs (use returned commands in main context)

## Workflow

### Step 0: Wait for Workflows to Complete (Automatic)

Before fetching results, ensure all workflows are complete by following the `awaiting-pr-workflows` skill.

**Skill location:** `~/.claude/skills/awaiting-pr-workflows/SKILL.md`

Read and execute that skill's workflow to:
- Check for unpushed commits
- Verify PR exists and commit correlation
- Wait for workflows to start (up to 30s)
- Wait for workflows to complete (up to 20 minutes)

Once all workflows are complete, proceed to Step 1 below.

### Step 1: Get Workflow Runs for PR Commit

```bash
# Get PR's head commit
PR_COMMIT=$(gh pr view $PR_NUM --json headRefOid -q '.headRefOid')

# List workflow runs for that commit
gh run list --commit $PR_COMMIT --json databaseId,name,status,conclusion,workflowName,createdAt
```

### Step 2: For Each Run, Get Job Details

```bash
RUN_ID=<from step 1>

# Get jobs in this run
gh run view $RUN_ID --json jobs --jq '.jobs[] | {
  name: .name,
  conclusion: .conclusion,
  url: .html_url,
  steps: [.steps[] | select(.conclusion == "failure") | .name]
}'
```

### Step 3: Build Return Summary

For each job, return:

1. **Job name and result**
2. **Location in repo** (workflow file path + line if applicable)
3. **gh command** to retrieve logs
4. **grep suggestions** for common issues

## Return Format

```markdown
PR #{number} Workflow Results (commit {sha}):

## ✅ Passing Jobs (N)
- Backend Tests
- iOS Lint
- workstation-test-e2e

## ❌ Failing Jobs (N)

### 1. iOS Test (failed after 7m28s)
**Workflow:** `.github/workflows/ci.yml:45`
**Retrieve logs:**
```bash
gh run view 19727163744 --log-failed
# OR specific job:
gh run view 19727163744 --job 56520688201 --log
```

**Search suggestions:**
```bash
# Find errors:
gh run view 19727163744 --log | grep -i error

# Find test failures:
gh run view 19727163744 --log | grep -E "(FAILED|failed|✗)"

# Find specific test:
gh run view 19727163744 --log | grep "testHealthCheckE2E"
```

### 2. workstation-lint (failed after 35s)
**Workflow:** `.github/workflows/workstation-ci.yml:12`
**Retrieve logs:**
```bash
gh run view 19727163743 --log-failed
```

**Search suggestions:**
```bash
# Find linting errors:
gh run view 19727163743 --log | grep -E "(error|warning)"

# Find formatting issues:
gh run view 19727163743 --log | grep "Diff in"
```

---

**Summary:** 2 failures, 7 passing
**All results:** https://github.com/{owner}/{repo}/pull/{number}/checks
```

## Finding Workflow File Locations

**Method 1: Via gh API**
```bash
gh api repos/{owner}/{repo}/actions/workflows \
  --jq '.workflows[] | {name: .name, path: .path}'
```

**Method 2: Local search**
```bash
find .github/workflows -name "*.yml" -o -name "*.yaml"
```

**Method 3: From run metadata**
```bash
gh run view $RUN_ID --json workflowName,workflowDatabaseId
# Then map to file using gh api
```

## Common Log Search Patterns

### For Test Failures
```bash
grep -E "(FAILED|✗|Error:|Exception)"
grep -B 5 -A 10 "test.*failed"  # Context around failures
grep "exit code [1-9]"           # Non-zero exits
```

### For Build Failures
```bash
grep -i "error:"
grep "fatal:"
grep "npm ERR!"
grep "cargo.*error"
```

### For Lint Failures
```bash
grep "warning:"
grep "Diff in"
grep "expected.*found"
```

## Example Implementation

```bash
#!/bin/bash
# Run in subagent

PR_NUM=$1
PR_COMMIT=$(gh pr view $PR_NUM --json headRefOid -q '.headRefOid')

# Get all runs for this commit
RUNS=$(gh run list --commit $PR_COMMIT --json databaseId,conclusion,name)

# For each run, get job details
echo "$RUNS" | jq -r '.[] | .databaseId' | while read RUN_ID; do
  gh run view $RUN_ID --json jobs --jq '.jobs[] | {
    name: .name,
    conclusion: .conclusion,
    url: .html_url
  }'
done

# Format and return (pseudo-code)
# - Group by passing/failing
# - Add gh commands for each
# - Add grep suggestions based on job type
```

## Common Mistakes

**Loading logs into context**
- **Problem:** Logs can be 100k+ tokens
- **Fix:** Return commands, not logs

**Not providing grep patterns**
- **Problem:** User has to figure out how to search
- **Fix:** Include job-type-specific grep examples

**Checking runs without commit correlation**
- **Problem:** May return results for old commits
- **Fix:** Always use `--commit $SHA` flag

## Quick Reference

| Task | Command |
|------|---------|
| List runs for commit | `gh run list --commit $SHA` |
| Get run details | `gh run view $RUN_ID --json jobs` |
| Get failed logs only | `gh run view $RUN_ID --log-failed` |
| Get specific job log | `gh run view $RUN_ID --job $JOB_ID --log` |
| List workflows | `gh api repos/{owner}/{repo}/actions/workflows` |

## Use Subagents

**CRITICAL:** Always run in subagent.

```
Use Task tool with subagent_type='general-purpose'.
Give them this skill and the PR number.
They return job summaries + commands.
```

**Why:** Prevents loading massive logs into main context. Main agent gets actionable commands instead.
