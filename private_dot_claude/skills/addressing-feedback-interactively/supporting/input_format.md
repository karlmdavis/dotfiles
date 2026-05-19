# Input Format

This skill expects TOON-formatted input with parsed feedback from getting-feedback-local or
  getting-feedback-remote skills.

## TOON Format Structure

```toon
source: local  # or "remote"
review_timestamp: 2026-01-04T16:00:00Z

build_results:
  status: fail_related  # or "all_passed", "fail_unrelated"

  failures[N]:  # Optional - only if build failures exist
    type: test  # or "lint", "build", "type_check"
    location: path/to/file.ts:42
    related_to_changes: true
    reasoning: |
      Explanation of why this failure is related to changes
    messages[M]:
      |
        Error message line 1
      |
        Error message line 2

review:
  status: success  # or "fail", "unavailable"
  source: claude_analysis  # or "tool_output", etc.

  issues[N]:  # Optional - only if review issues exist
    severity: critical  # or "warning", "suggestion"
    code_references[M]:
      file: path/to/file.ts
      line: 42
      # OR
      line_range: 15-20
    description: |
      Detailed description of the issue

summary:
  total_build_failures: 1
  total_review_issues: 2
  critical_review_issues: 1
  overall_status: needs_attention
```

## Field Descriptions

**Top Level:**
- `source`: Where feedback came from ("local" or "remote").
- `review_timestamp`: When review was performed (ISO 8601 format).

**build_results:**
- `status`: Overall build status.
  - `all_passed`: All tests/builds passed.
  - `fail_related`: Failures related to current changes.
  - `fail_unrelated`: Only pre-existing failures unrelated to changes.
- `failures[N]`: Array of build failures (optional, only if failures exist).

**failures[N] items:**
- `type`: Type of failure (test, lint, build, type_check).
- `location`: File path and line number where failure occurred.
- `related_to_changes`: Boolean indicating if failure is related to current changes.
- `reasoning`: Explanation of why failure is/isn't related to changes.
- `messages[M]`: Array of error message lines.

**review:**
- `status`: Review status (success, fail, unavailable).
- `source`: Where review came from (claude_analysis, tool_output, etc.).
- `issues[N]`: Array of review issues (optional, only if issues exist).

**issues[N] items:**
- `severity`: Issue severity level (critical, warning, suggestion).
- `code_references[M]`: Array of code locations referenced by issue.
- `description`: Detailed description of the issue.

**code_references[M] items:**
- `file`: File path.
- `line`: Single line number (for point references).
- `line_range`: Line range like "15-20" (for range references).

**summary:**
- `total_build_failures`: Total count of build failures.
- `total_review_issues`: Total count of review issues.
- `critical_review_issues`: Count of critical severity review issues.
- `overall_status`: Overall assessment (needs_attention, all_clear, etc.).

## Example

See [examples/toon-input-to-presentation.md](../examples/toon-input-to-presentation.md) for a
  complete example of TOON input and how it transforms into user presentation.
