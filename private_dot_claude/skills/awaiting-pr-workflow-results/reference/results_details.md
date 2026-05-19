# Awaiting PR Workflow Results: Results Details

The results produced by the `awaiting-pr-workflow-results` skill
  provide detailed information about the status and outputs of GitHub PR workflows.
They should be largely self-explanatory,
  but here are some additional details to help interpret the results.

## TOON Format Overview

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

## Example Output

### All Workflows Passed

```
local:
  branch: feature-auth
  commit: a1b2c3d
  commit_full: a1b2c3d4e5f6g7h8i9j0
  timestamp: 2026-01-12T10:30:00Z

pr:
  number: 123
  commit: a1b2c3d
  commit_full: a1b2c3d4e5f6g7h8i9j0
  url: https://github.com/user/repo/pull/123

workflows:
  complete: true
  wait_time_seconds: 342
  results[3]:
    - name: CI Tests
      database_id: 123
      status: completed
      conclusion: success
      duration_seconds: 298
      url: "https://github.com/user/repo/actions/runs/123"
      artifacts[1]{name,url}:
        test-results.xml,"https://github.com/user/repo/actions/artifacts/123/test-results.xml"
    - name: Lint
      database_id: 124
      status: completed
      conclusion: success
      duration_seconds: 45
      url: "https://github.com/user/repo/actions/runs/124"
      artifacts[0]:
    - name: Type Check
      database_id: 125
      status: completed
      conclusion: success
      duration_seconds: 67
      url: "https://github.com/user/repo/actions/runs/125"
      artifacts[0]:
```

### Timeout Waiting for Workflows

```
local:
  branch: feature-auth
  commit: a1b2c3d
  commit_full: a1b2c3d4e5f6g7h8i9j0
  timestamp: 2026-01-12T10:30:00Z

pr:
  number: 123
  commit: a1b2c3d
  commit_full: a1b2c3d4e5f6g7h8i9j0
  url: https://github.com/user/repo/pull/123

workflows:
  complete: false
  wait_time_seconds: 1200
  results[2]{name,database_id,status,conclusion,duration_seconds,url}:
    CI Tests,456,in_progress,null,1200,"https://github.com/user/repo/actions/runs/123"
    Lint,457,completed,success,45,"https://github.com/user/repo/actions/runs/124"
```

## Output Fields

| Field | Description |
|-------|-------------|
| `local.branch` | Current local branch name |
| `local.commit` | Local HEAD commit (short SHA) |
| `local.commit_full` | Local HEAD commit (full SHA) |
| `local.timestamp` | Local commit timestamp |
| `pr.number` | PR number |
| `pr.commit` | PR HEAD commit (short SHA) |
| `pr.commit_full` | PR HEAD commit (full SHA) |
| `pr.url` | PR URL |
| `workflows.complete` | Boolean indicating if all workflows finished |
| `workflows.wait_time_seconds` | Time spent waiting for workflows |
| `workflows.results[].name` | Workflow name |
| `workflows.results[].database_id` | Workflow run ID |
| `workflows.results[].status` | Workflow status (completed, in_progress, queued) |
| `workflows.results[].conclusion` | Workflow result (failure, neutral, skipped, stale, success, timed_out, in_progress, queued, requested, waiting, pending) |
| `workflows.results[].duration_seconds` | Time (completed or elapsed) |
| `workflows.results[].url` | Workflow run logs URL |
| `workflows.results[].artifacts[]` | Artifacts with {name, url} |

## Interpreting Results

Check `workflows.complete` to determine if workflows finished:

- `true` - All workflows finished (check individual results for success/failure).
- `false` - Timeout, some workflows still running.

Check `workflows.results[].conclusion` to determine individual workflow success/failure:

- `success` - Workflow passed.
- `failure` or `timed_out` - Workflow failed.
- `in_progress` or `queued` or `requested` or `waiting` or `pending` - Workflow still running or waiting.
- The other potential values indicate non-failure states
    (neutral, skipped, stale).

Always include workflow run IDs (`workflows.results[].database_id`),
  URLs (`workflows.results[].url`),
  and any artifacts (`workflows.results[].artifacts[]`) in your response.

## Error Handling

The script exits with error code 1 and prints to stderr if:

- No PR exists for the branch.
- Local and PR branches are out of sync (ahead, behind, or diverged).

These cases should be handled upstream by checking branch state before calling this skill.
