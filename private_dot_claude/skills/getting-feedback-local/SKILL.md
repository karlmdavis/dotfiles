---
name: getting-feedback-local
description: Orchestrate complete local feedback - runs local CI and code review, returns unified TOON summary without consuming main context
---

# Getting Feedback Local

## Overview

Comprehensive local feedback orchestrator that combines local build/test results and code review into a single unified TOON output.

Core principle: Run as subagent to gather all local feedback without consuming main context tokens.

What it does:
1. Run local CI commands (build, test, lint, type-check).
2. Parse build output into structured failures.
3. Perform code review of changes.
4. Parse review feedback into structured issues.
5. Combine everything into unified TOON summary.

Output: Complete local feedback ready for main context to address.

## When to Use

Use when you need:
- Pre-commit verification before creating commits.
- Pre-PR quality check before pushing.
- Quick local feedback loop during development.
- All feedback in one place before addressing issues.

When NOT to use:
- PR already exists (use `getting-feedback-remote`).
- No changes to review.
- Just need build results (use `getting-build-results-local`).
- Just need code review (use `getting-review-local`).

## Workflow

This skill orchestrates other skills in sequence:

### Step 1: Run Local Build

Use `getting-build-results-local` skill to:
1. Read project's CLAUDE.md or README.md for CI commands.
2. Run build/test/lint commands.
3. Capture raw output with exit codes and durations.

### Step 2: Parse Build Results

Use `parsing-build-results` skill to:
1. Extract CI commands and failures from raw output.
2. Identify file:line locations for each failure.
3. Determine if failures are related to current changes.
4. Categorize by type (test, lint, build, type_check).

### Step 3: Perform Code Review

Use `getting-review-local` skill to:
1. Identify changed files (staged or unstaged).
2. Run available review tools or perform own analysis.
3. Return structured review feedback.

### Step 4: Parse Review Feedback

Use `parsing-review-suggestions` skill to:
1. Extract issues from review feedback.
2. Categorize by severity (critical, warning, suggestion).
3. Extract code references for each issue.

### Step 5: Combine and Return

Merge all feedback into unified TOON structure:
- Build command results.
- Build failures (parsed and categorized).
- Review issues (categorized by severity).
- Overall counts and status.
- Recommendation for next steps.

## Return Format

```toon
status: needs_attention
source: local
review_timestamp: 2026-01-04T16:00:00Z

build_results:
  status: fail_related

  ci_commands[2]:
    id: 1
    command: npm run lint
    cwd: /Users/karl/projects/myapp
    exit_code: 0
    duration_seconds: 8

    id: 2
    command: npm test
    cwd: /Users/karl/projects/myapp
    exit_code: 1
    duration_seconds: 25

  failures[1]:
    type: test
    location: tests/api.test.ts:42
    source_command_id: 2
    related_to_changes: true
    reasoning: |
      Test file tests/api.test.ts was modified in staged changes.
    messages[2]:
      |
        FAIL tests/api.test.ts
          ● should handle null user
      |
        TypeError: Cannot read property 'id' of null
          at handler (src/api.ts:89)

  recommendation: fix_related_first

review:
  status: success
  source: claude_analysis
  overall_summary: |
    Reviewed 3 changed files. Found 1 critical issue and 1 suggestion.
    The critical null pointer issue aligns with the test failure.

  issues[2]:
    severity: critical
    code_references[1]:
      file: src/api.ts
      line: 42
    description: |
      **Null pointer risk**
      The user object may be null here. Add null check before accessing
      properties. This is causing the test failure in tests/api.test.ts.

    severity: suggestion
    code_references[1]:
      file: src/utils.ts
      line_range: 15-20
    description: |
      **Consider refactoring**
      Extract validation logic into separate function.

summary:
  total_build_failures: 1
  total_review_issues: 2
  critical_review_issues: 1
  overall_status: needs_attention
  recommendation: |
    Fix 1 critical issue (null pointer in src/api.ts) which is causing
    test failure. Then address 1 suggestion before committing.
```

## Implementation Steps

As an agent executing this skill, follow these steps.

Copy this checklist to track progress (helps maintain focus during multi-step orchestration):

```
Feedback Gathering Progress:
- [ ] Step 1: Determine review scope (staged vs unstaged)
- [ ] Step 2: Run local build
- [ ] Step 3: Parse build output
- [ ] Step 4: Perform code review
- [ ] Step 5: Parse review feedback (if needed)
- [ ] Step 6: Build unified output
- [ ] Step 7: Return to main context
```

### 1. Determine Review Scope

```bash
# Check if there are staged changes
STAGED=$(git diff --staged --name-only)

# Check if there are unstaged changes
UNSTAGED=$(git diff --name-only)

# Use staged if available, otherwise unstaged
```

### 2. Run Local Build

Use `getting-build-results-local` skill:
- Read project documentation for CI commands.
- Run CI commands via Bash tool.
- Capture raw output.

### 3. Parse Build Output

Use `parsing-build-results` skill:
- Provide raw build output.
- Provide list of changed files (from step 1).
- Get structured failures with relatedness analysis.

### 4. Perform Code Review

Use `getting-review-local` skill:
- Provide list of changed files.
- Run review tools or perform analysis.
- Get structured review feedback.

### 5. Parse Review Feedback (if needed)

If review feedback isn't already structured, use `parsing-review-suggestions` skill to structure it.

### 6. Build Unified Output

Combine build results and review feedback into unified TOON structure.

Calculate summary:
- Count total build failures.
- Count review issues by severity.
- Determine overall status.
- Generate actionable recommendation.

### 7. Return to Main Context

Output the complete unified TOON to stdout for main context consumption.

## Overall Status Values

- `all_clear` - No build failures, no critical review issues.
- `needs_attention` - Build failures or critical review issues.
- `warnings_only` - Minor issues or suggestions only.

## Recommendation Generation

Based on the feedback, generate actionable recommendation:

All clear:
```
All checks passed! Safe to commit.
```

Build failures only:
```
Fix 1 test failure before committing.
```

Review issues only:
```
Address 1 critical review issue before committing.
2 suggestions can be addressed optionally.
```

Both:
```
Fix 1 critical issue (null pointer in src/api.ts) which is causing
test failure. Then address 1 suggestion before committing.
```

Alignment (build + review point to same issue):
When build failure and review issue reference the same code location:
```
Fix critical null pointer issue in src/api.ts (causing test failure
and flagged by review) before committing.
```

## Usage Pattern

CRITICAL: Always run in subagent.

```markdown
Use Task tool with subagent_type='general-purpose':

"Use the getting-feedback-local skill to gather complete local feedback.
Run through all steps: local CI, parse results, code review, and return
unified TOON output with complete summary and recommendations."
```

Why run in subagent:
- Running CI can take minutes - the wait happens in subagent context, not main.
- Raw logs can be large (10k+ tokens) - never loaded into main context.
- Review analysis adds more tokens - computed in subagent, only summary returned.
- Main context only needs the structured summary (~2-3k tokens vs 10-20k raw).

## Integration with Commands

Used by:
- `/quality-triage` command - Pre-PR quality loop.
- `/quality-triage-pr` command - Pre-commit verification.

## Changed Files Detection

For staged changes:
```bash
git diff --staged --name-only
```

For unstaged changes:
```bash
git diff --name-only
```

For both:
```bash
# Combined list (unique)
{ git diff --staged --name-only; git diff --name-only; } | sort -u
```

Pass this to both parsing-build-results and getting-review-local for context.

## Common Mistakes

Not providing changed files context:
- Problem: Can't determine if failures are related to changes.
- Fix: Always include changed file list in context.

Running full review on entire codebase:
- Problem: Wastes time and tokens.
- Fix: Focus review on changed files only.

Not aligning build failures with review:
- Problem: Miss that they're pointing to same issue.
- Fix: Cross-reference code locations in summary.

Returning raw data instead of unified TOON:
- Problem: Main context gets overwhelmed.
- Fix: Always merge and summarize into unified structure.

## Error Handling

If build commands fail to run:
- Note in output.
- Continue with code review.
- Include partial results.

If code review unavailable:
- Note in output.
- Include build results only.
- Suggest running review separately.

Always return TOON output, even on partial failure. Main context needs actionable information.

## Quick Reference

| Step | Skill | Purpose |
|------|-------|---------|
| 1 | getting-build-results-local | Run local CI |
| 2 | parsing-build-results | Parse into failures |
| 3 | getting-review-local | Perform code review |
| 4 | parsing-review-suggestions | Parse into issues |
| 5 | (this skill) | Combine into unified output |

## Example Use Cases

### Pre-Commit Hook

Before committing:
1. Run `getting-feedback-local` in subagent
2. If status is `needs_attention` with critical issues → Block commit
3. If status is `warnings_only` → Allow commit, note issues
4. If status is `all_clear` → Proceed with commit

### Pre-PR Workflow

Before creating PR:
1. Run `getting-feedback-local` on all uncommitted changes
2. Address all issues
3. Commit clean code
4. Push and create PR with confidence

### Development Loop

During active development:
1. Make changes
2. Run `getting-feedback-local` for quick check
3. Fix issues
4. Repeat until clean
5. Commit
