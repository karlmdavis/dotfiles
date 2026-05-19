# Feedback Step 1: Wait for Workflows

We need to wait (up to a timeout) for all CI workflows to complete
  and then retrieve the workflow runs' details.
We will use the process specified below to wait for the workflow runs to complete,
  return their status and URLs as a TOON-formatted output,
  ensure that the PR is ready for further feedback gathering,
  and then to pass the TOON output to Feedback Step 2.

This checklist specifies the Workflow Waiting steps.
Copy this checklist and track your progress through it:

```
Workflow Waiting Progress:
[ ] Workflow Waiting Step 1: Run awaiting-pr-workflow-results Skill
[ ] Workflow Waiting Step 2: Display Workflow Summary
[ ] Workflow Waiting Step 3: Verify Workflow Completion
```

## Workflow Waiting Step 1: Run awaiting-pr-workflow-results Skill

Run the /awaiting-pr-workflow-results skill, as follows:

- **Tool**:
  Use the Skill tool to run the /awaiting-pr-workflow-results skill in the current context.
- **Prompt**:
  Run the /awaiting-pr-workflow-results skill.
    for the PR detailed in this TOON data,
    (which was collected, earlier, by the getting-branch-state skill):
  ```toon
  <PASTE THE TOON DATA FROM TRIAGE STEP 1 HERE>
  ```
  Respond with the suggested **Workflow Results** display
    and the unaltered TOON output
    that the /getting-feedback-remote skill produced when run.

With the above configuration, this Skill Tool use will
  wait (up to a defined timeout) for all of the CI workflows
  for the specified PR to complete,
  and return their status and URLs as a TOON-formatted output at the end.

**Note**: If the awaiting-pr-workflow-results skill fails (exits with error),
  it means the PR is missing or branches are out of sync.
Report the error to the user and stop execution.

## Workflow Waiting Step 2: Display Workflow Summary

Display the **Workflow Results** summary
  that was produced by the /awaiting-pr-workflow-results skill
  to the user.

## Workflow Waiting Step 3: Verify Workflow Completion

Evaluate the `workflows.complete` field in the TOON output that was produced by Workflow Waiting Step 1:

1. If `workflows.complete` is `false`:
   At least some of the workflows failed to complete within the timeout.
   Continue to Feedback Step 2,
     passing along a timeout notice and the TOON output from Workflow Waiting Step 1.
2. If `workflows.complete` is `true`:
   All workflows have completed.
   Continue to Feedback Step 2,
     passing along the TOON output from Workflow Waiting Step 1.

Once the workflow status has been handled per the above process,
  we're done with the Workflow Waiting steps.
Proceed to Feedback Step 2.
