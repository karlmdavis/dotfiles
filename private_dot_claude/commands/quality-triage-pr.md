---
description: Gather and triage all PR quality issues (workflows + reviews) interactively
---

I would like you to gather and address all PR feedback (workflow failures and review comments) interactively until everything is resolved and ready to merge:

## 0. Check Branch State and PR Sync

**0.a.** Run the getting-branch-state skill to check local/PR sync status:

Use Skill tool with skill='getting-branch-state'.

Parse the TOON output.

**0.b.** Verify PR exists:
- If `pr.exists` is false → Error: "No PR found for current branch. Create a PR first."

**0.c.** Check sync status (`comparison.local_vs_pr.status`):

If status is `in_sync`:
- ✅ Proceed to Step 1.

If status is `ahead`, `behind`, or `diverged`:
- ⚠️ Warn the user about the mismatch.
- Show the specific situation:
  - If `ahead`: "Local is {ahead_count} commit(s) ahead of PR"
  - If `behind`: "Local is {behind_count} commit(s) behind PR"
  - If `diverged`: "Local and PR have diverged ({ahead_count} ahead, {behind_count} behind)"
- Show commit lists from `ahead_commits` and/or `behind_commits`.
- Explain: "PR feedback will be for commit {pr.head_short}, not your local {local.head_short}."

Present options using AskUserQuestion:
```markdown
**Question:** "Local and PR branches are out of sync. How would you like to proceed?"

**Options:**
1. "Push now and re-run" (recommended for 'ahead' or 'diverged')
   - Description: "Push your local commits to the PR, then re-run this command to get fresh feedback"
2. "Pull first" (recommended for 'behind')
   - Description: "Pull PR commits to your local branch first, then re-run this command"
3. "Continue anyway"
   - Description: "Get feedback for the old PR commit (won't match your local code)"
4. "Cancel"
   - Description: "Stop and handle the sync issue manually"
```

Based on user choice:
- Option 1: Push with `git push`, then exit with message to re-run command.
- Option 2: Pull with `git pull`, then exit with message to re-run command.
- Option 3: Continue to Step 1 (accept mismatch).
- Option 4: Exit cleanly.

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

Note that this is a logical flow, not code to run or the exact messages to show your user.

```
Step 0: Check branch state
   - Run getting-branch-state skill
   - Local: feature-auth (abc123d)
   - PR: #123 (def456a)
   - Status: ahead (2 commits)
   - Warn: "Local is 2 commits ahead of PR"
   - User chooses: "Push now and re-run"
   - Push commits
   - Exit: "Pushed successfully. Re-run /quality-triage-pr to get fresh feedback."

(On re-run, Step 0 shows in_sync, proceeds to Step 1)

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
