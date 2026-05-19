---
name: getting-build-issues-remote
description: Extract structured failure, warning, etc. information from the log and any other artifacts that were produced by a GitHub PR workflow.
user_invocable: false
---

# Getting Build Issues Remote

I would like you to search the logs and artifacts
  that were produced by a specified GitHub PR workflow
  for failures, warnings, or other issues
  and return the issues that were found
  as structured TOON-formatted information.

**Note**: This skill is intended to be run
  in a separate subagent context per failed workflow,
  using the Task tool.
This prevents token bloat from large log files
  and allows parallel processing of multiple failed workflows.

When run, this skill expects TOON-formatted input
  that specifies the failed workflow to analyze,
  including its name, database ID, status, conclusion, URL, and any artifacts.
If this information is not available,
  the skill cannot proceed and should report an error.

GitHub workflows are arbitrary scripts defined by the repository owner.
The skill should not make assumptions about
  what steps the workflow contains
  or what tools it uses.
Instead, it should focus on extracting
  any failures, warnings, or other issues
  that are present in the logs and artifacts.
In order to accomplish this,
  this skill documents general strategies and techniques
  for extracting issues from workflow logs and artifacts,
  without being tied to any specific workflow implementation.

This checklist specifies the top-level Finding Issues Steps for the process.
Copy this checklist and track your progress through it:

```
Finding Issues Progress:
[ ] Finding Issues Step 1: Examine Workflow Steps
[ ] Finding Issues Step 2: Search Log and Other Artifacts for Issues
```

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

## Finding Issues Step 1: Examine Workflow Steps

In this step, the skill should examine the steps of the specified GitHub PR workflow
  to help contextualize the log and artifact data.
This involves analyzing the steps for the failing workflow job's,
  including their names, actions, and any relevant metadata.

The goal is to understand what the workflow was trying to accomplish
  and what tools or commands it was using.
This context will inform the search for issues
  in the subsequent steps.

Given the `database_id` of the failed workflow from the input TOON,
  retrieve the workflow job details
  using the GitHub API's
  [Get a workflow run](https://docs.github.com/en/rest/actions/workflow-runs#get-a-workflow-run) endpoint:

```bash
gh run view <database_id> --json workflowName,workflowPath,headSha,event,jobs
```

You can use the returned `workflowPath` to determine the specific workflow file
  (e.g., `.github/workflows/ci.yml`)
  and analyze its steps if needed.
You can use the returned `jobs` field
  to get details about each job in the workflow run,
  including their `steps` and `conclusion`s.

If you need to retrieve a specific commit's workflow file version,
  you can use the `headSha` from the workflow run details:

```bash
gh api \
  repos/:owner/:repo/contents/<workflowPath> \
  -H "Accept: application/vnd.github.raw" \
  -f ref=<headSha>
```

With this information,
  you can better understand the context of the logs and artifacts
  that will be analyzed in the next step.

## Finding Issues Step 2: Search Log and Other Artifacts for Issues

In this step, the skill should search the logs and any other artifacts
  that were produced by the specified GitHub PR workflow
  for failures, warnings, or other issues.
The goal is to extract structured information
  about any problems that occurred during the workflow execution,
  which can then be returned in a TOON-formatted output.

Use the /parsing-build-results skill's techniques and strategies
  to analyze the logs and artifacts of the specified failed workflow,
  and extract any failures, warnings, or other issues
  into its TOON format.

Return the resulting TOON-formatted output, unmodified.
It should contain an array of issues found in the workflow logs and artifacts.
