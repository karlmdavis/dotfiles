---
description: Gather and triage all local quality issues (build + review) interactively
argument-hint: everything | uncommitted | branch | branch-dirty
---

I would like you to gather and triage all local quality issues (build failures and code review) interactively until everything is clean and ready to commit or create a PR:

## Scope Argument

The `<scope>` argument determines what code to review:

- `everything` - Full project as it appears in working copy (all files, regardless of git state).
- `uncommitted` - Only staged and unstaged changes (what Git calls "working tree changes").
- `branch` - Committed changes on current branch vs base branch (clean branch comparison).
- `branch-dirty` - Current branch + uncommitted changes vs base branch (branch with WIP).

If no argument provided, defaults to `branch-dirty` (most common use case).

## Review Scope Determination

Based on the scope argument:

- `everything` → Review all files in project.
- `uncommitted` → Review files from `local.uncommitted_files` (from getting-branch-state).
- `branch` → Review files from `comparison.branch_vs_base.changed_files` (committed only).
- `branch-dirty` → Review files from `comparison.branch_vs_base.changed_files` + `local.uncommitted_files` (union).

## 0. Determine Review Context

**0.a.** Parse scope argument from command invocation:
- If argument provided: Use specified scope.
- If no argument: Default to `branch-dirty`.

**0.b.** Run the getting-branch-state skill to get branch info:

```bash
cd ~/.claude/skills/getting-branch-state
scripts/check_branch_state.py
```

Parse the TOON output and store for later use.

**0.c.** Determine file list based on scope:

- If scope is `everything`:
  - Get all tracked files: `git ls-files`
  - Review scope: "full project"

- If scope is `uncommitted`:
  - Use `local.uncommitted_files` from branch state
  - Review scope: "uncommitted changes"

- If scope is `branch`:
  - Use `comparison.branch_vs_base.changed_files` from branch state
  - Review scope: "branch changes"

- If scope is `branch-dirty`:
  - Combine `comparison.branch_vs_base.changed_files` + `local.uncommitted_files` (deduplicated)
  - Review scope: "branch with uncommitted changes"

**0.d.** Pass context to feedback gathering subagent:
- Provide the list of changed files from step 0.c
- Specify the review scope for context
- Pass complete branch state TOON for potential use by parsing skills

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
   - Scope argument: branch-dirty (default)
   - Run getting-branch-state skill
   - Local branch: feature-auth
   - Base branch: main
   - Changed files (branch): src/api.ts, tests/api.test.ts
   - Uncommitted files: src/utils.ts
   - Combined scope: src/api.ts, tests/api.test.ts, src/utils.ts
   - Review scope: "branch with uncommitted changes"

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
- Run `/quality-triage` before committing.
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
