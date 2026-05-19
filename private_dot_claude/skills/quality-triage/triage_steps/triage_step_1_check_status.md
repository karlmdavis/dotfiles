# Triage Step 1: Check Branch State

We need to understand the current branch state to determine what code should be reviewed based on the
  scope from Step 0.

This checklist specifies the Check Status steps.
Copy this checklist and track your progress through it:

```
Check Status Progress:
[ ] Check Status Step 1: Run getting-branch-state Skill
[ ] Check Status Step 2: Extract Relevant Information Based on Scope
```

## Check Status Step 1: Run getting-branch-state Skill

Use the Skill tool with skill='getting-branch-state' to retrieve TOON-formatted data on the working
  copy's status.
We will then manually parse and interpret the TOON output it produces.

## Check Status Step 2: Extract Relevant Information Based on Scope

Parse the TOON output from Step 1 and extract information based on the scope from Triage Step 0:

**For scope: `everything`**
1. Get all tracked files: Run `git ls-files`.
2. These are all the files to review.

**For scope: `uncommitted`**
1. Extract `local.uncommitted_files[]` - these are the files to review.
2. If list is empty → Inform user: "No uncommitted changes to review".

**For scope: `branch`**
1. Extract `comparison.branch_vs_base.changed_files[]` - committed changes only.
2. Exclude uncommitted files.

**For scope: `branch-dirty`**
1. Extract `comparison.branch_vs_base.changed_files[]` - committed changes.
2. Also extract `local.uncommitted_files[]` - uncommitted changes.
3. Combine both lists (deduplicate if needed).

Once file list is extracted:
1. Display to user: "Reviewing {N} file(s) with scope '{scope}'".
2. ✅ We're done with Check Status steps. Proceed to Triage Step 2.
