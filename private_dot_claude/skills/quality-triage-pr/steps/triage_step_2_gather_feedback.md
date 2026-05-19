# Triage Step 2: Gather Complete PR Feedback

We need to gather all feedback from the PR: workflow failures, build results, and review comments.
We will use the process specified below to get a unified TOON-formatted output of all PR feedback,
  which we will pass to Triage Step 3.

## Process for Gathering Complete PR Feedback

Run the /getting-feedback-remote skill, as follows:

- **Tool**:
  Use the Task tool to run the /getting-feedback-remote skill in a subagent.
  - **Subagent**:
    Use the `quality-data-extractor` subagent.
- **Prompt**:
  Run the /getting-feedback-remote skill,
    for the PR detailed in this TOON data,
    (which was collected, earlier, by the getting-branch-state skill):
  ```toon
  <PASTE THE TOON DATA FROM TRIAGE STEP 1 HERE>
  ```
  Respond with only the unaltered unified TOON output
    that the /getting-feedback-remote skill produced when run.

**Critical:** The skill MUST run in a subagent, never in main context.
This prevents token bloat from workflow logs and review text.

With the above configuration, this subagent task will orchestrate:

1. Waiting for workflows to complete (via awaiting-pr-workflow-results)
2. Fetching build results from failed workflows (via getting-build-results-remote)
3. Fetching review comments from PR (via getting-reviews-remote)
4. Parsing and combining everything into unified TOON format

## Once the Subagent Task is Completed

Once the subagent task has completed and returned its unified TOON output,
  with the complete PR feedback:

1. Do NOT display the raw TOON to the user - Triage Step 3 will handle presenting and addressing the gathered feedback.
2. ✅ We're done with this Gather Feedback step. Proceed to Triage Step 3.
