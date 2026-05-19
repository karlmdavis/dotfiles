
# Getting Branch State: Results Details

The results produced by the `getting-branch-state` skill
  provide detailed information about the current local git branch,
  its relationship to the base branch (main/master),
  the existence and status of any associated pull request (PR),
  and a comparison of the local branch vs the PR branch.
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

### Normal Case: PR Exists

```toon
local:
  branch: feature-auth
  head: abc123def456789...
  head_short: abc123d
  timestamp: 2026-01-07T10:30:00Z
  base_branch: main
  uncommitted_files[2]:
    src/api.ts
    tests/api.test.ts

pr:
  exists: true
  number: 123
  title: Add authentication feature
  is_draft: false
  head: def456abc123789...
  head_short: def456a
  url: https://github.com/owner/repo/pull/123

comparison:
  local_vs_pr:
    status: diverged
    ahead_count: 2
    behind_count: 3
    ahead_commits[2]:
      sha: abc123d
      message: Fix null pointer (rebased)

      sha: abc123e
      message: Add tests

    behind_commits[3]:
      sha: old789a
      message: Fix null pointer (original)

      sha: old789b
      message: Add validation

      sha: old789c
      message: Update docs

  branch_vs_base:
    changed_files[5]:
      src/api.ts
      src/utils.ts
      tests/api.test.ts
      tests/utils.test.ts
      docs/README.md
```

### PR Does Not Exist

```toon
local:
  branch: feature-auth
  head: abc123d...
  head_short: abc123d
  timestamp: 2026-01-07T10:30:00Z
  base_branch: main
  uncommitted_files[0]:

pr:
  exists: false

comparison:
  local_vs_pr:
    status: no_pr
  branch_vs_base:
    changed_files[3]:
      src/api.ts
      tests/api.test.ts
      docs/README.md
```

### When on Base Branch (main/master/etc.)

```toon
local:
  branch: main
  head: xyz789...
  head_short: xyz789a
  timestamp: 2026-01-07T10:30:00Z
  base_branch: main
  uncommitted_files[2]:
    src/api.ts
    tests/api.test.ts

pr:
  exists: false

comparison:
  local_vs_pr:
    status: no_pr
  branch_vs_base:
    changed_files[2]:
      src/api.ts
      tests/api.test.ts
```

Note: When on base branch, `branch_vs_base.changed_files` = uncommitted files (staged + unstaged).

## Interpreting Results

`local_vs_pr.status` can be:

- `in_sync` - Local and PR are identical (ahead: 0, behind: 0).
- `ahead` - Local has unpushed commits (ahead > 0, behind: 0).
- `behind` - PR has commits not in local (ahead: 0, behind > 0).
- `diverged` - Both have unique commits (ahead > 0, behind > 0), usually from rebase.
- `no_pr` - No PR exists for this branch.

### Common Scenarios

#### Scenario: Local ahead of PR

```toon
comparison:
  local_vs_pr:
    status: ahead
    ahead_count: 2
```

Interpretation: You have 2 unpushed commits. Push to update PR.

#### Scenario: Local Behind PR

```toon
comparison:
  local_vs_pr:
    status: behind
    behind_count: 3
```

Interpretation: PR has 3 commits you don't have. Pull to sync.

#### Scenario: Diverged (Rebased Locally)

```toon
comparison:
  local_vs_pr:
    status: diverged
    ahead_count: 2
    behind_count: 3
```

Interpretation: You rebased locally. Need to force push.

#### Scenario: Working on Feature Branch

```toon
local:
  branch: feature-auth
  base_branch: main
comparison:
  branch_vs_base:
    changed_files[5]: [...]
```

Interpretation: Review these 5 files that differ from main.

#### Scenario: Working on Main Branch

```toon
local:
  branch: main
  base_branch: main
  uncommitted_files[2]: [...]
comparison:
  branch_vs_base:
    changed_files[2]: [...]  # same as uncommitted
```

Interpretation: Review uncommitted changes before committing to main.

## Error Handling

If not in git repository:

- Script exits with error: "Error: Not in a git repository".

If gh CLI unavailable:

- `pr.exists` = false (can't check).

If remote origin/HEAD not set and neither main nor master exists:

- Falls back to "master" as base_branch.
- May be incorrect for repos with different conventions.
