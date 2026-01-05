---
description: Iteratively address local feedback (build + review) before committing or creating PR
---

I would like you to address all local feedback (build failures and code review) interactively until
  everything is clean and ready to commit or create a PR:

## 0. Determine Review Context

**CRITICAL:** Before gathering feedback, determine what changes to review.

**0.a.** Check current branch and comparison base:

```bash
# Get current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Determine main/master branch
MAIN_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "master")

# Check if on main branch
if [ "$CURRENT_BRANCH" = "$MAIN_BRANCH" ]; then
    REVIEW_SCOPE="staged_or_unstaged"
    CHANGED_FILES=$(git diff --staged --name-only || git diff --name-only)
else
    REVIEW_SCOPE="branch_vs_main"
    CHANGED_FILES=$(git diff $MAIN_BRANCH...HEAD --name-only)
fi
```

**0.b.** Review scope interpretation:
- **On main/master branch** → Review staged changes (or unstaged if nothing staged)
- **On feature branch** → Review all changes on branch vs main/master
- **User can override** by specifying explicit comparison in the command

**0.c.** Pass this context to the feedback gathering subagent:
- Provide the list of changed files
- Specify the comparison base (staged, unstaged, or branch vs main)
- This ensures build relatedness analysis and code review focus on the right changes

## 1. Gather Complete Local Feedback

**1.a.** Spawn a subagent using the Task tool with `subagent_type='general-purpose'` and
  `description="Get complete local feedback"`.
- The subagent prompt should use the `getting-feedback-local` skill.
- **CRITICAL:** Pass the review context from step 0:
  ```
  Review scope: [branch_vs_main|staged_or_unstaged]
  Changed files:
  [list files from step 0]
  ```
- This orchestrates: running local CI, parsing build results, performing code review, parsing review feedback.
- Wait for the subagent to return unified TOON output with complete local feedback.

**1.b.** CRITICAL: The skill MUST run in a subagent, never in main context.
  This prevents token bloat from build logs and review analysis.

## 2. Present Overall Summary

**2.a.** Provide a concise summary showing:
- Total number of build failures (related vs unrelated to changes).
- Total number of review issues (by severity: critical, warning, suggestion).
- Overall status (clean / needs fixes).

**2.b.** List all issues by number with severity and location:
```
Issue 1: [Critical Review] Null pointer in src/api.ts:42
Issue 2: [Test Failure] tests/api.test.ts:42 (related to changes)
Issue 3: [Warning Review] Missing error handling in src/api.ts:89
Issue 4: [Suggestion] Refactor src/utils.ts:15-20
```

## 3. Address Each Issue Interactively

**3.a.** For each issue from the summary (prioritize critical and related):
- Discuss the specific issue in detail.
- Investigate the root cause (read relevant code, understand context).
- Propose a fix and ask the user about the proposal.
- Implement the fix per user direction.

**3.b.** AFTER implementing each fix:
- Run local verification in a subagent to re-check build status.
- Use the `getting-build-results-local` skill to run CI commands.
- Use the `parsing-build-results` skill to parse output.
- Triage the results:
  - **If new failures in files you just modified** → Fix them before proceeding.
  - **If unrelated failures** → Note but continue (they existed before your changes).
  - **If all passing** → Proceed to next issue.

**3.c.** DO NOT commit during the loop - just accumulate fixes.

**3.d.** Work through all issues sequentially until all are addressed.

## 4. Final Verification and Commit Decision

**4.a.** After all issues are fixed, run full local verification one more time:
- Run `getting-feedback-local` again in subagent.
- Confirm all critical issues resolved.

**4.b.** Ask the user what to do next:
- **Option 1:** Commit all changes now.
- **Option 2:** Stage changes but don't commit yet (let user commit manually).
- **Option 3:** Leave changes unstaged (user will stage and commit manually).

**4.c.** If user chooses to commit, create a single comprehensive commit with all fixes:
```bash
git add <files>
git commit -m "Address feedback: [brief summary of what was fixed]"
```

## Important Guidelines

- **Keep initial summary concise** - just counts and numbered list of issues.
- **Address issues one at a time** - don't try to fix multiple simultaneously.
- **Don't commit during the loop** - accumulate fixes, commit once at the end.
- **Re-verify after fixing** - use local CI to catch new failures.
- **Triage objectively** - distinguish between related and unrelated failures.
- **Don't dump giant walls of text** - work iteratively and focused.
- **Let user decide about committing** - don't assume they want to commit immediately.

## Verification Between Fixes

After each fix, before moving to next issue:

```markdown
Use Task tool with subagent_type='general-purpose':

"Run local CI to verify current state.
Use getting-build-results-local skill to run CI commands.
Use parsing-build-results skill to parse output.

Changed files for relatedness analysis:
[list all files modified so far in this session]

Return structured TOON with failures and relatedness determination."
```

Triage the results:
- If `status: all_passed` → Move to next issue.
- If `status: fail_related` → Fix new related failures before proceeding.
- If `status: fail_unrelated` → Note in summary, continue with issues.

## Example Flow

```
1. Gather feedback → 4 issues found
2. Present summary:
   - Issue 1: [Critical] Null pointer src/api.ts:42
   - Issue 2: [Test Failure] tests/api.test.ts:42
   - Issue 3: [Warning] Missing error handling src/api.ts:89
   - Issue 4: [Suggestion] Refactor src/utils.ts:15-20

3. Address Issue 1:
   - Read src/api.ts
   - Add null check
   - Run verification → All passing
   - Move to next issue (don't commit yet)

4. Address Issue 2:
   - Read tests/api.test.ts
   - Update test expectations
   - Run verification → All passing
   - Move to next issue

5. Address Issue 3:
   - Read src/api.ts
   - Add try/catch for database call
   - Run verification → All passing
   - Move to next issue

6. Address Issue 4:
   - Discuss with user: "Suggestion to refactor. Address now or defer?"
   - User says "defer"
   - Skip

7. Final verification:
   - Run getting-feedback-local → All critical issues resolved
   - Ask: "All issues fixed. What next? (commit/stage/leave)"
   - User says "commit"
   - git add src/api.ts tests/api.test.ts
   - git commit -m "Address feedback: fix null pointer, update tests, add error handling"
```

## Use Cases

**Pre-commit workflow:**
- Make changes during development.
- Run `/pr-address-feedback-local` before committing.
- Address all issues.
- Commit clean code.

**Pre-PR workflow:**
- Multiple commits already made.
- Want to verify quality before creating PR.
- Run on all uncommitted/unstaged changes.
- Fix any issues found.
- Create PR with confidence.

**Continuous development:**
- Make changes iteratively.
- Run periodically to catch issues early.
- Fix as you go.
- Maintain high quality throughout.
