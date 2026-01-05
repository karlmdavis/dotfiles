---
name: parsing-review-suggestions
description: Parse raw review text into structured issues - extracts severity, code references, descriptions from Claude bot reviews, GitHub PR reviews, and unresolved threads
---

# Parsing Review Suggestions

## Overview

Parse raw review feedback (from Claude bot, GitHub reviewers, and unresolved threads) into structured TOON format with issues, code references, and severity levels.

**Core principle:** This is an agent-only skill. Claude naturally understands review text and can extract structured information.

**Input:** Raw review text (from `getting-reviews-remote` or `getting-review-local`)

**Output:** Structured TOON with categorized issues and code references

## When to Use

Use when you need to:
- Parse Claude bot review recommendations into actionable issues
- Structure GitHub PR review feedback
- Extract code references and severity from review text

**When NOT to use:**
- Need to fetch reviews (use getting-reviews-* skills first)
- Reviews already structured

## Concrete Example

**Input (raw Claude bot review comment):**

```markdown
## Code Review

Great work on the authentication refactor! The overall structure is solid.
Found a few issues that need attention:

### 🔴 Critical Issues

1. **Null pointer risk** (src/api.ts:42)
   The user object may be null here. Add null check before accessing properties.

   Suggested fix:
   ```typescript
   if (!user) {
     throw new Error('User not found');
   }
   return user.id;
   ```

### 💡 Suggestions

1. **Consider error handling** (src/api.ts:89)
   Database call should have try/catch for better error handling.

Recommendation: Address the critical issue before merging.
```

**Output (parsed TOON):**

```toon
status: success
pr_number: 123
current_commit: a1b2c3d

claude_bot_review:
  updated_at: 2026-01-04T15:30:00Z
  link: https://github.com/.../issuecomment-123
  overall_summary: |
    Great work on the authentication refactor! The overall structure is solid.
    Found a few issues that need attention.

    Recommendation: Address the critical issue before merging.

  issues[2]:
    severity: critical
    link: https://github.com/.../issuecomment-123#issue-1
    code_references[1]:
      file: src/api.ts
      line: 42
    description: |
      **Null pointer risk**

      The user object may be null here. Add null check before accessing
      properties.

      Suggested fix:
      ```typescript
      if (!user) {
        throw new Error('User not found');
      }
      return user.id;
      ```

    severity: suggestion
    link: https://github.com/.../issuecomment-123#issue-2
    code_references[1]:
      file: src/api.ts
      line: 89
    description: |
      **Consider error handling**

      Database call should have try/catch for better error handling.

github_reviews[0]:

unresolved_earlier[0]:
```

## What to Extract

### 1. Claude Bot Review

Parse Claude bot comment for:
- **overall_summary** - Overall assessment and recommendation
- **issues** - List of specific issues with:
  - severity: "critical", "warning", "suggestion"
  - link: Link to specific issue (if available)
  - code_references: List of file:line locations
  - description: Full issue description

### 2. GitHub PR Reviews

For each GitHub review, extract:
- **reviewer** - GitHub username
- **state** - "approved", "changes_requested", "commented"
- **submitted_at** - When review was submitted
- **review_link** - URL to review
- **summary** - Overall review comment (from body)
- **inline_comments** - Specific code comments (if mentioned in body)

### 3. Unresolved Earlier Threads

For each unresolved thread, extract:
- **link** - URL to thread
- **reviewer** - Who started the thread
- **code_references** - Where the comment was made
- **summary** - What the unresolved issue is about

## Severity Detection

**Claude Bot Reviews:**

Look for emoji indicators:
- 🔴 or "Critical" → severity: "critical"
- ⚠️ or "Warning" → severity: "warning"
- 💡 or "Suggestion" → severity: "suggestion"

Or markdown headers:
- "### 🔴 Critical Issues"
- "### ⚠️ Warnings"
- "### 💡 Suggestions"

**GitHub Reviews:**

Based on state:
- `changes_requested` → Treat as critical
- `commented` → Treat as suggestion
- `approved` → No issues (summary only)

## Code Reference Extraction

Look for these patterns in review text:

**File:line format:**
```
src/api.ts:42
tests/utils.test.ts:15
```

**File with line range:**
```
src/api.ts:15-18
src/auth.ts#L42-L45
```

**Markdown code references:**
```
In `src/api.ts` at line 42...
```

**Stack trace references:**
```
at handler (src/api.ts:89)
```

For each issue, create a `code_references` list:
```toon
code_references[2]:
  file: src/api.ts
  line: 42

  file: src/utils.ts
  line_range: 15-18
```

## Return Format

```toon
status: success
pr_number: 123
current_commit: a1b2c3d

claude_bot_review:
  updated_at: 2026-01-04T15:30:00Z
  link: https://github.com/.../issuecomment-123
  overall_summary: |
    Overall the changes look solid! Found 2 critical issues that need
    addressing before merge. The authentication refactoring is well-structured.

    Recommendation: Address critical issues, then ready to merge.

  issues[3]:
    severity: critical
    link: https://github.com/.../issuecomment-123#ref-42
    code_references[1]:
      file: src/api.ts
      line: 42
    description: |
      **Null pointer risk**

      The user object may be null here. Add null check before accessing
      properties.

      Suggested fix:
      ```typescript
      if (user) {
        return user.id;
      }
      ```

    severity: critical
    link: https://github.com/.../issuecomment-123#ref-89
    code_references[1]:
      file: src/api.ts
      line: 89
    description: |
      **Missing error handling**

      Database call should have try/catch for better error handling.

    severity: suggestion
    link: https://github.com/.../issuecomment-123#ref-15
    code_references[1]:
      file: src/utils.ts
      line_range: 15-20
    description: |
      **Consider refactoring**

      This validation logic could be extracted into a separate function
      for better reusability.

github_reviews[2]:
  reviewer: alice
  state: changes_requested
  submitted_at: 2026-01-04T14:00:00Z
  review_link: https://github.com/.../pullrequestreview-789
  summary: |
    Nice work on the authentication refactoring! The overall structure
    is good, but I have a few concerns about error handling and testing.

    Changes requested - see inline comments.

  inline_comments[2]:
    reviewer: alice
    link: https://github.com/.../discussion_r456
    code_references[1]:
      file: src/api.ts
      line: 89
    description: |
      Error handling missing in database call. What happens if the
      connection fails?

    reviewer: alice
    link: https://github.com/.../discussion_r457
    code_references[1]:
      file: tests/api.test.ts
      line: 42
    description: |
      Consider adding an integration test for the full authentication
      flow, not just unit tests.

  reviewer: bob
  state: approved
  submitted_at: 2026-01-04T14:30:00Z
  review_link: https://github.com/.../pullrequestreview-790
  summary: LGTM! Nice refactoring.

unresolved_earlier[1]:
  link: https://github.com/.../discussion_r123
  reviewer: alice
  code_references[1]:
    file: src/auth.ts
    line_range: 15-18
  summary: Handle edge case when user validation fails
```

## Parsing Claude Bot Reviews

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
1. Overall summary (text before first issue section)
2. Each issue with severity from section header
3. File references from issue description
4. Full issue description including suggested fixes

**Link generation:**

If Claude bot comment doesn't have per-issue links, generate anchor links:
```
https://github.com/.../issuecomment-123#ref-42
```

## Parsing GitHub Reviews

**Body vs inline comments:**

GitHub reviews have:
- **body**: Overall review comment
- **inline comments**: Comments on specific lines (fetched separately)

For this skill, if the review body mentions specific code locations, extract those as inline_comments. The actual inline comment fetching would require additional API calls (not done by getting-reviews-remote script currently).

**State interpretation:**
- `changes_requested` → Critical severity
- `commented` → Suggestion severity
- `approved` → No issues, just summary

## Parsing Unresolved Threads

Unresolved threads are simpler:
- Extract file:line from body text
- Summarize what the unresolved issue is
- Include link and reviewer

## Handling Missing Information

**No code references found:**
- Leave code_references empty or omit field
- Issue is still valid, just not tied to specific location

**No severity markers:**
- Default to "suggestion" for Claude bot issues
- Use review state for GitHub reviews

**Ambiguous descriptions:**
- Include full text, let main context interpret

## Integration with Other Skills

**Used by:**
- `getting-feedback-local` - Parses local review output
- `getting-feedback-remote` - Parses PR review feedback

**Dependencies:**
- Requires raw review text from `getting-reviews-remote` or `getting-review-local`

## Usage Pattern

This is an agent-only skill. Caller provides raw review text, agent parses and returns structured TOON.

**Example caller pattern:**
```markdown
Use Task tool with subagent_type='general-purpose':

"Parse the following PR review feedback using the parsing-review-suggestions skill.

PR #123, commit a1b2c3d

Claude bot comment:
[paste Claude bot review here]

GitHub reviews:
[paste GitHub review data here]

Unresolved threads:
[paste unresolved thread data here]

Return structured TOON output with all issues categorized by severity and
code references extracted."
```

## Common Mistakes

**Missing code references**
- **Problem:** Don't extract file:line from issue descriptions
- **Fix:** Scan all text for file path patterns

**Not handling line ranges**
- **Problem:** Only capture single lines, miss ranges like "15-18"
- **Fix:** Support both single lines and ranges in code_references

**Losing issue context**
- **Problem:** Extract location but not full description
- **Fix:** Include complete issue description including suggested fixes

**Not extracting overall summary**
- **Problem:** Miss high-level recommendations
- **Fix:** Capture overall review assessment before diving into issues

## Edge Cases

**Review with no specific issues:**
- Just capture overall_summary
- Empty issues list is valid

**Multiple code references in one issue:**
- Use code_references list with multiple entries
- Issue can reference several files

**Issue without clear severity:**
- Default to "suggestion" unless review state indicates otherwise

**Inline comments not in review body:**
- Note in comments that inline details may be available via API
- Main context can fetch if needed
