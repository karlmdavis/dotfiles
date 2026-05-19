# Resolution Step 3: Interactive Resolution Loop

Now we address each issue in priority order, one at a time.
This step involves a loop with substeps for each issue.

## Loop Structure

For each issue in priority order (Priority 1, then Priority 2, then Priority 3):

This checklist specifies the Resolution Loop substeps for each issue.
Copy this checklist and track your progress through it for each issue:

```
Resolution Loop Progress (Issue {N} of {Total}):
[ ] Substep 3.1: Investigate Root Cause
[ ] Substep 3.2: Present Issue Details
[ ] Substep 3.3: Propose Fix
[ ] Substep 3.4: Implement Fix
[ ] Substep 3.5: Verify Fix
[ ] Substep 3.6: Commit Decision
```

## Before Starting Each Issue

Announce to the user:

```markdown
Next, we'll triage and consider addressing Issue {N} of {Total}: {issue brief description}...
```

Then proceed through the substeps.

## Substep Details

Each substep has detailed instructions in its own file:

### Substep 3.1: Investigate Root Cause

See [substeps/substep_3.1_investigate.md](substeps/substep_3.1_investigate.md).

Gather context for the issue by reading relevant files and understanding how the code is used.
Identify one or more options for addressing the issue.

### Substep 3.2: Present Issue Details

See [substeps/substep_3.2_present_issue.md](substeps/substep_3.2_present_issue.md).

Present the issue details to the user using templates appropriate for the issue type (build
  failure, review issue, or aligned issue).

### Substep 3.3: Propose Fix

See [substeps/substep_3.3_propose_fix.md](substeps/substep_3.3_propose_fix.md).

Propose one or more approaches to address the issue.
Get user approval before implementing.

### Substep 3.4: Implement Fix

See [substeps/substep_3.4_implement.md](substeps/substep_3.4_implement.md).

Once user approves, implement the fix by making necessary code changes.

### Substep 3.5: Verify Fix

See [substeps/substep_3.5_verify.md](substeps/substep_3.5_verify.md).

Run verification in a subagent to confirm the fix works.
Triage results and loop back if needed.

### Substep 3.6: Commit Decision

See [substeps/substep_3.6_commit.md](substeps/substep_3.6_commit.md).

Based on commit strategy chosen in Resolution Step 1, decide whether to commit now or defer.

## After Each Issue

After completing Substep 3.6 for an issue:
- If more issues remain: Return to the top of Resolution Step 3 for the next issue.
- If all issues addressed: Proceed to Resolution Step 4 (Final Completion).

## Loop Control

**Important:** Track which issue you're on and total count.
Reset the substep checklist for each new issue.
