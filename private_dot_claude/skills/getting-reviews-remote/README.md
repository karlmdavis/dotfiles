# Agent Skill: `getting-reviews-remote`

Fetches PR review feedback from GitHub for the current commit,
  including PR-level comments,
  formal reviews,
  and review threads nested under their parent reviews.
Primarily implemented as a Python script that queries GitHub's GraphQL API,
  with robust pagination and grouping logic to handle real-world review patterns
  (e.g., Claude bot's tendency to split reviews into multiple comments).
Outputs the reviews as structured TOON to stdout for downstream processing.

## Features

### Data Fetching

- PR-level comments from all users,
    filtered to those posted at or after the commit's push timestamp.
- Formal GitHub PR reviews (filtered to current commit SHA).
  - Review threads nested under those reviews (unresolved and not outdated only).

### Comment Processing

- Groups consecutive split comments from same author within 60 seconds.
  - This grouping is motivated by Claude bot's intermittent behavior
      of splitting a single review across multiple consecutive GitHub comments
      (typically 3-7 parts, posted seconds apart).
  - This grouping heuristic is author-agnostic (not Claude-bot-specific):
      the same logic applies to any commenter rapidly posting consecutive comments.

### Output

- TOON-formatted structured output to stdout.
- All status/error messages to stderr.
- Nested structure:
  - `pr` metadata.
  - `reviews` with `threads`.
  - `other_comments` with comments in `items` (grouped when appropriate).

### Robustness

- 60-second timeout per subprocess command.
- Defensive error handling with informative exit codes (0 = success, 1 = fatal).

## Tests

- Located in `test/skills/test_find_pr_feedback.py`.
- Run with `mise run test-python`.

## Dependencies

- `gh` CLI (GitHub CLI with GraphQL support).
- `uv` (inline script dependency management).
- `toon-format` (0.9.0b1, declared in script header).
