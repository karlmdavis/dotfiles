---
description: Check PR status, workflow results, and review comments
---

I would like you to check the current PR's quality and readiness for merge:

1. **Get Workflow Results**
   1.a. Use the `getting-pr-workflow-results` skill.
   1.b. This will wait for workflows to complete, then return job summaries with commands to retrieve logs.
   1.c. Present the workflow results summary.

2. **Get Review Comments**
   2.a. Use the `getting-pr-review-comments` skill.
   2.b. This will extract Claude Code review bot recommendations.
   2.c. Present the review recommendations.

3. **Summary**
   3.a. Provide a clear summary of:
       - Which workflow jobs passed/failed
       - Key review recommendations
       - Whether the PR is ready to merge
       - Any action items that need to be addressed
       - Commands to investigate failures (if any)
