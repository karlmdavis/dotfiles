---
name: getting-feedback-remote
description: Orchestrate complete PR feedback - waits for workflows, fetches build results and reviews, returns unified TOON summary without consuming main context
---

# Getting Feedback Remote

## Overview

Comprehensive PR feedback orchestrator that combines workflow results, build failures, and review suggestions into a single unified TOON output.

Core principle: Run as subagent to gather all PR feedback without consuming main context tokens.

What it does:
1. Wait for all PR workflows to complete.
2. Fetch and parse build/test failures from failed workflows.
3. Fetch and parse review feedback (Claude bot + GitHub reviews + unresolved threads).
4. Combine everything into unified TOON summary.

Output: Complete PR feedback ready for main context to address.

## When to Use

Use when you need:
- Complete picture of PR status (workflows + reviews).
- All feedback in one place before starting fixes.
- Token-efficient PR quality check.

When NOT to use:
- No PR exists yet (create PR first).
- Just need workflow status (use `awaiting-pr-workflow-results`).
- Just need reviews (use `getting-reviews-remote`).

## Workflow

This skill orchestrates other skills in sequence:

### Step 1: Wait for Workflows

Use `awaiting-pr-workflow-results` skill to:
- Check for unpushed commits.
- Verify PR exists and commit correlation.
- Wait for workflows to complete (up to 20 minutes).
- Get workflow status and URLs.

If workflows haven't started or commits are unpushed, return early with recommendation to push.

### Step 2: Fetch Build Results (if failures exist)

For each failed workflow:
1. Use `getting-build-results-remote` to fetch raw logs.
2. Use `parsing-build-results` to extract structured failures.

### Step 3: Fetch and Parse Reviews

1. Use `getting-reviews-remote` to fetch:
   - Claude bot review comments (after commit push).
   - GitHub PR reviews (for current commit).
   - Unresolved threads from earlier commits.

2. Use `parsing-review-suggestions` to parse into structured issues.

### Step 4: Combine and Return

Merge all feedback into unified TOON structure:
- Workflow summary.
- Build failures (parsed and categorized).
- Review issues (categorized by severity).
- Overall counts and status.
- Recommendation for next steps.

## Return Format

```toon
status: needs_attention
pr_number: 123
current_commit: a1b2c3d

workflows:
  complete: true
  wait_time_seconds: 342
  results[3]:
    name: CI Tests
    status: completed
    conclusion: failure
    duration_seconds: 298
    url: https://github.com/.../runs/19727163744

    name: Lint
    status: completed
    conclusion: success
    duration_seconds: 45
    url: https://github.com/.../runs/19727163745

    name: Type Check
    status: completed
    conclusion: success
    duration_seconds: 23
    url: https://github.com/.../runs/19727163746

build_results:
  status: fail_related

  ci_commands[2]:
    id: 1
    command: npm test
    exit_code: 1
    duration_seconds: 298

    id: 2
    command: npm run type-check
    exit_code: 0
    duration_seconds: 23

  failures[2]:
    type: test
    location: tests/api.test.ts:42
    source_command_id: 1
    related_to_changes: true
    reasoning: |
      Test file tests/api.test.ts was modified in this commit.
    messages[2]:
      |
        FAIL tests/api.test.ts
          ● should handle null user
      |
        TypeError: Cannot read property 'id' of null
          at handler (src/api.ts:89)

    type: test
    location: tests/auth.test.ts:15
    source_command_id: 1
    related_to_changes: false
    reasoning: |
      Test file tests/auth.test.ts was not modified in this commit.
      Pre-existing failure.
    messages[1]:
      |
        FAIL tests/auth.test.ts
          ● should validate user token

  recommendation: fix_related_first

reviews:
  status: success
  pr_number: 123
  current_commit: a1b2c3d

  claude_bot_review:
    updated_at: 2026-01-04T15:30:00Z
    link: https://github.com/.../issuecomment-123
    overall_summary: |
      Overall the changes look solid! Found 2 critical issues.
      Recommendation: Address critical issues, then ready to merge.

    issues[2]:
      severity: critical
      code_references[1]:
        file: src/api.ts
        line: 42
      description: |
        **Null pointer risk**
        The user object may be null here. Add null check.

      severity: suggestion
      code_references[1]:
        file: src/utils.ts
        line_range: 15-20
      description: |
        **Consider refactoring**
        Extract validation logic into separate function.

  github_reviews[1]:
    reviewer: alice
    state: changes_requested
    summary: |
      Nice work! Add error handling to database calls.
    inline_comments[1]:
      code_references[1]:
        file: src/api.ts
        line: 89
      description: |
        Error handling missing in database call.

  unresolved_earlier[1]:
    link: https://github.com/.../discussion_r123
    reviewer: alice
    code_references[1]:
      file: src/auth.ts
      line_range: 15-18
    summary: Handle edge case when user validation fails

summary:
  total_workflow_failures: 1
  total_build_failures: 2
  total_review_issues: 4
  unresolved_earlier_count: 1
  overall_status: needs_attention
  recommendation: |
    Fix 2 related build failures and 2 critical review issues before merge.
    Also address 1 unresolved earlier comment.
```

## Implementation Steps

As an agent executing this skill, follow these steps:

Copy this checklist to track progress (helps maintain focus during multi-step orchestration):

```
Feedback Gathering Progress:
- [ ] Step 1: Get PR context (number, commit)
- [ ] Step 2: Wait for workflows to complete
- [ ] Step 3: Fetch build results for failed workflows
- [ ] Step 4: Fetch and parse reviews
- [ ] Step 5: Build unified output
- [ ] Step 6: Return to main context
```

### 1. Get PR Context

```bash
# Get PR number and commit
PR_NUM=$(gh pr view --json number -q '.number')
COMMIT=$(git rev-parse HEAD)
COMMIT_SHORT=$(git rev-parse --short HEAD)
```

### 2. Wait for Workflows

Run `awaiting-pr-workflow-results` skill:

```bash
cd ~/.claude/skills/awaiting-pr-workflow-results
scripts/check_pr_workflows.py
```

Parse the TOON output. If status is:
- `no_pr` → Return with recommendation to create PR
- `warning` (unpushed) → Return with recommendation to push
- `timeout` → Return with partial results and timeout notice
- `success` or `failure` → Continue to next step

### 3. Fetch Build Results for Failed Workflows

Extract failed workflow run IDs from awaiting skill output.

For each failed workflow:

```bash
cd ~/.claude/skills/getting-build-results-remote
scripts/fetch_workflow_logs.py <run_id1> <run_id2> ...
```

Take the raw logs and use `parsing-build-results` skill to parse them.

**Note:** Provide context about changed files:
```bash
# Get changed files for relatedness analysis
git diff main...HEAD --name-only
```

### 4. Fetch and Parse Reviews

```bash
cd ~/.claude/skills/getting-reviews-remote
scripts/fetch_pr_reviews.py $PR_NUM $COMMIT
```

Take the raw review text and use `parsing-review-suggestions` skill to parse it.

### 5. Build Unified Output

Combine all outputs into unified TOON structure as shown in Return Format above.

Calculate summary:.
- Count total failures (by type).
- Count review issues (by severity).
- Count unresolved earlier comments.
- Determine overall status
- Generate recommendation.

### 6. Return to Main Context

Output the complete unified TOON to stdout for main context consumption.

## Overall Status Values

- `all_clear` - All workflows passed, no review issues
- `needs_attention` - Failures or critical review issues
- `warnings_only` - Minor issues or suggestions only
- `blocked` - Can't proceed (no PR, unpushed commits, timeout)

## Recommendation Generation

Based on the feedback, generate actionable recommendation:

All clear:
```
All checks passed! Ready to merge.
```

Build failures only:
```
Fix 2 related build failures before merge.
1 unrelated failure can be addressed separately.
```

Review issues only:
```
Address 2 critical review issues before merge.
3 suggestions can be addressed optionally.
```

Both:
```
Fix 2 related build failures and 2 critical review issues before merge.
Also address 1 unresolved earlier comment.
```

## Usage Pattern

CRITICAL: Always run in subagent.

```markdown
Use Task tool with subagent_type='general-purpose':

"Use the getting-feedback-remote skill to gather complete PR feedback.
Run through all steps: wait for workflows, fetch build results for any
failures, fetch and parse reviews, and return unified TOON output with
complete summary and recommendations."
```

## Integration with Commands

Used by:
- `/quality-triage-pr` command - Main consumer

Why run in subagent:
- Waiting for workflows can take up to 20 minutes - the wait happens in subagent context, not main.
- Raw logs can be 50k+ tokens - never loaded into main context.
- Raw reviews can be 20k+ tokens - computed in subagent, only summary returned.
- Main context only needs the structured summary (~2-5k tokens vs 50-70k raw).

## Common Mistakes

Not waiting for workflows:
- Problem: Try to fetch logs while workflows still running
- Fix: Always run awaiting-pr-workflow-results first

Fetching logs for passing workflows:
- Problem: Waste time and tokens
- Fix: Only fetch logs for failed workflows

Not providing changed files context:
- Problem: Can't determine if failures are related to changes
- Fix: Include `git diff --name-only` in context for parsing skill

Returning raw data instead of unified TOON:
- Problem: Main context gets overwhelmed
- Fix: Always merge and summarize into unified structure

## Error Handling

If awaiting-pr-workflow-results fails:
- Return status: "blocked"
- Include error message
- Recommendation: Check git/gh setup

If getting-build-results-remote fails:
- Note which workflows couldn't be fetched
- Continue with reviews
- Include partial results

If getting-reviews-remote fails:
- Continue with build results
- Note that review data unavailable
- Include partial results

Always return TOON output, even on partial failure. Main context needs actionable information.

## Quick Reference

| Step | Skill | Purpose |
|------|-------|---------|
| 1 | awaiting-pr-workflow-results | Wait for workflows |
| 2 | getting-build-results-remote | Fetch logs for failed workflows |
| 3 | parsing-build-results | Parse logs into failures |
| 4 | getting-reviews-remote | Fetch review feedback |
| 5 | parsing-review-suggestions | Parse reviews into issues |
| 6 | (this skill) | Combine into unified output |
