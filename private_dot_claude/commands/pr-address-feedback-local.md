---
description: Iteratively address local feedback (build + review) before committing or creating PR
---

I would like you to gather and address all local feedback (build failures and code review) interactively until everything is clean and ready to commit or create a PR:

## 0. Determine Review Context

**CRITICAL:** Before gathering feedback, determine what changes to review.

**0.a.** Run the getting-branch-state skill to get branch info and changed files:

```bash
cd ~/.claude/skills/getting-branch-state
scripts/check_branch_state.py
```

Parse the TOON output.

**0.b.** Determine review scope from branch state:
- If `local.branch` == `local.base_branch` (on main/master) → review scope is "uncommitted"
- If `local.branch` != `local.base_branch` (on feature branch) → review scope is "branch_vs_base"

**0.c.** Get changed files for review:
- If review scope is "uncommitted": Use `local.uncommitted_files`
- If review scope is "branch_vs_base": Use `comparison.branch_vs_base.changed_files`

**0.d.** Optional: Note PR status if it exists:
- If `pr.exists` is true and `comparison.local_vs_pr.status` is "ahead":
  - You have unpushed commits. Consider pushing before continuing local work.
- If status is "diverged":
  - You've rebased locally. Be aware when interpreting feedback.

**0.e.** Pass context to feedback gathering subagent:
- Provide the list of changed files from step 0.c
- Specify the review scope (uncommitted or branch_vs_base)
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

Note that this is a logical flow, not code to run or the exact messages to show your human partner.

```
Step 0: Determine review context
   - Run getting-branch-state skill
   - Local branch: feature-auth
   - Base branch: main
   - Review scope: branch_vs_base (not on main)
   - Changed files from branch_vs_base: src/api.ts, tests/api.test.ts
   - PR exists: true (#123, status: ahead by 1 commit)
   - Note: Unpushed commits exist, consider pushing later

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
