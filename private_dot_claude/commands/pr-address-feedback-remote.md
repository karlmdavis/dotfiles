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

## 2. Address Issues Interactively

**2.a.** Use the `addressing-feedback-interactively` skill to handle all issue resolution:

```markdown
Use Skill tool with skill='addressing-feedback-interactively':

Pass the complete TOON feedback from Step 1.

The skill will:
- Ask user to choose commit strategy (incremental/accumulated/manual)
  - Recommend "incremental" for PR workflow
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
- Commits based on strategy

## 3. Push to Remote

**3.a.** After all issues are addressed and committed, ask user once:

```
All issues resolved with {N} commit(s).

Push to remote branch? (yes/no)
```

**3.b.** If user confirms, push:

```bash
git push
```

## Example Flow

```
Step 1: Gather PR feedback
   - Run getting-feedback-remote skill in subagent
   - Waits for workflows to complete
   - Fetches build logs and review comments
   - Returns: 3 issues (2 critical, 1 suggestion)

Step 2: Address issues interactively
   - Skill asks: "How would you like to commit fixes?"
   - User chooses: "Incremental" (recommended for PRs)

   - Skill presents summary:
     Issue 1: [Critical] Null pointer src/api.ts:42
     Issue 2: [Test Failure] tests/api.test.ts:42
     Issue 3: [Suggestion] Refactor src/utils.ts:15-20

   - Skill addresses Issue 1:
     - Reads src/api.ts
     - Adds null check
     - Verifies (passed)
     - Commits "fix: add null check in src/api.ts:42"

   - Skill addresses Issue 2:
     - Reads tests/api.test.ts
     - Updates test expectations
     - Verifies (passed)
     - Commits "test: update api.test.ts expectations"

   - Skill addresses Issue 3:
     - Asks: "Address now or defer?"
     - User says "defer"
     - Skips

Step 3: Push to remote
   - Ask: "All issues resolved with 2 commits. Push to remote? (yes/no)"
   - User says "yes"
   - git push

Done! PR updated with fixes. Workflows will run again.
```
