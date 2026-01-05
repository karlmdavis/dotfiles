---
name: getting-reviews-remote
description: Fetch PR review comments (Claude bot + GitHub reviews + unresolved threads) - returns raw review text for parsing by parsing-review-suggestions
---

# Getting Reviews Remote

## Overview

Fetch all review feedback for a PR commit from GitHub:
1. Claude bot review comments (filtered by commit push timestamp)
2. GitHub PR reviews (filtered by commit SHA)
3. Unresolved review threads from earlier commits

**Core principle:** Run in subagent to fetch reviews without consuming main context tokens.

**Input:** PR number and commit SHA

**Output:** TOON-formatted raw review text for parsing

## When to Use

Use when you need:
- Claude bot review recommendations for current commit
- Human reviewer feedback from GitHub PR reviews
- Outstanding unresolved comments from earlier commits

**When NOT to use:**
- Need parsed/structured issues (use `parsing-review-suggestions` after this)
- PR doesn't exist yet (create PR first)

## Workflow

### Step 1: Get PR Number and Commit

```bash
# Get current PR number
PR_NUM=$(gh pr view --json number -q '.number')

# Get current commit SHA
COMMIT=$(git rev-parse HEAD)
```

### Step 2: Fetch Reviews

Run the script:

```bash
scripts/fetch_pr_reviews.py $PR_NUM $COMMIT
```

### Step 3: Use Output for Parsing

Pass the raw review text to `parsing-review-suggestions` skill (agent-driven) to extract structured issues.

## Return Format

```toon
status: success
pr_number: 123
current_commit: a1b2c3d
commit_pushed_at: 2026-01-04T15:00:00Z

claude_bot_comment:
  link: https://github.com/.../issuecomment-987654
  updated_at: 2026-01-04T15:30:00Z
  body: |
    ## Code Review

    Overall the changes look solid! Found a few issues to address:

    ### 🔴 Critical Issues

    1. **Null pointer risk** (src/api.ts:42)
       The user object may be null here. Add null check before accessing properties.

    ### 💡 Suggestions

    1. **Consider error handling** (src/api.ts:89)
       Database call should have try/catch for better error handling.

    Recommendation: Address critical issues, then ready to merge.

github_reviews[2]:
  reviewer: alice
  state: changes_requested
  submitted_at: 2026-01-04T14:00:00Z
  review_link: https://github.com/.../pullrequestreview-789
  body: |
    Nice work on the authentication refactoring! A few comments:

    - Add error handling to the database calls
    - Consider adding integration tests for the new flow

    Changes requested - see inline comments.

  reviewer: bob
  state: approved
  submitted_at: 2026-01-04T14:30:00Z
  review_link: https://github.com/.../pullrequestreview-790
  body: LGTM!

unresolved_threads[1]:
  link: https://github.com/.../discussion_r456
  reviewer: alice
  created_at: 2026-01-03T10:00:00Z
  body: |
    Consider refactoring this validation logic into a separate function
    for better reusability.
  resolved: false
```

## Filtering Strategy

### Claude Bot Comments

- **Filter:** Only comments updated **after** commit was pushed to PR
- **Reason:** Ensures review is for current commit, not stale feedback
- **Selection:** Most recent Claude bot comment meeting criteria

### GitHub PR Reviews

- **Filter:** Only reviews where `commit_id` matches current commit SHA
- **Reason:** Reviews are tied to specific commits; only want current commit reviews
- **Selection:** All matching reviews (can be multiple reviewers)

### Unresolved Threads

- **Filter:**
  - `isResolved: false` in GitHub API
  - From commits **other than** current commit
- **Reason:** Need to track outstanding issues even if not on current commit
- **Selection:** All unresolved threads from PR history

## Usage Pattern

**CRITICAL:** Always run in subagent to save context tokens.

```markdown
Use Task tool with subagent_type='general-purpose':

"Use the getting-reviews-remote skill to fetch review feedback for PR #123
at commit a1b2c3d4. Run scripts/fetch_pr_reviews.py with these parameters
and return the complete TOON output."
```

## Integration with Other Skills

**Typical workflow:**
1. `awaiting-pr-workflow-results` → Ensure workflows complete
2. `getting-reviews-remote` → Fetch raw reviews (this skill)
3. `parsing-review-suggestions` → Parse into structured issues
4. `getting-feedback-remote` → Combine with build results

## Common Bot Usernames

The script checks for Claude bot under these usernames:
- `claude` (most common)
- `github-actions[bot]`
- `claude-code-bot`
- `anthropic-claude[bot]`

If your repo uses a different bot username, modify the script's filter list.

## Timestamp Precision

**Why commit push timestamp matters:**

Claude bot may post multiple review iterations. We only want reviews **after** the current commit was pushed to the PR.

```timeline
10:00 - Commit A pushed, Claude reviews
12:00 - Commit B pushed (current)
12:30 - Claude reviews Commit B ← We want this
```

The script uses GitHub's `/pulls/{pr}/commits` API to find when the commit actually appeared in the PR, not just when it was created locally.

## GraphQL for Unresolved Threads

Regular GitHub API doesn't expose review thread resolution status. We use GraphQL:

```graphql
query {
  repository {
    pullRequest {
      reviewThreads {
        isResolved
        comments { ... }
      }
    }
  }
}
```

This requires `gh` CLI with GraphQL support (included by default).

## Common Mistakes

**Using created_at instead of push timestamp**
- **Problem:** Gets stale reviews from before current commit
- **Fix:** Use commit push timestamp from PR commits API

**Only fetching most recent review regardless of commit**
- **Problem:** May get review for old commit
- **Fix:** Filter by commit_id (GitHub reviews) or timestamp (Claude bot)

**Missing unresolved threads**
- **Problem:** Don't realize there are outstanding issues
- **Fix:** Fetch via GraphQL and filter for unresolved + different commit

**Running in main context**
- **Problem:** Review text can be 20k+ tokens
- **Fix:** Always run in subagent

## Quick Reference

| Task | Command |
|------|---------|
| Fetch reviews for PR #123 at commit abc123 | `scripts/fetch_pr_reviews.py 123 abc123` |
| Get current PR number | `gh pr view --json number -q '.number'` |
| Get current commit SHA | `git rev-parse HEAD` |
| Get short commit SHA | `git rev-parse --short HEAD` |
