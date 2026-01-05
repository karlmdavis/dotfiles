---
description: Iteratively address PR feedback from workflows and reviews until all issues resolved
---

I would like you to address all PR feedback (workflow failures and review comments) interactively until
  everything is resolved and ready to merge:

## 1. Gather Complete PR Feedback

**1.a.** Spawn a subagent using the Task tool with `subagent_type='general-purpose'` and
  `description="Get complete PR feedback"`.
- The subagent prompt should use the `getting-feedback-remote` skill.
- This orchestrates: waiting for workflows, fetching build results, fetching reviews.
- Wait for the subagent to return unified TOON output with complete PR feedback.

**1.b.** CRITICAL: The skill MUST run in a subagent, never in main context.
  This prevents token bloat from workflow logs and review text.

## 2. Present Overall Summary

**2.a.** Provide a concise summary showing:
- Total number of workflow failures (if any).
- Total number of build failures from failed workflows (related vs unrelated to changes).
- Total number of review issues (by severity: critical, warning, suggestion).
- Total number of unresolved earlier comments.
- Overall PR status (ready to merge / needs fixes).

**2.b.** List all issues by number with severity and location:
```
Issue 1: [Critical Review] Null pointer in src/api.ts:42
Issue 2: [Test Failure] tests/api.test.ts:42 (related to changes)
Issue 3: [Warning Review] Missing error handling in src/api.ts:89
Issue 4: [Unresolved] src/auth.ts:15-18 (from earlier commit)
```

## 3. Address Each Issue Interactively

**3.a.** For each issue from the summary (prioritize critical and related):
- Discuss the specific issue in detail.
- Investigate the root cause (read relevant code, understand context).
- Propose a fix and ask the user about the proposal.
- Implement the fix per user direction.

**3.b.** BEFORE committing each fix:
- Run local pre-commit verification in a subagent.
- Use the `getting-build-results-local` skill to run CI commands.
- Use the `parsing-build-results` skill to parse output.
- Triage the results:
  - **If new failures in files you just modified** → Fix them before committing.
  - **If unrelated failures** → Ask user how to proceed (commit anyway / fix first / skip).
  - **If all passing** → Proceed with commit.

**3.c.** After successful verification, commit the fix:
- Use clear commit message referencing what was fixed.
- DO NOT ask for permission to commit - just make the commit.

**3.d.** Work through all issues sequentially until all are addressed.

## 4. Final Verification and Push

**4.a.** After all issues are fixed and committed, verify the branch is ready:
- Run local CI one more time if needed.
- Confirm all changes are committed.

**4.b.** Ask once whether to push all commits to the remote branch.

**4.c.** If user confirms, push to remote.

## Important Guidelines

- **Keep initial summary concise** - just counts and numbered list of issues.
- **Address issues one at a time** - don't try to fix multiple simultaneously.
- **Commit fixes separately** - one commit per logical fix.
- **Verify before each commit** - use local CI to catch new failures.
- **Triage objectively** - don't ignore unrelated failures, but don't block on them unnecessarily.
- **Don't dump giant walls of text** - work iteratively and focused.
- **Only ask about pushing at the very end** - not for each commit.

## Pre-Commit Verification Details

For each fix, before committing:

```markdown
Use Task tool with subagent_type='general-purpose':

"Run local CI to verify changes.
Use getting-build-results-local skill to run CI commands.
Use parsing-build-results skill to parse output.

Changed files for relatedness analysis:
[list files you just modified]

Return structured TOON with failures and relatedness determination."
```

Triage the results:
- If `status: all_passed` → Commit immediately.
- If `status: fail_related` → Fix related failures before committing.
- If `status: fail_unrelated` → Ask user: "Unrelated failures exist. Commit anyway? (yes/no/fix)"

## Example Flow

```
1. Gather feedback → 3 issues found
2. Present summary:
   - Issue 1: [Critical] Null pointer src/api.ts:42
   - Issue 2: [Test Failure] tests/api.test.ts:42
   - Issue 3: [Suggestion] Refactor src/utils.ts:15-20

3. Address Issue 1:
   - Read src/api.ts
   - Add null check
   - Run local verification → All passing
   - Commit "fix: add null check in src/api.ts:42"

4. Address Issue 2:
   - Read tests/api.test.ts
   - Update test expectations
   - Run local verification → All passing
   - Commit "test: update api.test.ts expectations"

5. Address Issue 3:
   - Discuss with user: "Suggestion to refactor validation. Address now or defer?"
   - User says "defer"
   - Skip to next

6. All critical issues resolved
   - Ask: "Push 2 commits to remote? (yes/no)"
   - User says "yes"
   - Push to remote
```
