# Triage Step 3: Address Issues Interactively

We now have complete PR feedback.
We will use the process specified below to interactively guide the user
  through addressing all issues found in the PR feedback.

## Process for Addressing Issues Interactively

Run the /addressing-feedback-interactively skill, as follows:

- **Tool**:
  Use the Skill tool to run the /addressing-feedback-interactively skill in the current context.
- **Prompt**:
  Run the /addressing-feedback-interactively skill.
    for the PR detailed in this TOON data,
    (which was collected, earlier, by the getting-branch-state skill):
  ```toon
  <PASTE THE TOON DATA FROM TRIAGE STEP 1 HERE>
  ```
  Follow the instructions provided by the /addressing-feedback-interactively skill.

**Critical:** We must use the `addressing-feedback-interactively` skill in the current context,
  as it has the detailed workflow and logic that are required to correctly accomplish this complex task.

With the above configuration, this Skill Tool use will
  interactively guide the user through addressing all PR feedback.
It uses a formal workflow with conversation templates to ensure clarity and correctness.

## Once All Issues Are Addressed

Once all issues are addressed (or deferred):

1. The skill will report how many commits were created.
2. ✅ We're done with this Addresing Issues step. Proceed to Triage Step 4.
