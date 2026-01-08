---
name: getting-branch-state
description: Check local branch state, PR status, and sync comparison (ahead/behind/diverged). Returns branch info, base branch detection, uncommitted files, PR details, and changed files for review context.
---

# Getting Branch State

## Overview

Analyzes the current git branch state, detects base branch (main/master), checks for associated PR, and compares local vs PR sync status.

Core principle: Single source of truth for branch/PR state analysis across all skills and commands.

What it does:
1. Get local branch info (branch, head, base_branch, uncommitted files).
2. Check if PR exists for current branch.
3. Compare local vs PR (ahead/behind/diverged status with commit lists).
4. Get changed files vs base branch for review context.

Output: Complete branch state ready for decision-making in commands.

## When to Use

Use when you need:
- Branch and PR state before addressing feedback.
- Base branch detection (main vs master).
- Sync status (ahead/behind/diverged) for user warnings.
- Changed files list for review scope.

When NOT to use:
- Just need PR workflow status (use `awaiting-pr-workflow-results`).
- Don't need git state analysis.

## Return Format

```toon
local:
  branch: feature-auth
  head: abc123def456789...
  head_short: abc123d
  timestamp: 2026-01-07T10:30:00Z
  base_branch: main
  uncommitted_files[2]:
    src/api.ts
    tests/api.test.ts

pr:
  exists: true
  number: 123
  head: def456abc123789...
  head_short: def456a
  url: https://github.com/owner/repo/pull/123

comparison:
  local_vs_pr:
    status: diverged
    ahead_count: 2
    behind_count: 3
    ahead_commits[2]:
      sha: abc123d
      message: Fix null pointer (rebased)

      sha: abc123e
      message: Add tests

    behind_commits[3]:
      sha: old789a
      message: Fix null pointer (original)

      sha: old789b
      message: Add validation

      sha: old789c
      message: Update docs

  branch_vs_base:
    changed_files[5]:
      src/api.ts
      src/utils.ts
      tests/api.test.ts
      tests/utils.test.ts
      docs/README.md
```

When PR doesn't exist:
```toon
local:
  branch: feature-auth
  head: abc123d...
  head_short: abc123d
  timestamp: 2026-01-07T10:30:00Z
  base_branch: main
  uncommitted_files[0]:

pr:
  exists: false

comparison:
  local_vs_pr:
    status: no_pr
  branch_vs_base:
    changed_files[3]:
      src/api.ts
      tests/api.test.ts
      docs/README.md
```

When on base branch (main/master):
```toon
local:
  branch: main
  head: xyz789...
  head_short: xyz789a
  timestamp: 2026-01-07T10:30:00Z
  base_branch: main
  uncommitted_files[2]:
    src/api.ts
    tests/api.test.ts

pr:
  exists: false

comparison:
  local_vs_pr:
    status: no_pr
  branch_vs_base:
    changed_files[2]:
      src/api.ts
      tests/api.test.ts
```

Note: When on base branch, `branch_vs_base.changed_files` = uncommitted files (staged + unstaged).

## Sync Status Values

local_vs_pr.status can be:
- `in_sync` - Local and PR are identical (ahead: 0, behind: 0).
- `ahead` - Local has unpushed commits (ahead > 0, behind: 0).
- `behind` - PR has commits not in local (ahead: 0, behind > 0).
- `diverged` - Both have unique commits (ahead > 0, behind > 0), usually from rebase.
- `no_pr` - No PR exists for this branch.

## Base Branch Detection

The skill automatically detects the base branch:
1. First tries `git symbolic-ref refs/remotes/origin/HEAD` (if remote HEAD is set).
2. Falls back to checking if `refs/heads/main` exists.
3. Falls back to `master` if main doesn't exist.

## Usage Pattern

```markdown
Run the script directly via Bash:

scripts/check_branch_state.py
```

Parse the TOON output to get branch state, PR info, and sync status.

## Integration with Commands

Used by:
- `/quality-triage` command - Step 0 (determine review scope, detect PR).
- `/quality-triage-pr` command - Step 0 (check sync, warn about mismatches).

Why extract to separate skill:
- Single source of truth for branch/PR state logic.
- Prevents duplication across multiple skills and commands.
- Consistent base branch detection.
- Consistent sync status determination.

## Example Use Cases

### Pre-commit workflow (quality-triage)

```
1. Run getting-branch-state
2. Check local.branch vs local.base_branch:
   - If on main/master → review uncommitted files
   - If on feature branch → review branch_vs_base.changed_files
3. Check pr.exists and local_vs_pr.status:
   - If PR exists and status is "ahead" → may want to push before more local work
   - If diverged → warn about rebase
4. Pass changed files to getting-feedback-local
```

### PR workflow (quality-triage-pr)

```
1. Run getting-branch-state
2. Check pr.exists:
   - If false → error, can't proceed
3. Check local_vs_pr.status:
   - If "in_sync" → proceed normally
   - If "ahead" → warn, offer to push
   - If "behind" → warn, offer to pull
   - If "diverged" → warn, explain rebase situation, offer options
4. Pass pr.number to getting-feedback-remote
```

### Refactored awaiting-pr-workflow-results

The awaiting skill will:
1. Call getting-branch-state (or run script directly).
2. Use pr.exists, pr.number, local_vs_pr.status for its logic.
3. Focus on workflow waiting, not branch state detection.

## Common Scenarios

Scenario: Local ahead of PR
```toon
comparison:
  local_vs_pr:
    status: ahead
    ahead_count: 2
```
Interpretation: You have 2 unpushed commits. Push to update PR.

Scenario: Local behind PR
```toon
comparison:
  local_vs_pr:
    status: behind
    behind_count: 3
```
Interpretation: PR has 3 commits you don't have. Pull to sync.

Scenario: Diverged (rebased locally)
```toon
comparison:
  local_vs_pr:
    status: diverged
    ahead_count: 2
    behind_count: 3
```
Interpretation: You rebased locally. Need to force push.

Scenario: Working on feature branch
```toon
local:
  branch: feature-auth
  base_branch: main
comparison:
  branch_vs_base:
    changed_files[5]: [...]
```
Interpretation: Review these 5 files that differ from main.

Scenario: Working on main branch
```toon
local:
  branch: main
  base_branch: main
  uncommitted_files[2]: [...]
comparison:
  branch_vs_base:
    changed_files[2]: [...]  # same as uncommitted
```
Interpretation: Review uncommitted changes before committing to main.

## Error Handling

If not in git repository:
- Script exits with error: "Error: Not in a git repository".

If gh CLI unavailable:
- pr.exists = false (can't check).

If remote origin/HEAD not set and neither main nor master exists:
- Falls back to "master" as base_branch.
- May be incorrect for repos with different conventions.

## Benefits

Consistency:
- Same branch detection logic everywhere.
- Same sync status interpretation.
- Same base branch detection.

Efficiency:
- Single call gets all branch/PR state.
- Avoids multiple git/gh command calls.

Maintainability:
- One place to update branch state logic.
- Easier to add new state checks.
