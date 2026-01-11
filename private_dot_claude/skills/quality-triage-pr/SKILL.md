---
description: Gather and triage all PR quality issues (workflows + reviews) interactively
user-invocable: true
disable-model-invocation: true
tools: Bash, Edit, Skill, WebFetch, WebSearch, Write, LSP, mcp__ide__getDiagnostics, mcp__ide__executeCode
---

I would like you to gather all PR feedback (workflow failures and review comments) and then interactively guide the user through addressing all of that PR feedback. I will give you a checklist of Triage Steps 1 though 4 and ask you to track your progress through them. Some Triage Steps will have their own checklists and steps, which you will be asked to track your progress through, as well.

Many steps will produce and/or consume TOON-formatted data, which is a structured data format suited for use by agents. TOON is similar to JSON and YAML but uses 2-space indents and arrays show length and fields. Here's a small toy example:

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

This checklist specifies the top-level Triage Steps for the PR quality triage process. Copy this checklist and track your progress through it:

```
PR Quality Triage Progress:
[ ] Triage Step 1: Check Branch State and PR Sync Status
[ ] Triage Step 2: Gather Complete PR Feedback
[ ] Triage Step 3: Address Issues Interactively
[ ] Triage Step 4: Push Changes to Remote, Maybe
```

## Triage Step 1: Check Branch State and PR Sync Status

See [Triage Step 1: Check Branch State and PR Sync Status](triage_steps/triage_step_1_check_status.md) and follow its instructions.

## Triage Step 2: Gather Complete PR Feedback

**2.a.** Spawn a subagent using the Task tool with `subagent_type='quality-data-extractor'` and
  `description="Get complete PR feedback"`.
- The subagent prompt should use the `getting-feedback-remote` skill.
- This orchestrates: waiting for workflows, fetching build results, fetching reviews.
- Wait for the subagent to return unified TOON output with complete PR feedback.
- No need to display this returned feedback to the user, as Step 2 will do that.

**2.b.** CRITICAL: The skill MUST run in a subagent, never in main context.
  This prevents token bloat from workflow logs and review text.

## Triage Step 3: Address Issues Interactively

**3.a.** Use the `addressing-feedback-interactively` skill to handle all issue resolution:

```markdown
Use Skill tool with skill='addressing-feedback-interactively':

Pass the complete TOON feedback from Step 2.

The skill will:
- Ask user to choose commit strategy (incremental/accumulated/manual)
  - Recommend "incremental" for PR workflow
- Present unified summary of all issues with priorities
- Work through each issue interactively
- Verify fixes after each change
- Create commits based on user's chosen strategy
```

**3.b.** The skill handles:
- Commit strategy selection (with recommendation)
- Issue presentation in priority order
- Interactive resolution with user approval
- Verification after each fix
- Commits based on strategy

## Triage Step 4: Push Changes to Remote, Maybe

**4.a.** After all issues are addressed and committed, ask user once:

```
All issues resolved with {N} commit(s).

Push to remote branch? (yes/no)
```

**4.b.** If user confirms, push:

```bash
git push
```

## Example Flow

Note that this is a logical flow, not code to run or the exact messages to show your user.

```
Step 1: Check branch state
   - Run getting-branch-state skill
   - Local: feature-auth (abc123d)
   - PR: #123 (def456a)
   - Status: ahead (2 commits)
   - Warn: "Local is 2 commits ahead of PR"
   - User chooses: "Push now and re-run"
   - Push commits
   - Exit: "Pushed successfully. Re-run /quality-triage-pr to get fresh feedback."

(On re-run, Step 1 shows in_sync, proceeds to Step 2)

Step 2: Gather PR feedback
   - Run getting-feedback-remote skill in subagent
   - Waits for workflows to complete
   - Fetches build logs and review comments
   - Returns: 3 issues (2 critical, 1 suggestion)

Step 3: Address issues interactively
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

   - Skill addresses Issue 3: [Suggestion] Refactor src/utils.ts:15-20
     - Asks: "Address now or defer?"
     - User says "defer"
     - Skips

Step 4: Push to remote
   - Ask: "All issues resolved with 2 commits. Push to remote? (yes/no)"
   - User says "yes"
   - git push

Done! PR updated with fixes. Workflows will run again.
```
