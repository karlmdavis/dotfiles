# Substep 3.3: Propose Fix

Propose one or more approaches to address the issue and get user approval before implementing.

## What to Propose

Based on your investigation in Substep 3.1, propose:

1. **What needs to change:**
   - Which file(s) need modification?
   - What code needs to be added/changed/removed?

2. **Approach options:**
   - If there's one clear fix, present it.
   - If there are multiple valid approaches, present options with tradeoffs.

3. **Expected outcome:**
   - What will be different after the fix?
   - How will this address the issue?

## Proposal Template

```markdown
**Proposed Fix**

{Explain what needs to change and why}

**Approach:**
{Describe the specific changes you'll make}

{If multiple options exist:}
**Alternative Approach:**
{Describe alternative and explain tradeoffs}

**Expected Outcome:**
{What will be fixed/improved}

Does this approach sound good?
```

## Special Case: Suggestions

For Priority 3 issues (suggestions), give the user more control:

```markdown
**This is a suggestion** (Priority 3).

**Proposed Improvement:**
{Describe the suggested improvement}

Would you like to:
1. Address this now
2. Defer to later (note for follow-up)
3. Skip entirely
```

Handle user's choice:
- **Address now:** Proceed to Substep 3.4 (Implement Fix).
- **Defer:** Skip to Substep 3.6 (Commit Decision) - no fix, no verification needed.
- **Skip:** Skip to Substep 3.6 (Commit Decision) - no fix, no verification needed.

## Get User Approval

**Critical:** Do NOT proceed to implementation without user approval.

Wait for user response:
- If approved: Proceed to Substep 3.4 (Implement Fix).
- If user suggests alternative: Adjust proposal and re-propose.
- If user wants to defer/skip: Note it and proceed to Substep 3.6 (skip implementation and verification).

## When Done

Once user has approved the fix approach (or chosen to defer/skip):
- ✅ Substep 3.3 complete.
- Proceed to Substep 3.4 (Implement Fix) if approved, or Substep 3.6 (Commit Decision) if deferred/skipped.
