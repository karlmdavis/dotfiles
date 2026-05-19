# Getting Reviews Remote: Output Details

The results produced by the `getting-reviews-remote` skill
  provide structured review feedback for a specific PR commit.
They should be largely self-explanatory,
  but here are some additional details to help interpret the results.

## TOON Format Overview

Many steps will produce and/or consume TOON-formatted data,
  which is a structured data format suited for use by agents.
TOON is similar to JSON and YAML but uses 2-space indents and arrays show length and fields.
Here's a small toy example:

```toon
context:
  task: Our favorite hikes together
  location: Boulder
  season: spring_2025
friends[3]: ana,luis,sam
hikes[3]{id,name,distanceKm,elevationGain,companion,wasSunny}:
  1,Blue Lake Trail,7.5,320,ana,true
  2,Ridge Overlook,9.2,540,luis,false
  3,Wildflower Loop,5.1,180,sam,true
```

## Example Output

```toon
pr_feedback:
  pr:
    number: 456
    url: https://github.com/owner/repo/pull/456
    commit: 7a3f9e2c1b8d4e6f0a2b5c8d9e1f3a4b6c7d8e9f

  reviews:
    - url: 'https://github.com/owner/repo/pull/456#pullrequestreview-789'
      fullDatabaseId: '12345678'
      author: teammate-alice
      commit: 7a3f9e2c1b8d4e6f0a2b5c8d9e1f3a4b6c7d8e9f
      createdAt: '2026-02-13T15:00:00Z'
      threads:
        - path: src/api.ts
          startDiffSide: RIGHT
          diffSide: RIGHT
          startLine: 42
          line: 42
          originalStartLine: 42
          originalLine: 42
          isOutdated: false
          isResolved: false
          comments:
            - url: 'https://github.com/.../r123'
              fullDatabaseId: '99887766'
              author: teammate-alice
              createdAt: '2026-02-13T15:05:00Z'
              diffHunk: '@@ -40,6 +40,7 @@...'
              path: src/api.ts
              line: 42
              startLine: 42
              originalLine: 42
              originalStartLine: 42
              diffSide: RIGHT
              startDiffSide: RIGHT
              subjectType: LINE

  other_comments:
    - author: teammate-bob
      items[1]{url,fullDatabaseId,createdAt}:
        https://github.com/owner/repo/pull/456#issuecomment-123,11223344,2026-02-13T14:00:00Z

    - author: claude[bot]
      items[3]{url,fullDatabaseId,createdAt}:
        https://github.com/owner/repo/pull/456#issuecomment-201,55660001,2026-02-13T15:00:00Z
        https://github.com/owner/repo/pull/456#issuecomment-202,55660002,2026-02-13T15:00:18Z
        https://github.com/owner/repo/pull/456#issuecomment-203,55660003,2026-02-13T15:00:35Z
```

## Output Fields

| Field | Description |
|-------|-------------|
| `pr_feedback.pr.number` | PR number. |
| `pr_feedback.pr.url` | PR URL. |
| `pr_feedback.pr.commit` | Commit SHA the feedback was fetched for. |
| `pr_feedback.reviews[]` | Reviews matching the specified commit. |
| `pr_feedback.reviews[].url` | Review URL on GitHub. |
| `pr_feedback.reviews[].fullDatabaseId` | Review database ID. |
| `pr_feedback.reviews[].author` | Review author login. |
| `pr_feedback.reviews[].commit` | Commit SHA the review was submitted against. |
| `pr_feedback.reviews[].createdAt` | Review creation timestamp. |
| `pr_feedback.reviews[].threads[]` | Unresolved, non-outdated inline threads nested under the review. |
| `pr_feedback.reviews[].threads[].path` | File path the thread applies to. |
| `pr_feedback.reviews[].threads[].line` | Line number in the diff. |
| `pr_feedback.reviews[].threads[].isResolved` | Always `false` (resolved threads are filtered out). |
| `pr_feedback.reviews[].threads[].isOutdated` | Always `false` (outdated threads are filtered out). |
| `pr_feedback.reviews[].threads[].comments[]` | Comments within the thread (includes diff hunk context). |
| `pr_feedback.other_comments[]` | Top-level PR comments grouped by author. |
| `pr_feedback.other_comments[].author` | Comment author login. |
| `pr_feedback.other_comments[].items[]` | Comments with url, fullDatabaseId, and createdAt. |

## Filtering Strategy

The script applies the following filters to return only actionable feedback:

- **Reviews:** Only reviews where `commit.oid` matches the specified commit SHA.
- **Threads:** Only threads that are `isResolved: false` and `isOutdated: false`,
    nested under their parent review from the commit-filtered set.
- **Other comments:** Only comments posted at or after the commit's `pushedDate`
    (earlier discussion is considered stale).
