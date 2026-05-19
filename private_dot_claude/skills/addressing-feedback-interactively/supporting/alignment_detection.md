# Alignment Detection

When build failures and review issues reference the same code location, they should be presented as
  aligned issues.
This prevents duplicate work and helps users understand the connection between different types of
  feedback.

## Alignment Criteria

Issues are considered aligned if any of the following are true:

1. **Same line, same problem**: They reference the same line in the same file AND involve the same
   underlying problem.

2. **Overlapping ranges, same problem**: They reference lines or line ranges in the same file(s)
   that overlap AND they involve the same underlying problem.

3. **Shared root cause**: They share the same root cause.
   - Determining this may require a brief investigation, looking at code context, and reasoning
     about the issues.
   - However, this should be kept lightweight to avoid excessive overhead.
   - A deeper root cause analysis will be done later, in Resolution Step 3 Substep 1 (Investigate
     Root Cause).
   - We can always change our mind about alignment during that investigation if needed.

## When to Detect Alignment

Perform alignment detection in Resolution Step 2 (Present Feedback Summary) before presenting
  issues to the user.

Review all feedback and identify any aligned issues.
Group aligned issues together - those groupings will be noted in the summary and then will be
  presented as a single combined issue going forward.

## Priority of Aligned Issues

The priority of the combined aligned issue is the **highest priority** of any individual issue in the group.

Example:
- Test failure (Priority 1) + Warning review (Priority 2) = Combined issue at Priority 1.

## Presentation Format

When presenting aligned issues in the summary, note them explicitly:

```markdown
**Notes**
- The following issues are likely aligned with each other and will be presented together:
  - [Priority 1] [Test Failure and Warning Review] src/api.ts:42 — Incorrect handling of null user
    object.
    - [Priority 1] [Test Failure] tests/api.test.ts:73 — TypeError: Cannot read property 'id' of
      null.
    - [Priority 2] [Warning Review] src/api.ts:42 — Null pointer risk.
```

Later, when presenting the individual issue for resolution, use the combined format:

```markdown
**Issue 1:** [Test Failure and Critical Review] src/api.ts:42 — Null pointer issue

**Build Failure**
{description of each build failure included in the aligned issue, if any, including error messages}

**Review Feedback**
{description of each review issue included in the aligned issue, if any, including any relevant details}

**Investigation Notes**
{summary of relevant code context you gathered}

These appear to be related to the same underlying issue.
```

## Benefits

User understanding:
- User sees the connection between failures and reviews.
- Clear that one fix can address multiple items.

Efficiency:
- Single fix addresses both issues.
- Avoids duplicate work.
- Reduces total resolution time.

Verification:
- One verification run covers all aligned items.
- Clear success criteria for the combined issue.

## Example

See [examples/toon-input-to-presentation.md](../examples/toon-input-to-presentation.md) for a
  concrete example of alignment detection in action.
