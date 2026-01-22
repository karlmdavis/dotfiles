# Example: Incremental Strategy with Alignment

**IMPORTANT:** This example illustrates decision logic and state transitions.
It is NOT a conversation transcript - use the templates in the workflow sections of SKILL.md for actual communication with users.

## Input

- 3 feedback items (2 failures related, 1 review critical)
- Test failure at tests/api.test.ts:42 (related=true)
- Review critical at src/api.ts:42
- Review critical at src/db.ts:89

## Step 1: Choose Strategy

- User choice: Incremental

## Step 2: Present Summary

- Alignment detection: Test failure + Review both reference :42 → Aligned
- Grouped result: 2 issues to address (1 aligned, 1 standalone)
- Priority assignment:
  - Issue 1: [Priority 1] [Test Failure + Critical Review] src/api.ts:42 (aligned)
  - Issue 2: [Priority 1] [Critical Review] src/db.ts:89

## Step 3: Resolution Loop

Issue 1 (aligned):
- Investigate: Read src/api.ts, understand null handling
- Present: Show both test failure and review together
- Propose: Add null check before property access
- Implement: Edit src/api.ts
- Verify: Run CI → status: all_passed
- Commit: "fix: add null check in API handler" (with attribution)

Issue 2:
- Investigate: Read src/db.ts, understand query construction
- Present: Show SQL injection risk
- Propose: Use parameterized query
- Implement: Edit src/db.ts
- Verify: Run CI → status: all_passed
- Commit: "fix: use parameterized query in database handler" (with attribution)

## Step 4: Final Completion

- All commits already created (2 total)
- Report: "All 2 issues addressed with 2 commits."

## Key Decisions

- Alignment detection prevented duplicate work (1 fix for 2 items)
- Each fix verified independently before commit
- Two separate commits for two distinct issues
