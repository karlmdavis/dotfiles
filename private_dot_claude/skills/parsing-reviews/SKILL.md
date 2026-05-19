---
name: parsing-review
description: Parse review feedback into structured data - extracts review summaries and suggestions from GiHub PR comments and reviews.
user_invocable: false
---

# Parsing Review Suggestions

## Overview

Parse raw review feedback (from GitHub PR comments and reviews) into structured TOON-formatted review summaries and suggestions.

Core principle: This is an agent-only skill. Claude naturally understands review text and can extract structured information.

**Input:** Review text (e.g. from the getting-review-local skill)
  or URLs pointing to that text (e.g. from the `getting-reviews-remote` skill).

Output: Structured TOON with review summaries and suggestions.

## Fetching Review Content

Depending on the input provided,
  you may need to fetch the actual review content first.
If the input contains URLs to review comments or reviews,
  fetch the content from those URLs before parsing.

## Concrete Example

This example illustrates the input and output of this skill.

### Input

Here's a sample input review comment,
  e.g. as from Claude bot on a GitHub PR.

```markdown
## Code Review

Great work on the authentication refactor! The overall structure is solid.
Found a few issues that need attention:

### 🔴 Critical Issues

1. **Null pointer risk** (src/api.ts:42).
   The user object may be null here. Add null check before accessing properties.

   Suggested fix:

   ```typescript
   if (!user) {
     throw new Error('User not found');
   }
   return user.id;
   ```

### 💡 Suggestions

1. **Consider error handling** (src/api.ts:89).
   Database call should have try/catch for better error handling.

### Recommendations

Address the critical issue before merging.
```

### Output

```toon
parsed_review:

  review_sources[1]:
    - type: github_pr_comment
      reviewer: Claude Bot
      updated_at: 2026-01-04T15:30:00Z
      commit: a1b2c3d
      links:
        - https://github.com/.../issuecomment-123
  
  overall_summary: |
    The authentication refactor is solid but not yet ready for merge.
    There was 1 critical issue that should be addressed before merging: a null pointer risk in src/api.ts:42.
    There was also 1 other suggestion for improvement: add error handling to database call in src/api.ts:89.
  
  suggestions[2]:
    - summary: Null pointer risk in src/api.ts:42
      severity: critical
      link: https://github.com/.../issuecomment-123#issue-1
      code_references[1]{file,line_number_start,line_number_end}:
        src/api.ts,42,42
      description: |
        **Null pointer risk**

        The user object may be null here. Add null check before accessing properties.

        Suggested fix:

        ```typescript
        if (!user) {
          throw new Error('User not found');
        }
        return user.id;
        ```

    - summary: Missing error handling for database call in src/api.ts:89
      severity: minor
      link: https://github.com/.../issuecomment-123#issue-2
      code_references[1]{file,line_number_start,line_number_end}:
        src/api.ts,89,91
      description: |
        **Consider error handling**

        Database call should have try/catch for better error handling.
```

## What to Extract

### Review Sources (`review_sources`)

For traceability, capture metadata about the source of the review,
  including:

- **`type`**: e.g. `github_pr_comment`, `github_pr_review`, `local_review`.
- **`reviewer`**: GitHub username or bot name.
- **`updated_at`**: timestamp of the review.
- **`commit`**: commit SHA the review refers to.
- **`links`**: URLs to the review comment or review, when available.

Note: this metadata should just be a restatement of the input context,
  not something inferred from the review content itself.

### Overall Review Summary (`overall_summary`)

Capture the high-level assessment of the code changes,
  including any overall recommendations for the user.
This should be a concise summary of the reviewer's main points
  and should enumerate critical issues that likely block merging
  and separately enumerate other suggestions for improvement.

A rough template might be:

```markdown
The {extremely brief name for code changes being reviewed} is {overall assessment} {and/but} {is/is not/may be} ready for merge.
There {was/were} {number} critical issue{s} that should be addressed before merging: {extremely brief list of critical issues}.
There {was/were} also {number} other suggestion{s} for improvement: {extremely brief list of other suggestions}.
```

### Individual Suggestions (`suggestions`)

The review content should be analyzed to extract individual suggestions,
  each with the following fields:

- **`summary`**: one-line summary of the suggestion/issue, distinct from the other suggestions in the review.
- **`severity`**: `critical` or `minor`, based on the reviewer's emphasis and any metadata (e.g. GitHub review state).
  - `critical`: indicates issues that likely block merging,
      such as likely bugs, reasonable security concerns,
      divergence from requirements or acceptance criteria,
      and failure to comply with any documented standards for the project.
  - `minor`: indicates suggestions for improvement that
      do not block merging, such as code style suggestions,
      performance optimizations, or general best practices.
- **`link`**: URL to the specific comment or section in the review that discusses this suggestion, if available.
- **`code_references`**: list of file and line number references related to this suggestion.
  - `file`: file path relative to repo root.
  - `line_number_start`: starting line number (1-based).
  - `line_number_end`: ending line number (1-based, inclusive).
- **`description`**: full text of the suggestion/issue,
    including any relevant context, explanation, and suggested fixes.
  If the suggestion is split across multiple parts of the review,
    combine them into a single coherent description.

Note that GitHub PR reviews may have both overall review comments
  and inline comments on specific lines of code.
This skill should extract suggestions from both sources,
  combining them into a single `suggestions` array.
Any inline comments that are already marked as resolved should be ignored.
This resolution state may impact the overall review summary:
  if all inline comments are resolved,
  and there are no other critical issues mentioned in the overall review comment,
  the overall summary you return for the review should reflect that there are no blocking issues.

## Parsing Strategies

### Parsing Claude Bot Reviews

**Section-based parsing:**

Claude bot often uses markdown sections:

```markdown
## Code Review

Overall summary here...

### 🔴 Critical Issues

1. **Issue title** (file.ts:42)
   Description here...

### ⚠️ Warnings

1. **Warning title** (file.ts:89)
   Description here...

### 💡 Suggestions

1. **Suggestion title** (file.ts:15)
   Description here...
```

Extract:

1. Overall summary (text before first issue section).
2. Each issue with severity from section header.
3. File references from issue description.
4. Full issue description including suggested fixes.

### Parsing GitHub PR Reviews

**Body vs inline comments:**

GitHub reviews have:

- **body**: Overall review comment.
- **inline comments**: Comments on specific lines (fetched separately).

**State interpretation:**
- `changes_requested`: One or more of the suggestions are of `critical` severity.
- `commented`: None of the suggestions are of `critical` severity. The changes may be ready for merge.
- `approved`: None of the suggestions are of `critical` severity. The changes are ready for merge.

## Handling Missing Information and Other Edge Cases

**No code references found:**

- Leave code_references empty or omit field.
- Issue is still valid, just not tied to specific location.

**Ambiguous descriptions:**

- Include the full text (or a summary of it,
    if the review/suggestion is more than 3 paragraphs),
    for the user to interpret.

**Review with no specific issues:**

- Just capture the overall summary.
- Empty suggestions list is valid.

**Multiple code references in one suggestion:**

- Use `code_references` list with multiple entries.
- Suggestion can reference several files.

**Issue without clear severity:**

- Default to `minor` unless review state indicates otherwise.
