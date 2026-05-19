# Substep 3.4: Implement Fix

Now implement the fix that was approved by the user in Substep 3.3.

## What to Do

Make the necessary code changes:

1. **Use Edit tool for existing files:**
   - Make precise edits to existing code.
   - Preserve formatting and style.

2. **Use Write tool for new files (if needed):**
   - Only create new files if absolutely necessary.
   - Prefer editing existing files.

3. **Track all modified files:**
   - Maintain a list of ALL files modified in this session.
   - This list is critical for verification in Substep 3.5 (relatedness analysis).

## Implementation Guidelines

**Be precise:**
- Make only the changes needed to fix the issue.
- Don't refactor unrelated code (unless it's part of the approved fix).

**Be consistent:**
- Match existing code style.
- Follow project conventions.

**Be complete:**
- If the fix requires changes in multiple files, make all necessary changes.
- Don't leave the codebase in a broken state.

## Track Modified Files

**Critical:** Keep a running list of all files modified during the entire session (across all issues).

This list will be passed to verification in Substep 3.5 for relatedness analysis.

Example tracking:
```
Modified files in this session:
- src/api.ts
- tests/api.test.ts
- src/utils.ts
```

## When Done

Once all code changes are implemented:
- ✅ Substep 3.4 complete.
- Proceed to Substep 3.5 (Verify Fix).
