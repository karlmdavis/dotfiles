---
description: Monitor and fix CI checks until all pass
---

I would like you to operate in a loop where you:

1. Work through all of the local quality checks…
   1.a. Run all of the same checks from the CI locally.
   1.b. Resolve any issues they find.
   1.c. Commit and push the fixes.

2. Verify that all acceptance/success criteria for the current issue, plans, and/or PR have been met.
   2.a. If any criteria have not been met, address them.
   2.b. Commit and push the fixes.

3. Work through all of the CI quality checks…
   3.a. Wait (in 30 second intervals) for the current branch's PR CI checks to complete.
   3.b. Look at the results of those CI checks.
   3.c. Address any issues revealed by the CI checks.
   3.d. Look at the most recent review comment from Claude.
   3.e. Address the findings that Claude reported.
      3.e.1. Always fully address any critical, major, important, or blocker findings/recommendations.
      3.e.2. Prompt me, one at a time, to ask whether or not the other, more minor, findings/recommendations
               should be addressed or deferred to a new GitHub issue, or ignored.
   3.f. Commit and push all of those changes.

4. Go back to Step 1 and repeat from the top.

This is a dynamic system: every time you commit a change,
  the results from the previous steps and iterations are potentially invalidated.
The goal is to get to a full iteration of the loop Where no changes are needed in any step.
Once that happens, we're done.
