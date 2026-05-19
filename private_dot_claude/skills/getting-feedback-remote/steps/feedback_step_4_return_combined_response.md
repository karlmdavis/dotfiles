## Feedback Step 4: Combine and Return

Merge all feedback into unified TOON structure:
- Workflow summary.
- Build failures (parsed and categorized).
- Review issues (categorized by severity).
- Overall counts and status.
- Recommendation for next steps.

TODO: resolve dupes:

Combine all outputs into unified TOON structure as shown in Return Format above.

Calculate summary:.
- Count total failures (by type).
- Count review issues (by severity).
- Count unresolved earlier comments.
- Determine overall status
- Generate recommendation.


Based on the feedback, generate actionable recommendation:

All clear:
```
All checks passed! Ready to merge.
```

Build failures only:
```
Fix 2 related build failures before merge.
1 unrelated failure can be addressed separately.
```

Review issues only:
```
Address 2 critical review issues before merge.
3 suggestions can be addressed optionally.
```

Both:
```
Fix 2 related build failures and 2 critical review issues before merge.
Also address 1 unresolved earlier comment.
```

Overall Status Values

- `all_clear` - All workflows passed, no review issues
- `needs_attention` - Failures or critical review issues
- `warnings_only` - Minor issues or suggestions only
- `blocked` - Can't proceed (no PR, unpushed commits, timeout)

## Return Format

```toon
status: needs_attention
pr_number: 123
current_commit: a1b2c3d

workflows:
  complete: true
  wait_time_seconds: 342
  results[3]:
    name: CI Tests
    status: completed
    conclusion: failure
    duration_seconds: 298
    url: https://github.com/.../runs/19727163744

    name: Lint
    status: completed
    conclusion: success
    duration_seconds: 45
    url: https://github.com/.../runs/19727163745

    name: Type Check
    status: completed
    conclusion: success
    duration_seconds: 23
    url: https://github.com/.../runs/19727163746

build_results:
  status: fail_related

  ci_commands[2]:
    id: 1
    command: npm test
    exit_code: 1
    duration_seconds: 298

    id: 2
    command: npm run type-check
    exit_code: 0
    duration_seconds: 23

  failures[2]:
    type: test
    location: tests/api.test.ts:42
    source_command_id: 1
    related_to_changes: true
    reasoning: |
      Test file tests/api.test.ts was modified in this commit.
    messages[2]:
      |
        FAIL tests/api.test.ts
          ● should handle null user
      |
        TypeError: Cannot read property 'id' of null
          at handler (src/api.ts:89)

    type: test
    location: tests/auth.test.ts:15
    source_command_id: 1
    related_to_changes: false
    reasoning: |
      Test file tests/auth.test.ts was not modified in this commit.
      Pre-existing failure.
    messages[1]:
      |
        FAIL tests/auth.test.ts
          ● should validate user token

  recommendation: fix_related_first

reviews:
  status: success
  pr_number: 123
  current_commit: a1b2c3d

  claude_bot_review:
    updated_at: 2026-01-04T15:30:00Z
    link: https://github.com/.../issuecomment-123
    overall_summary: |
      Overall the changes look solid! Found 2 critical issues.
      Recommendation: Address critical issues, then ready to merge.

    issues[2]:
      severity: critical
      code_references[1]:
        file: src/api.ts
        line: 42
      description: |
        **Null pointer risk**
        The user object may be null here. Add null check.

      severity: suggestion
      code_references[1]:
        file: src/utils.ts
        line_range: 15-20
      description: |
        **Consider refactoring**
        Extract validation logic into separate function.

  github_reviews[1]:
    reviewer: alice
    state: changes_requested
    summary: |
      Nice work! Add error handling to database calls.
    inline_comments[1]:
      code_references[1]:
        file: src/api.ts
        line: 89
      description: |
        Error handling missing in database call.

  unresolved_earlier[1]:
    link: https://github.com/.../discussion_r123
    reviewer: alice
    code_references[1]:
      file: src/auth.ts
      line_range: 15-18
    summary: Handle edge case when user validation fails

summary:
  total_workflow_failures: 1
  total_build_failures: 2
  total_review_issues: 4
  unresolved_earlier_count: 1
  overall_status: needs_attention
  recommendation: |
    Fix 2 related build failures and 2 critical review issues before merge.
    Also address 1 unresolved earlier comment.
```
