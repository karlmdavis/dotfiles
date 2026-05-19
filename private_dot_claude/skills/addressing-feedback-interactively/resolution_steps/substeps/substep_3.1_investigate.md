# Substep 3.1: Investigate Root Cause

Before presenting the issue or proposing a fix, gather context to understand the problem.

## What to Do

1. **Read the file(s) referenced in the issue.**
   - Use Read tool to view the code at the location mentioned in the issue.
   - For aligned issues, read all referenced files.

2. **Read surrounding code to understand context.**
   - How is this code used?
   - What are the dependencies?
   - What are the edge cases?

3. **Identify one or more options for addressing the issue.**
   - What needs to change?
   - Are there multiple approaches?
   - What are the tradeoffs?

## Output

This investigation informs the next substeps:
- Substep 3.2 (Present Issue Details) will include investigation notes in the presentation.
- Substep 3.3 (Propose Fix) will use this context to propose solutions.

## Notes for Aligned Issues

For aligned issues (build failure + review issue combined):
- Investigate both aspects of the problem.
- Look for how they relate to each other.
- Consider that a single fix might address both.
- If during investigation you determine they're NOT actually aligned, you can split them back into
    separate issues.

## When Done

Once you've gathered sufficient context and identified potential approaches:
- ✅ Substep 3.1 complete.
- Proceed to Substep 3.2 (Present Issue Details).
