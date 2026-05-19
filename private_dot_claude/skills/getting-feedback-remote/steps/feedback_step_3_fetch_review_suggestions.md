## Feedback Step 3: Fetch and Parse Reviews

We need to retrieve and parse out any suggestions that can be found
  from the available reviews for the latest commit.
We will use the process specified below to
  find and retrieve all such reviews,
  analyze the reviews to extract structured suggestion information,
  and then to pass that as TOON output to later Feedback Steps.

This checklist specifies the Fetch Review Suggestions steps.
Copy this checklist and track your progress through it:

```
Fetch Review Suggestions Progress:
[ ] Fetch Review Suggestions Step 1: Find Relevant Reviews
[ ] Fetch Review Suggestions Step 2: Retrieve and Analyze Each Review for Suggestions
[ ] Fetch Review Suggestions Step 3: Display Reviews Summary
[ ] Fetch Review Suggestions Step 4: Extract De-Duplicated Suggestions
```

## Fetch Review Suggestions Step 1: Find Relevant Reviews

Run the /getting-reviews-remote skill, as follows:

- **Tool**:
  Use the Skill tool to run the /getting-reviews-remote skill in the current context.
- **Prompt**:
  Run the /getting-reviews-remote skill.
    for the PR detailed in this TOON data,
    (which was collected, earlier, by the getting-branch-state skill):
  ```toon
  <PASTE THE TOON DATA FROM TRIAGE STEP 1 HERE>
  ```
  Respond with the unaltered TOON output
    that the /getting-reviews-remote skill produced when run.

With the above configuration, this Skill Tool use will
  find all reviews relevant to the latest commit of the specified PR,
  returning their URLs and metadata as a TOON-formatted output at the end.

To keep track of the reviews that need processing,
  replace Step 2 of the Fetch Review Suggestions Progress checklist
  with a new entry for each review found:

**Before:**

```
...
[ ] Fetch Review Suggestions Step 2: Retrieve and Analyze Each Review for Suggestions
...
```

**After (example with 3 review URLs):**

```
...
[ ] Fetch Review Suggestions Step 2.1: Retrieve and Analyze PR Comment https://github.com/owner/repo/pull/456#issuecomment-123
[ ] Fetch Review Suggestions Step 2.2: Retrieve and Analyze PR Review https://github.com/owner/repo/pull/456#pullrequestreview-789
[ ] Fetch Review Suggestions Step 2.3: Retrieve and Analyze PR Review Thread https://github.com/owner/repo/pull/456#discussion_r123,teammate-alice,2026-02-13T15:05:00Z,7a3f9e2c1b8d4e6f0a2b5c8d9e1f3a4b6c7d8e9f
...
```

## Fetch Review Suggestions Step 2: Retrieve and Analyze Each Review for Suggestions

For each of those reviews,
  we will use the /parsing-reviews skill
  to extract and return structured suggestion information from the review content.
The /parsing-reviews skill can be run,
  in a separate parallel subagent tasks per review,
  as follows:

- **Tool**:
  Use the Task tool to run the /parsing-reviews skill in a subagent.
  - **Subagent**:
    Use the `quality-data-extractor` subagent.
- **Prompt**:
  Run the /parsing-reviews skill,
    for the PR review, comment, or thread detailed in this TOON data,
    (which was collected, earlier, by the getting-reviews-remote skill),
    and grab the structured TOON output that the skill produces.
  Pass the URL for the PR review, comment, or thread to the skill.
  Respond with unaltered TOON output that the /parsing-reviews skill produced when run.

With the above configuration, this Skill Tool use will
  return parsed details from the review and any suggestions found within it
  as structured TOON output.
This TOON output will consist of a top-level `parsed_review` key, containing:

* `review_sources`: metadata about the review sources (e.g., reviewer, date, URL).
* `overall_summary`: a textual overall summary of the review.
* `suggestions`: an array of individual suggestion entries found in that review.

## Fetch Review Suggestions Step 3: Display Reviews Summary

Once all of the reviews have been retrieved and parsed,
  display a summary of the reviews to the user,
  using the following template:

TODO: the find reviews script needs to group comments that were accidentally split and tie threads to their parent reviews, so that the display can be more coherent.

```markdown
## PR Review Summary
These reviews were found for the latest commit of this PR:
{# for each in: group PR review artifacts by reviewer and by type #}
**{count} PR {Reviews/Comments/Threads} by {Reviewer Name}. Suggestions include:**
  {# for each suggestion in those reviews #}
  - {Suggestion summary, e.g. "Change variable name for clarity"}
  {# end for #}
{# end group #}



## Fetch Review Suggestions Step 4: Extract De-Duplicated Suggestions

TODO: need to define input/output

After finding and parsing all of the reviews,
  evaluate the suggestion entries to see if any of them are largely duplicates of each other.
Those that are largely duplicates
  should be marked as such,
  combining their metadata (e.g., sources, reviewers, etc.) as appropriate.
The combination is straightforward:

1. Merge the separate `review_sources` together by appending them into a single array,
     removing any duplicates.
2. Update the `TODO` field to merge the comments, suggested action items, and other relevant information
     from each duplicate suggestion into a single coherent comment.

Return this combined TOON output to be used in later Feedback Steps.

Once the combined `suggestions` TOON output is returned,
  we're done with the Fetch Review Suggestions steps.
