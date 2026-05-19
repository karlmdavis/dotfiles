---
name: getting-branch-state
description: Check local branch state, PR status, and sync comparison (ahead/behind/diverged). Returns branch info, base branch detection, uncommitted files, PR details, and changed files for review context.
user_invocable: false
---

# Getting Branch State

I would like you to analyze the current git branch state,
  detect its base branch (main/master or other),
  check for an associated PR,
  and compare local vs PR sync status.
In order to accomplish all of this,
  this skill has a bundled script that collects and returns
  all the relevant branch and PR state information in a single call.

Run the `scripts/check_branch_state.py` script, as follows:

1. The base directory for this skill is shown at the top: `Base directory for this skill: <PATH>`
2. Construct the absolute path to the script: `<PATH>/scripts/check_branch_state.py`
3. Run: `<absolute_path_from_step_2>`
4. Capture the TOON-formatted output from stdout and any status messages from stderr.

Examples:
- If the base directory for this skill is `/Users/cool_person/.claude/skills/getting-branch-state`,
    then run: `/Users/cool_person/.claude/skills/getting-branch-state/scripts/check_branch_state.py`.
- If the base directory for this skill is `/home/cool_person/neat_project/.claude/skills/getting-branch-state`,
    then run: `/home/cool_person/neat_project/.claude/skills/getting-branch-state/scripts/check_branch_state.py`.

The script will output TOON-formatted results to stdout, status messages to stderr.

## Interpreting getting-branch-state Results

The TOON output from the `getting-branch-state` skill
  contains three main sections: `local`, `pr`, and `comparison`.
The data should be largely self-explanatory,
  but `reference/results_details.md` contains additional details and interpretation guidance,
  if needed.

## Displaying getting-branch-state Results

If the user would like a summary of the branch state,
  they can be displayed using this template:

```markdown
**Branch State**

**PR:** {if pr.exists}[#{pr.number} — {pr.title}]({pr.url}){else}No PR found for current branch.{end if}
**PR Sync Status:** {local_vs_pr.status, with ahead/behind counts as applicable}
**Uncommitted Files:** {# uncommitted_files} file(s)
```

## getting-branch-state Completed

Make the full TOON output from the `check_branch_state.py` script available
  to downstream steps for further processing.
