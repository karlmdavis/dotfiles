# Triage Step 0: Parse and Validate Scope Argument

The quality-triage command accepts a scope argument that determines what code to review.
We need to parse and validate this argument before proceeding.

This checklist specifies the Parse Scope steps.
Copy this checklist and track your progress through it:

```
Parse Scope Progress:
[ ] Parse Scope Step 1: Extract Scope Argument
[ ] Parse Scope Step 2: Validate Scope Value
[ ] Parse Scope Step 3: Determine Files to Review
```

## Parse Scope Step 1: Extract Scope Argument

The scope argument is provided by the user when they invoke the skill.
Extract it from the command invocation.

Expected format: `/quality-triage <scope>`

Where `<scope>` is one of: `everything`, `uncommitted`, `branch`, `branch-dirty`

If no argument is provided, default to `branch-dirty` (most common use case).

## Parse Scope Step 2: Validate Scope Value

Check if the extracted scope is one of the valid options:
1. If scope is `everything`, `uncommitted`, `branch`, or `branch-dirty` → ✅ Valid, proceed to
    Parse Scope Step 3.
2. If scope is anything else → ❌ Invalid.

**For invalid scope:**
1. Display error: "**Error:** Invalid scope '{scope}'.
    Valid options: everything, uncommitted, branch, branch-dirty".
2. Exit cleanly; we cannot proceed until user provides valid scope.

## Parse Scope Step 3: Determine Files to Review

Based on the validated scope value, determine which files will be reviewed:

**Scope: `everything`**
- Review all files in the project.
- This is comprehensive but may include many files.

**Scope: `uncommitted`**
- Review only uncommitted changes (staged + unstaged).
- Quick local feedback before committing.

**Scope: `branch`**
- Review all committed changes in current branch vs base branch.
- Excludes uncommitted changes.

**Scope: `branch-dirty`**
- Review all changes: committed (branch vs base) + uncommitted (staged + unstaged).
- Most comprehensive for current work.

Once scope is validated and understood:
1. Store the scope value for use in later steps.
2. ✅ We're done with Parse Scope steps. Proceed to Triage Step 1.
