---
description: Check PR status, workflow results, and review comments
---

I would like you to check the current PR's quality and readiness for merge, then interactively address
  each issue:

1. **Gather All QA Data in Subagents**
   1.a. Spawn a subagent using the Task tool with `subagent_type='general-purpose'` and
         `description="Get PR workflow results"`.
       - The subagent prompt should use the `getting-pr-workflow-results` skill.
       - Wait for the subagent to return workflow job summaries.
   1.b. Spawn a subagent using the Task tool with `subagent_type='general-purpose'` and
         `description="Get PR review comments"`.
       - The subagent prompt should use the `getting-pr-review-comments` skill.
       - Wait for the subagent to return review recommendations.
   1.c. CRITICAL: Skills MUST run in subagents, never in main context.
         This prevents token bloat and scope creep.

2. **Present Overall Summary**
   2.a. Provide a concise summary showing:
       - Total number of workflow failures (if any).
       - Total number of review recommendations (if any).
       - Overall PR status (ready to merge / needs fixes).
   2.b. List all issues/recommendations by number (e.g., "Issue 1: Test failure in...", "Issue 2: Review
         suggests...").
   2.c. CRITICAL: The subagents should ONLY report status, NEVER fix issues.
         Fixing happens in step 3 with user approval, not during data gathering.

3. **Address Each Issue Interactively**
   3.a. For each issue/recommendation from the summary:
       - Discuss the specific issue in detail.
       - Investigate the root cause (fetch logs, read relevant code, etc.).
       - Propose a fix, ask the user about the proposal, and proceed per their direction.
       - If changes are made to address the issue, commit those changes with a clear message referencing
           the issue.
   3.b. Work through all issues sequentially until all are addressed.
   3.c. DO NOT ask for permission for individual commits - just make them after implementing fixes.

4. **Final Push**
   4.a. After all issues are fixed and committed, verify the branch is ready.
   4.b. Ask once whether to push all commits to the remote branch.

**Important Guidelines:**
- Keep the initial summary concise - just the counts and numbered list of issues.
- Address issues one at a time, committing fixes separately.
- Don't dump giant walls of text - work iteratively.
- Only ask about pushing at the very end, not for each commit.
