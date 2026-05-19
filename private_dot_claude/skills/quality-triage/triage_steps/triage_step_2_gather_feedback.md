# Triage Step 2: Gather Complete Local Feedback

We need to gather all local feedback: build failures, test results, and local code review.
This is done in a subagent to prevent token bloat.

This checklist specifies the Gather Feedback steps.
Copy this checklist and track your progress through it:

```
Gather Feedback Progress:
[ ] Gather Feedback Step 1: Spawn Quality Data Extractor Subagent
[ ] Gather Feedback Step 2: Wait for Unified TOON Output
```

## Gather Feedback Step 1: Spawn Quality Data Extractor Subagent

Use the Task tool with the following parameters:
- `subagent_type='quality-data-extractor'`
- `description="Get complete local feedback"`

The subagent prompt should instruct it to use the `getting-feedback-local` skill, passing:
1. The file list from Step 1 (files to review).
2. The scope from Step 0 (for context).

This skill orchestrates:
1. Running local CI commands (via getting-build-results-local).
2. Running local code review (via getting-review-local).
3. Parsing and combining everything into unified TOON format.

## Gather Feedback Step 2: Wait for Unified TOON Output

Wait for the subagent to complete and return unified TOON output with complete local feedback.

**Critical:** The skill MUST run in a subagent, never in main context.
This prevents token bloat from build logs.

Once you receive the TOON output:
1. Parse it to understand the feedback structure.
2. Do NOT display the raw TOON to the user - Step 3 will present issues in user-friendly format.
3. ✅ We're done with Gather Feedback steps. Proceed to Triage Step 3.
