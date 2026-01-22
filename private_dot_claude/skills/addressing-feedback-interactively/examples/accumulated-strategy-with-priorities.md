# Example: Accumulated Strategy with Priority Ordering

**IMPORTANT:** This example illustrates decision logic and state transitions.
It is NOT a conversation transcript - use the templates in the workflow sections of SKILL.md for actual communication with users.

## Input

- 5 feedback items with mixed priorities
- Test failure at tests/auth.test.ts:15 (related=true)
- Review critical at src/auth.ts:42
- Review warning at src/auth.ts:89
- Review suggestion at src/utils.ts:20
- Test failure at tests/legacy.test.ts:99 (related=false)

## Step 1: Choose Strategy

- User choice: Accumulated

## Step 2: Present Summary

- No alignment detected
- Priority assignment:
  - Priority 1: 2 issues (test failure related, review critical)
  - Priority 2: 1 issue (review warning)
  - Priority 3: 1 issue (review suggestion)
  - Not presented: 1 unrelated test failure (noted separately)
- Presentation order: Issues 1-4 (skipping unrelated failure)

## Step 3: Resolution Loop

Issue 1 [Priority 1] - Test failure:
- Steps: Investigate → Present → Propose → Implement → Verify (passed)
- Commit decision: Accumulated → Don't commit yet, continue

Issue 2 [Priority 1] - Review critical:
- Steps: Investigate → Present → Propose → Implement → Verify (passed)
- Commit decision: Accumulated → Don't commit yet, continue

Issue 3 [Priority 2] - Review warning:
- Steps: Investigate → Present → Propose → Implement → Verify (passed)
- Commit decision: Accumulated → Don't commit yet, continue

Issue 4 [Priority 3] - Suggestion:
- Present: Show suggestion to user
- User choice: "Defer to follow-up issue"
- Skip implementation, continue

## Step 4: Final Completion

- Create single commit with all 3 fixes (Issues 1-3)
- Commit message: "Address feedback: fix auth test, add validation, improve error handling"
- Report: "All 3 critical/warning issues addressed. 1 suggestion deferred."

## Key Decisions

- Priority ordering ensured critical issues handled first
- Unrelated failure not included in issue list (noted only)
- User decision on suggestion (defer) respected
- Single accumulated commit at end with all fixes
