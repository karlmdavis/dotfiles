---
description: Iteratively address local feedback (build + review) before committing or creating PR
---

I would like you to address all local feedback (build failures and code review) interactively until
  everything is clean and ready to commit or create a PR:

## 0. Determine Review Context

**CRITICAL:** Before gathering feedback, determine what changes to review.

**0.a.** Determine review scope with separate simple commands:

First, check current branch:
```bash
git rev-parse --abbrev-ref HEAD
```

Then determine the main branch (usually main or master):
```bash
git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'
```

If that fails (no remote HEAD set), check which exists:
```bash
git show-ref --verify refs/heads/main >/dev/null 2>&1 && echo "main" || echo "master"
```

**Logic to apply:**
- If current branch == main/master → review scope is "staged_or_unstaged"
- If current branch != main/master → review scope is "branch_vs_main"

Get changed files based on scope:
```bash
# For staged_or_unstaged:
git diff --staged --name-only || git diff --name-only

# For branch_vs_main (replace MAIN with actual main branch name):
git diff MAIN...HEAD --name-only
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

## 2. Address Issues Interactively

**2.a.** Use the `addressing-feedback-interactively` skill to handle all issue resolution:

```markdown
Use Skill tool with skill='addressing-feedback-interactively':

Pass the complete TOON feedback from Step 1.

The skill will:
- Ask user to choose commit strategy (incremental/accumulated/manual)
  - Recommend "accumulated" for local development
- Present unified summary of all issues with priorities
- Work through each issue interactively
- Verify fixes after each change
- Create commits based on user's chosen strategy
```

**2.b.** The skill handles:
- Commit strategy selection (with recommendation)
- Issue presentation in priority order
- Interactive resolution with user approval
- Verification after each fix
- Final commits and verification

## Example Flow

```
Step 0: Determine review scope
   - Current branch: feature-auth
   - Main branch: main
   - Review scope: branch_vs_main
   - Changed files: src/api.ts, tests/api.test.ts

Step 1: Gather feedback
   - Run getting-feedback-local skill in subagent
   - Returns: 3 issues (2 critical, 1 suggestion)

Step 2: Address issues interactively
   - Skill asks: "How would you like to commit fixes?"
   - User chooses: "Accumulated" (recommended for local)

   - Skill presents summary:
     Issue 1: [Critical] Null pointer src/api.ts:42
     Issue 2: [Test Failure] tests/api.test.ts:42
     Issue 3: [Suggestion] Refactor src/utils.ts:15-20

   - Skill addresses Issue 1:
     - Reads src/api.ts
     - Adds null check
     - Verifies (passed)
     - Continues (no commit yet)

   - Skill addresses Issue 2:
     - Reads tests/api.test.ts
     - Updates test expectations
     - Verifies (passed)
     - Continues (no commit yet)

   - Skill addresses Issue 3:
     - Asks: "Address now or defer?"
     - User says "defer"
     - Skips

   - Skill creates final commit (accumulated strategy):
     - git add src/api.ts tests/api.test.ts
     - git commit -m "Address feedback: fix null pointer, update tests"
     - Final verification (all passed)

Done! Ready to create PR or continue development.
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
