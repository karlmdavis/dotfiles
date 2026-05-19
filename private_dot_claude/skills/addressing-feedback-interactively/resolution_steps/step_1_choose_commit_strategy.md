# Resolution Step 1: Choose Commit Strategy

Before starting to address issues, we need to know how the user wants commits to be handled.
Ask the user once at the beginning and store their choice for use in later steps.

## Prompt Template

Ask the user:

```markdown
How would you like to commit fixes?

**1. Incremental**: Commit after each fix.
  - Each fix gets its own commit.
  - Easy to revert individual changes.
  - Clean git history showing progression.
  - Best when working on PR with CI feedback.

**2. Accumulated**: Fix all issues, commit once at end.
  - All fixes in single commit.
  - Cleaner final history.
  - Good for local development before creating PR.
  - Best when addressing pre-commit feedback.

**3. Manual**: Don't auto-commit, I'll commit manually.
  - You control all commits.
  - Fixes are implemented but not committed.
  - Maximum flexibility.
  - Best when you want to review changes first.
```

## Store Choice

Store the user's choice (1, 2, 3 or incremental, accumulated, manual) for use in:
- Resolution Step 3 Substep 6 (Commit Decision) - determines whether to commit after each fix.
- Resolution Step 4 (Final Completion) - determines how to finalize at the end.

## Strategy Details

**Incremental Strategy:**
- Commit after each successfully verified fix.
- Use descriptive message: "Fix {issue type}: {brief description}".
- Append Claude Code attribution.
- Continue to next issue.

**Accumulated Strategy:**
- Don't commit after each fix.
- Track that fixes are complete.
- At end (Resolution Step 4), create single commit with all fixes.

**Manual Strategy:**
- Don't commit at all.
- Implement fixes but leave staging and committing to user.
- At end (Resolution Step 4), summarize changes and list modified files.

## When Done

Once user has chosen and you've stored the choice:
- ✅ Resolution Step 1 complete.
- Proceed to Resolution Step 2 (Present Feedback Summary).
