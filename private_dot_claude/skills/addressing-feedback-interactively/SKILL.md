---
name: addressing-feedback-interactively
description: Guide user through resolving build failures and code review feedback interactively, as
    parsed by the getting-feedback-local or getting-feedback-remote skills. Use when addressing build
    failures (local or CI), test failures, type errors, linting errors, or review comments from PRs.
allowed-tools: Read, Edit, Write, Bash, Task
user_invocable: false
---

I would like you to guide the user through resolving all build failures and code review feedback
  interactively.
I will give you a checklist of Resolution Steps 1 through 4 and ask you to track your progress
  through them.
Some Resolution Steps will have their own checklists and substeps, which you will be asked to
  track your progress through, as well.

Many steps will produce and/or consume TOON-formatted data, which is a structured data format
  suited for use by agents.
TOON is similar to JSON and YAML but uses 2-space indents and arrays show length and fields.
The input to this skill will be TOON-formatted feedback from getting-feedback-local or
  getting-feedback-remote skills.

This checklist specifies the top-level Resolution Steps for the interactive feedback resolution
  process.
Copy this checklist and track your progress through it:

```
Feedback Resolution Progress:
[ ] Resolution Step 1: Choose Commit Strategy
[ ] Resolution Step 2: Present Feedback Summary
[ ] Resolution Step 3: Interactive Resolution Loop
[ ] Resolution Step 4: Final Completion
```

## Resolution Step 1: Choose Commit Strategy

See [Resolution Step 1: Choose Commit Strategy](resolution_steps/step_1_choose_commit_strategy.md)
  and follow its instructions.

## Resolution Step 2: Present Feedback Summary

See [Resolution Step 2: Present Feedback Summary](resolution_steps/step_2_present_summary.md) and
  follow its instructions.

## Resolution Step 3: Interactive Resolution Loop

See [Resolution Step 3: Interactive Resolution Loop](resolution_steps/step_3_interactive_resolution.md)
  and follow its instructions.

## Resolution Step 4: Final Completion

See [Resolution Step 4: Final Completion](resolution_steps/step_4_final_completion.md) and follow
  its instructions.

## Input Format

This skill expects TOON-formatted input with parsed feedback.
See [Input Format Documentation](supporting/input_format.md) for complete specification.

## Supporting Documentation

- [Alignment Detection](supporting/alignment_detection.md) - How to detect and group related issues
- [Verification Triage](supporting/verification_triage.md) - How to handle verification results

## Examples

**IMPORTANT:** These examples illustrate decision logic and state transitions.
They are NOT conversation transcripts - use the templates in the resolution step files for actual
  communication with users.

**Available examples:**

1. **TOON Input to Presentation Format** -
   [examples/toon-input-to-presentation.md](examples/toon-input-to-presentation.md)
   - Shows how to transform TOON feedback into Step 2 presentation summary.
   - Demonstrates alignment detection and priority assignment logic.
   - Illustrates handling of unrelated failures.

2. **Incremental Strategy with Alignment** -
   [examples/incremental-strategy-with-alignment.md](examples/incremental-strategy-with-alignment.md)
   - Shows alignment detection grouping related items.
   - Demonstrates commit-after-each-fix workflow.
   - Illustrates one fix resolving multiple items.

3. **Accumulated Strategy with Priority Ordering** -
   [examples/accumulated-strategy-with-priorities.md](examples/accumulated-strategy-with-priorities.md)
   - Shows all three priority levels in action.
   - Demonstrates unrelated failure handling (noted but not addressed).
   - Shows suggestion deferral and single accumulated commit.

4. **Verification Triage** - [examples/verification-triage.md](examples/verification-triage.md)
   - Shows three different verification outcomes (all_passed, fail_related, fail_unrelated).
   - Illustrates relatedness analysis based on modified files.
   - Demonstrates different actions for each outcome.

## Common Mistakes

Not tracking changed files:
- Problem: Can't determine if new failures are related.
- Fix: Maintain list of all files modified in session.

Committing before verification:
- Problem: Commit might introduce new failures.
- Fix: Always verify before commit decision.

Skipping suggestions without asking:
- Problem: User misses optional improvements.
- Fix: Always ask user for suggestions (address/defer/skip).

Not presenting aligned issues together:
- Problem: User fixes same issue twice.
- Fix: Detect alignment, present as single issue.

Not explaining commit strategies:
- Problem: User picks wrong strategy for context.
- Fix: Show recommendations (incremental for PRs, accumulated for local).

## Error Handling

If verification fails repeatedly, after 3 failed verification attempts on same fix, ask your user:
- Try different approach.
- Skip verification for this fix.
- Abort and investigate manually.

If user wants to change commit strategy mid-workflow:
- Allow strategy change.
- Adjust remaining workflow accordingly.
- Don't undo commits already created.

If fix introduces new critical issues:
- Stop immediately.
- Investigate new issue.
- Fix before proceeding with original issues.

## Usage Pattern

This skill is typically invoked after getting feedback locally or remotely, via the quality-triage
  or quality-triage-pr skills:
```markdown
Use Skill tool with skill='addressing-feedback-interactively':

Pass the complete TOON feedback from getting-feedback-local or getting-feedback-remote.

The skill will handle all user interaction for resolving issues.
```

Skill expectations:
- Input is well-formed TOON with parsed feedback.
- User is available for interactive decisions.
- Local CI commands are available (for verification).
- Git operations are available (for commits).

## Benefits

Consistency:
- Same workflow for local and remote.
- Same issue presentation format.
- Same priority logic.

User Control:
- Choose commit strategy upfront.
- Decide on each suggestion.
- Full transparency.

Verification:
- After each fix.
- Catches regressions early.
- Distinguishes new vs pre-existing failures.

Efficiency:
- Priority-based ordering.
- Aligned issues presented together.
- Subagent verification (low token cost).
