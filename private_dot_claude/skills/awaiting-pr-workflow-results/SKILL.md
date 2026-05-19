---
name: awaiting-pr-workflow-results
description: Check GitHub PR workflow status, verify unpushed commits, and wait for workflows to complete (up to 20min). Use when user asks "are tests passing?", "is CI done?", "wait for workflows", or needs to verify workflow status after pushing commits.
user_invocable: false
tools: Bash, WebFetch
---

# Awaiting PR Workflow Results

I would like you to wait for all GitHub PR workflows to complete (up to a timeout),
  and return the workflow status and URLs as a TOON-formatted output.
In order to accomplish all of this,
  this skill has a bundled script that handles the workflow monitoring and status retrieval.

Run the `scripts/check_pr_workflows.py` script, as follows:

1. The base directory for this skill is shown at the top: `Base directory for this skill: <PATH>`
2. Construct the absolute path to the script: `<PATH>/scripts/check_pr_workflows.py`
3. Run: `<absolute_path_from_step_2>`
4. Capture the TOON-formatted output from stdout and any status messages from stderr.

Examples:
- If the base directory for this skill is `/Users/cool_person/.claude/skills/awaiting-pr-workflow-results`,
    then run: `/Users/cool_person/.claude/skills/awaiting-pr-workflow-results/scripts/check_pr_workflows.py`.
- If the base directory for this skill is `/home/cool_person/neat_project/.claude/skills/awaiting-pr-workflow-results`,
    then run: `/home/cool_person/neat_project/.claude/skills/awaiting-pr-workflow-results/scripts/check_pr_workflows.py`.

The script will output TOON-formatted results to stdout, status messages to stderr.

## Interpreting awaiting-pr-workflow-results Results

The TOON output from the `awaiting-pr-workflow-results` skill
  contains information about the status and outputs of GitHub PR workflows.
The data should be largely self-explanatory,
  but `reference/results_details.md` contains additional details and interpretation guidance,
  if needed.

## Displaying awaiting-pr-workflow-results Results

If the user would like a summary of the workflow results,
  they can be displayed using this template:

```markdown
**Workflow Results**

**Workflows By Status:** {# completed} completed, {# in_progress} in-progress, {# queued} queued
**Completed Workflows:**
{for each workflow in workflows.results where status == "completed"}
- {name}: {conclusion} ({duration_seconds} seconds) — [View Workflow]({url})
  {for each artifact in workflow.artifacts}
  - Artifact: [{artifact.name}]({artifact.url})
  {end for}
{end for}
```

## awaiting-pr-workflow-results Completed

Make the full TOON output from the `check_pr_workflows.py` script available
  to downstream steps for further processing.
