---
name: getting-build-results-remote
description: Fetch workflow logs from GitHub PR workflows - takes run IDs from awaiting-pr-workflow-results and returns raw logs for parsing
context: fork
---

# Getting Build Results Remote

## Overview

Fetch raw workflow logs from GitHub for failed PR workflows.

Core principle: Run in subagent to fetch logs without consuming main context tokens.

**Input:** Workflow run IDs (from `awaiting-pr-workflow-results` skill)

Output: TOON-formatted raw logs for each failed workflow

## When to Use

Use when you need:
- Raw workflow logs for failed PR checks
- Build output from GitHub Actions workflows
- Test failure logs from CI runs

When NOT to use:
- Need parsed/structured failures (use `parsing-build-results` after this)
- Workflows still running (use `awaiting-pr-workflow-results` first)

## Workflow

### Step 1: Get Workflow Run IDs

First use `awaiting-pr-workflow-results` to get run IDs:

```toon
workflows:
  complete: true
  results[2]:
    name: CI Tests
    status: completed
    conclusion: failure
    url: https://github.com/.../runs/19727163744
```

Extract the run ID from the URL (last segment) or use `databaseId` if available.

### Step 2: Fetch Logs

Run the script with run IDs as arguments:

```bash
scripts/fetch_workflow_logs.py 19727163744 19727163745
```

### Step 3: Use Output for Parsing

Pass the raw logs to `parsing-build-results` skill (agent-driven) to extract structured failures.

## Return Format

```toon
status: success
message: Fetched logs for 2 workflow run(s)

workflows[2]:
  run_id: 19727163744
  run_name: CI Tests
  conclusion: failure

  jobs[3]:
    job_id: 56520688201
    job_name: test (ubuntu-latest)
    conclusion: failure
    log_content: |
      Run npm test
      > test
      > jest

      FAIL tests/api.test.ts
        ● should handle null user
          TypeError: Cannot read property 'id' of null
            at handler (src/api.ts:89)

      Tests: 1 failed, 47 passed

  run_id: 19727163745
  run_name: Lint
  conclusion: success

  jobs[1]:
    job_id: 56520688202
    job_name: lint
    conclusion: success
    log_content: (skipped - job passed)
```

## Usage Pattern

**Context:** This skill uses `context: fork` to always run in isolated subagent context.

When invoking via Task tool, the context field ensures automatic isolation.

When invoking script directly via Bash, caller is responsible for running in appropriate context.

```markdown
Use Task tool with subagent_type='general-purpose':

"Use the getting-build-results-remote skill to fetch logs for workflow runs
19727163744 and 19727163745. Run scripts/fetch_workflow_logs.py with these IDs
and return the complete TOON output."
```

## Integration with Other Skills

**Typical workflow:**
1. `awaiting-pr-workflow-results` → Get run IDs for failed workflows
2. `getting-build-results-remote` → Fetch raw logs (this skill)
3. `parsing-build-results` → Parse logs into structured failures
4. `getting-feedback-remote` → Combine with review feedback

## Common Mistakes

**Fetching logs for all workflows**
- Problem: Wastes time and tokens fetching logs for passing workflows
- Fix: Script only fetches full logs for failed/cancelled jobs

**Running in main context**
- Problem: Log output can be 50k+ tokens
- Fix: Always run in subagent, return TOON to main context

**Not waiting for workflows to complete**
- Problem: Logs may be incomplete or unavailable
- Fix: Use `awaiting-pr-workflow-results` first

## Quick Reference

| Task | Command |
|------|---------|
| Fetch logs for one run | `scripts/fetch_workflow_logs.py 19727163744` |
| Fetch logs for multiple runs | `scripts/fetch_workflow_logs.py 19727163744 19727163745` |
| Get run ID from awaiting skill | Extract from `workflows.results[].url` or use `databaseId` |
