## Feedback Step 2: Fetch Build Issues

We need to retrieve and parse out any failures, warnings, or other issues that can be found
  from any workflows that failed.
We will use the process specified below to identify the failed workflows,
  retrieve their build logs,
  parse the build logs to extract structured issue information,
  and then to pass that TOON output to later Feedback Steps.

This checklist specifies the Fetch Build Issues steps.
Copy this checklist and track your progress through it:

```
Fetch Build Issues Progress:
[ ] Fetch Build Issues Step 1: Identify Failed Workflows
[ ] Fetch Build Issues Step 2: Retrieve and Parse Build Logs for Each Failed Workflow
[ ] Fetch Build Issues Step 3: Combine and Return Parsed Build Issues
```

## Fetch Build Issues Step 1: Identify Failed Workflows

From the output of the `awaiting-pr-workflow-results` skill,
  identify any workflows that failed by
  checking the `workflows.results` array for workflows
  where `status` is `completed` and `conclusion` is `failure` or `timed_out`.
The matched workflows are the failed workflows
  that we need to retrieve and parse build logs for.

To keep track of the workflows that need processing,
  replace Step 2 of the Fetch Build Issues Progress checklist
  with a new entry for each failed workflow found:

**Before:**

```
...
[ ] Fetch Build Issues Step 2: Retrieve and Parse Build Logs for Each Failed Workflow
...
```

**After (example with two failed workflows):**

```
...
[ ] Fetch Build Issues Step 2.1: Retrieve and Parse Build Logs for "Build and Test" Workflow (database_id: 101)
[ ] Fetch Build Issues Step 2.2: Retrieve and Parse Build Logs for "Deploy to Staging" Workflow (database_id: 102)
...
```

## Fetch Build Issues Step 2: Retrieve and Parse Build Logs for Each Failed Workflow

For each of those failed workflows,
  we will use the /getting-build-issues-remote skill
  to extract and return structured failure, warning, etc. information from the build logs.

The /getting-build-issues-remote skill can be run,
  in a separate parallel subagent tasks per failed workflow,
  as follows:

- **Tool**:
  Use the Task tool to run the /getting-build-issues-remote skill in a subagent.
  - **Subagent**:
    Use the `quality-data-extractor` subagent.
- **Prompt**:
  Run the /getting-build-issues-remote skill,
    for the failed workflow detailed in this TOON data,
    (which was collected, earlier, by the awaiting-pr-workflow-results skill),
    and grab the structured TOON output that it produces.
  Pass the following TOON data to the skill,
    replacing the placeholders with the actual values from the failed workflow:
  ```toon
  failed_workflow:
    name: {workflow.name}
    database_id: {workflow.database_id}
    status: {workflow.status}
    conclusion: {workflow.conclusion}
    url: "{workflow.url}"
    artifacts[{len(workflow.artifacts)}]{name,url}:
      {workflow.artifacts}
  ```
  Respond with unaltered TOON output that the /getting-build-issues-remote skill produced when run.

With the above configuration, this Skill Tool use will
  return structured failure, warning, etc. information
  extracted from the build logs of the specified failed workflow.
This TOON output will consist of a top-level `build_issues` array,
  containing the individual issues found in that workflow's build logs.
This `build_issues` array
  should be added as a child field of the `failed_workflow` object
  that was passed to the /getting-build-issues-remote skill.

## Fetch Build Issues Step 3: Combine and Return Parsed Build Issues

After retrieving and parsing the build logs for all failed workflows,
  combine the structured failure, warning, etc. information into a single TOON output object,
  containing an array of failed workflows,
  each with its associated structured failure, warning, etc. information.
The combination is straightforward:
  append each `failed_workflow` instance
  (including its now-associated `build_issues` array child field)
  as a new element added to a new top-level `failed_workflows` array.
Return this combined TOON output to be used in later Feedback Steps.

Once the combined `failed_workflows` TOON output is returned,
  we're done with the Fetch Build Issues steps.
