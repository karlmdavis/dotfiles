# Resolution Step 2: Present Feedback Summary

Before diving into individual issues, present a unified summary of all feedback to the user.
This gives them the big picture and sets expectations.

## Preparation

First, review all feedback from the TOON input and identify any aligned issues.
See [Alignment Detection](../supporting/alignment_detection.md) for details.

Group aligned issues together - those groupings will be noted in the summary and presented as single
  combined issues going forward.
The priority of a combined issue is the highest priority of any individual issue in the group.

**Terminology note:** From here on, we refer to individual items that need addressing as "issues",
  whether they are:
- Build/test failures.
- Review feedback items (regardless of severity, including suggestions).
- Aligned sets of items (grouped together).

## Priority Assignment Logic

Use the following logic to assign priorities:

**Priority 1:** User will likely want to fix these immediately.
- Build failures related to changes (`related_to_changes: true`).
- Review issues with `severity: critical`.

**Priority 2:** User will probably want to fix these soon.
- Review issues with `severity: warning`.

**Priority 3:** User may want to fix these.
- Review issues with `severity: suggestion`.

**Not presented** (noted separately):
- Build failures unrelated to changes (`related_to_changes: false`).
  - Don't include in issue list.
  - Don't require fixing as part of this workflow.
  - Note them in summary for awareness.

## Presentation Template

Present the unified summary to your user:

```markdown
**Build and Review Feedback Summary**

**Build Results:** {Pass/Fail} ({N} failures, {M} related)
**Review Results:** {Merge/Needs Work} ({N} recommendations): {concise 1-2 sentence summary of
  review results, focused on overall recommendation and tone}

**{N} Total Items To Consider Addressing**
- Priority 1: {count} Build Failures and Critical Issues
- Priority 2: {count} Warnings
- Priority 3: {count} Suggestions

**Notes**
- {N} pre-existing build failures unrelated to your changes.
<!-- If aligned issues were found, include this bullet. -->
- The following issues are likely aligned with each other and will be presented together:
  - [Priority {X}] [{Issue Types}] {location} — {brief title}
    - [Priority {Y}] [{Type}] {location} — {description}
    - [Priority {Z}] [{Type}] {location} — {description}

**Issue List**
1. [Priority {X}] [{Issue Type(s)}] {location} — {brief description}
2. [Priority {X}] [{Issue Type(s)}] {location} — {brief description}
3. [Priority {X}] [{Issue Type(s)}] {location} — {brief description}

Let's work through these in order.
```

## Fill-in Guide

**Build Results line:**
- Status: "Pass" or "Fail" based on `build_results.status`.
- Count failures from `build_results.failures` array.
- Count related failures where `related_to_changes: true`.

**Review Results line:**
- Status: "Merge" if no critical/warning issues, "Needs Work" if there are.
- Count from `review.issues` array.
- Summarize the overall tone and recommendation from the review.

**Total Items count:**
- Count Priority 1 issues (related failures + critical reviews - aligned duplicates).
- Count Priority 2 issues (warnings - aligned duplicates).
- Count Priority 3 issues (suggestions - aligned duplicates).

**Notes section:**
- Count and note unrelated failures (`related_to_changes: false`).
- List aligned issue groups with sub-items indented.

**Issue List:**
- List all issues in priority order (Priority 1, then 2, then 3).
- Use consistent format: `[Priority X] [Type] location — brief description`.
- For aligned issues, combine types: `[Test Failure and Warning Review]`.

## Example

See [examples/toon-input-to-presentation.md](../examples/toon-input-to-presentation.md) for a
  complete example transformation from TOON input to this presentation format.

## When Done

Once you've presented the summary to the user:
- ✅ Resolution Step 2 complete.
- Proceed to Resolution Step 3 (Interactive Resolution Loop).
