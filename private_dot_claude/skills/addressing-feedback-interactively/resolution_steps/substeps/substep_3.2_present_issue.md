# Substep 3.2: Present Issue Details

Present the issue details to the user using the appropriate template for the issue type.

## Template Selection

Choose the template based on issue type:
- Build failures (test, lint, build, type_check).
- Review issues (critical, warning, suggestion).
- Aligned issues (build failure + review issue combined).

## Template for Build Failures

```markdown
**Issue {N}:** [{issue type, e.g. "Test Failure", "Lint Issue", "Build Error", "Type Check Error"}] {location}

**Related to your changes:** Yes
**Reasoning:** {reasoning from TOON input}

**Description**
{description of the build failure, including error messages from TOON input}

**Investigation Notes**
{summary of relevant code context you gathered in Substep 3.1}
```

## Template for Review Issues

```markdown
**Issue {N}:** [{severity level, e.g. "Critical Review", "Warning", "Suggestion"}]
  {code_references} — {brief title of issue}

**Description**
{description of the review issue from TOON input, including any relevant details}

**Investigation Notes**
{summary of relevant code context you gathered in Substep 3.1}
```

## Template for Aligned Issues

```markdown
**Issue {N}:** [{combined types, e.g. "Test Failure and Critical Review"}] {code_references} —
  {brief title of issue}

**Build Failure**
{description of each build failure included in the aligned issue, if any, including error
  messages}

**Review Feedback**
{description of each review issue included in the aligned issue, if any, including any relevant
  details}

**Investigation Notes**
{summary of relevant code context you gathered in Substep 3.1}

These appear to be related to the same underlying issue.
```

## Fill-in Guide

**Issue {N}:**
- Use current issue number and total count from loop.

**{issue type}:**
- Build failures: "Test Failure", "Lint Issue", "Build Error", "Type Check Error".
- Review issues: "Critical Review", "Warning", "Suggestion".
- Aligned: Combine types like "Test Failure and Warning Review".

**{location}:**
- File path and line number from `location` or `code_references` in TOON.

**{reasoning}:**
- Copy from `reasoning` field in TOON build failure.

**{description}:**
- For build failures: Include error messages from `messages` array.
- For review issues: Copy from `description` field.
- For aligned: Include descriptions from all constituent issues.

**{Investigation Notes}:**
- Summarize what you learned in Substep 3.1.
- Keep it concise but informative.

## When Done

Once you've presented the issue details to the user:
- ✅ Substep 3.2 complete.
- Proceed to Substep 3.3 (Propose Fix).
