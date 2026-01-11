# Triage Step 1: Check Branch State and PR Sync Status

We need to ensure that the local branch is properly synced with the PR before gathering feedback. This prevents feedback from being applied to outdated or mismatched code.

This checklist specifies the Check Status steps. Copy this checklist and track your progress through it:

```
Check Status Progress:
[ ] Check Status Step 1: Run getting-branch-state Skill
[ ] Check Status Step 2: Verify PR Exists
[ ] Check Status Step 3: Check and Handle Sync Status
```

## Check Status Step 1: Run getting-branch-state Skill

Use the Skill tool with skill='getting-branch-state' to retrieve TOON-formatted data on the working copy's status. We will then manually parse and interpret the TOON output it produces.

## Check Status Step 2: Verify PR Exists

1. Extract the `pr.exists` field from the TOON output. This indicates whether a PR exists for the current branch.
  a. **If `pr.exists` is `true`**, a PR exists for the current branch → Proceed to Check Status Step 3.
  b. **If `pr.exists` is `false`**, no PR exists for the current branch → Handle as follows:
    1. Report the following error to the user: "**Error:** No PR found for current branch. Create a PR first."
    2. Exit cleanly; we cannot proceed further until the user addresses this issue.

## Check Status Step 3: Check and Handle Sync Status

1. Extract the `comparison.local_vs_pr.status` field from the TOON output. This indicates whether the local branch and PR branch are in sync.
2. Display the sync status to the user, following the **Check Status Step 3.a: Sync Status Display** below.
3. Determine the sync status:
  a. **Status is `in_sync`**: Local and PR branches match → ✅ We're done with the Check Status steps. Proceed to Triage Step 2.
  b. **Status is `ahead`, `behind`, or `diverged`**: Local and PR branches do not match → ⚠️ Follow the **Check Status Step 3.b: Out-of-Sync Handling** below.

### Check Status Step 3.a: Sync Status Display

Display the value of `comparison.local_vs_pr.status` to the user, as follows:

1. Happy path:
  a. If `in_sync`: "✅ Local and PR branches are in sync."
2. Warning paths:
  a. If `ahead`: "⚠️ Local is {ahead_count} commit(s) ahead of PR."
  b. If `behind`: "⚠️ Local is {behind_count} commit(s) behind PR."
  c. If `diverged`: "⚠️ Local and PR have diverged ({ahead_count} ahead, {behind_count} behind)."
  d. Show commit lists from `ahead_commits` and/or `behind_commits`.
  e. Explain: "PR feedback is for commit {pr.head_short}, not your local {local.head_short}."

### Check Status Step 3.b: Out-of-Sync Handling

When the working copy and PR are out of sync, present the following options using the AskUserQuestion tool:

```markdown
**Question:** "Local and PR branches are out of sync. How would you like to proceed?"

**Options:**

1. "Push Now and Re-Run" (recommended for `ahead`).
   - Description: "Push your local commits to the PR, then re-run this command to get fresh feedback."
2. "Pull First" (recommended for `behind`).
   - Description: "Pull PR commits to your local branch first, then re-run this command to get fresh feedback."
3. "Continue Anyway".
   - Description: "Get feedback for the old PR commit (won't match your local code)."
4. "Stop and Address Manually" (recommended for `diverged`).
   - Description: "Stop and handle the sync issue manually."
```

Based on user choice:

- Option 1: Push with `git push`, then exit cleanly with message to re-run command.
- Option 2: Pull with `git pull`, then exit cleanly with message to re-run command.
- Option 3: Continue to Triage Step 2 (accept mismatch). We're done with Check Status steps.
- Option 4: Exit cleanly.
