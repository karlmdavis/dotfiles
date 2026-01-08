---
name: awaiting-pr-workflow-results
description: Check GitHub PR workflow status, verify unpushed commits, and wait for workflows to complete (up to 20min). Use when user asks "are tests passing?", "is CI done?", "wait for workflows", or needs to verify workflow status after pushing commits.
---

# Awaiting PR Workflow Results

Checks GitHub PR workflows while correctly handling unpushed commits, commit correlation, and workflow timing. Uses the `getting-branch-state` skill to verify local/PR state, then waits for workflows to complete.

## When to Use

- User asks "are tests passing?", "is CI done?", "wait for CI", or similar.
- Need to verify workflow status after pushing commits.
- Want to wait for workflows to complete before proceeding.

## Usage

```
Task tool with subagent_type='general-purpose':

"Run scripts/check_pr_workflows.py and return the complete output."
```

The script outputs TOON format to stdout, status messages to stderr.

## Example Output

```
status: success

local:
  branch: feature-auth
  commit: a1b2c3d
  unpushed_count: 0

pr:
  number: 123
  url: https://github.com/user/repo/pull/123

workflows:
  complete: true
  wait_time_seconds: 342
  results[3]{name,status,conclusion,duration_seconds,url}:
    CI Tests,completed,success,298,https://github.com/user/repo/actions/runs/123
    Lint,completed,success,45,https://github.com/user/repo/actions/runs/124
    Type Check,completed,success,67,https://github.com/user/repo/actions/runs/125

recommendation: all_passed
message: All 3 workflow(s) passed for commit a1b2c3d
```

## Output Fields

| Field | Description |
|-------|-------------|
| `status` | success, warning, failure, timeout, no_pr |
| `recommendation` | Action to take (see table below) |
| `message` | Human-readable summary |
| `local.unpushed_count` | Number of unpushed commits |
| `local.unpushed_commits[]` | Array of {sha, message} |
| `pr.url` | PR URL |
| `workflows.results[].url` | Workflow run logs URL |
| `workflows.results[].artifacts[]` | Artifacts with {name, url} |
| `workflows.results[].duration_seconds` | Time (completed or elapsed) |

## Interpreting Recommendations

| recommendation | What to do |
|----------------|------------|
| `create_pr` | Ask user if they want to create a PR |
| `push_required` | Ask user if they want to push unpushed commits |
| `all_passed` | Report success with workflow details and URLs |
| `fix_failures` | Report failures with log URLs and artifacts |
| `wait_longer_or_check_logs` | Report timeout, ask user how to proceed |

Always include workflow URLs (`workflows.results[].url`) and any artifacts in your response, regardless of the recommendation.
