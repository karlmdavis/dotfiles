---
description: Gather and triage all PR quality issues (workflows + reviews) interactively
user-invocable: true
disable-model-invocation: true
tools: Bash, Edit, Skill, WebFetch, WebSearch, Write, LSP, mcp__ide__getDiagnostics, mcp__ide__executeCode
---

# PR Quality Triage

I would like you to gather all PR feedback (workflow failures and review comments)
  and then interactively guide the user through addressing all of that PR feedback.
I will give you a checklist of Triage Steps 1 though 4
  and ask you to track your progress through them.
Some Triage Steps may also have their own checklists and steps,
  which you will be asked to track your progress through, as well.

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

This checklist specifies the top-level Triage Steps for the PR quality triage process.
Copy this checklist and track your progress through it:

```
PR Quality Triage Progress:
[ ] Triage Step 1: Check Branch State and PR Sync Status
[ ] Triage Step 2: Gather Complete PR Feedback
[ ] Triage Step 3: Address Issues Interactively
[ ] Triage Step 4: Push Changes to Remote, Maybe
```

TODO: Move example flow to its own doc and link here, as otherwise it risks confusing the main flow

## Triage Step 1: Check Branch State and PR Sync Status

See [Triage Step 1: Check Branch State and PR Sync Status](steps/triage_step_1_check_status.md) and follow its instructions.

## Triage Step 2: Gather Complete PR Feedback

See [Triage Step 2: Gather Complete PR Feedback](steps/triage_step_2_gather_feedback.md) and follow its instructions.

## Triage Step 3: Address Issues Interactively

See [Triage Step 3: Address Issues Interactively](steps/triage_step_3_address_issues.md) and follow its instructions.

## Triage Step 4: Push Changes to Remote, Maybe

See [Triage Step 4: Push Changes to Remote, Maybe](steps/triage_step_4_push_changes.md) and follow its instructions.

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
