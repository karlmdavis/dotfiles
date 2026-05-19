---
name: getting-reviews-remote
description: Find PR feedback (reviews with nested threads + other comments) from GitHub for a specific PR commit.
user_invocable: false
---

# Getting Reviews Remote

I would like you to fetch all review feedback for a specific GitHub PR and commit,
  including PR reviews with nested threads and other PR comments.
In order to accomplish all of this,
  this skill has a bundled script that handles the GraphQL queries and filtering.

Run the `scripts/find_pr_feedback.py` script, as follows:

1. The base directory for this skill is shown at the top: `Base directory for this skill: <PATH>`
2. Construct the absolute path to the script: `<PATH>/scripts/find_pr_feedback.py`
3. Run: `<absolute_path_from_step_2> <PR_NUMBER> <COMMIT_SHA>`
4. Capture the TOON-formatted output from stdout and any status messages from stderr.

Examples:
- If the base directory for this skill is `/Users/cool_person/.claude/skills/getting-reviews-remote`,
    and the PR number is `123` and the commit SHA is `a1b2c3d4`,
    then run: `/Users/cool_person/.claude/skills/getting-reviews-remote/scripts/find_pr_feedback.py 123 a1b2c3d4`.
- If the base directory for this skill is `/home/cool_person/neat_project/.claude/skills/getting-reviews-remote`,
    and the PR number is `456` and the commit SHA is `e5f6g7h8`,
    then run: `/home/cool_person/neat_project/.claude/skills/getting-reviews-remote/scripts/find_pr_feedback.py 456 e5f6g7h8`.

The script will output TOON-formatted results to stdout, status messages to stderr.

## Interpreting getting-reviews-remote Results

The TOON output from the `getting-reviews-remote` skill
  contains structured review feedback with reviews, nested threads, and other comments.
Note that not all of the comments returned by this skill will be review comments:
  some may be general PR comments that are not part of a review.
Also note that the returned comments may be for a commit _later_ than the specified commit,
  as the script fetches all comments that were posted _after_ the specified commit was pushed.
Otherwise, the data should be largely self-explanatory,
  but `reference/output_details.md` contains additional details and interpretation guidance,
  if needed.

## Displaying getting-reviews-remote Results

You should not attempt to display the returned data directly to the user,
  as it will not include the feedbacks' contents, only its metadata.

## getting-reviews-remote Completed

Make the full TOON output from the `find_pr_feedback.py` script available
  to downstream steps for further processing.
