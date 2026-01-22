---
name: addressing-feedback-interactively
description: Guide user through resolving build failures and code review feedback interactively, as parsed by the getting-feedback-local or getting-feedback-remote skills. Use when addressing build failures (local or CI), test failures, type errors, linting errors, or review comments from PRs.
allowed-tools: Read, Edit, Write, Bash, Task
---

# Addressing Feedback Interactively

## Overview

Unified workflow for guiding users through resolving feedback issues one at a time, with user control over commit strategy.

**Core principle:** Present all issues in priority order, work through them interactively, and commit based on user's strategy choice.

What it does:
1. Ask user to choose commit strategy (incremental/accumulated/manual).
2. Present unified summary of all issues with priority levels.
3. Work through each issue in priority order.
  - Handle commits based on chosen strategy.
  - Verify fixes after each change.
4. Complete workflow based on strategy.

Output: All feedback addressed, commits created based on user's strategy choice.

## When to Use

Use when you have parsed feedback (build failures + review issues) and need to:
- Guide user through resolving issues one by one.
- Let user control when/how commits are created.
- Maintain consistent workflow across local and remote contexts.
- Verify fixes after each change.

When NOT to use:
- No feedback to address (all clear).
- Feedback not yet parsed (use parsing skills first).
- User wants to address issues themselves without guidance.

## Input Format

This skill expects TOON-formatted input with parsed feedback:

```toon
source: local  # or "remote"
review_timestamp: 2026-01-04T16:00:00Z

build_results:
  status: fail_related  # or "all_passed", "fail_unrelated"

  failures[N]:  # Optional - only if build failures exist
    type: test  # or "lint", "build", "type_check"
    location: path/to/file.ts:42
    related_to_changes: true
    reasoning: |
      Explanation of why this failure is related to changes
    messages[M]:
      |
        Error message line 1
      |
        Error message line 2

review:
  status: success  # or "fail", "unavailable"
  source: claude_analysis  # or "tool_output", etc.

  issues[N]:  # Optional - only if review issues exist
    severity: critical  # or "warning", "suggestion"
    code_references[M]:
      file: path/to/file.ts
      line: 42
      # OR
      line_range: 15-20
    description: |
      Detailed description of the issue

summary:
  total_build_failures: 1
  total_review_issues: 2
  critical_review_issues: 1
  overall_status: needs_attention
```

## Workflow

### Step 1: Choose Commit Strategy

Ask user once at the beginning:
```markdown
How would you like to commit fixes?

**1. Incremental**: Commit after each fix.
  - Each fix gets its own commit.
  - Easy to revert individual changes.
  - Clean git history showing progression.
  - Best when working on PR with CI feedback.
**2. Accumulated**: Fix all issues, commit once at end.
  - All fixes in single commit.
  - Cleaner final history.
  - Good for local development before creating PR.
  - Best when addressing pre-commit feedback.
**3. Manual**: Don't auto-commit, I'll commit manually.
  - You control all commits.
  - Fixes are implemented but not committed.
  - Maximum flexibility.
  - Best when you want to review changes first.

**Store choice for use in Steps 3 and 4.**

### Step 2: Present Feedback Summary

First, review all feedback and identify any aligned issues (see "Alignment Detection" section below). Group aligned issues together - those groupings will be noted in the summary and then will be presented as a single combined issue, going forwards. Priority of the combined issue is the highest priority of any individual issue in the group.

A note on terminology: from here on out, we refer to individual items that need addressing as "issues", whether they are build/test failures, review feedback items regardless of severity and including suggestions, or aligned sets of items.

#### Unified Presentation Format

Then, present a unified summary of all issues to your user.

```markdown
**Build and Review Feedback Summary**

**Build Results:** Pass/Fail ({N} failures, {M} related)
**Review Results:** Merge/Needs Work ({N} recommendations): {concise 1-2 sentence summary of review results, focused on their overall recommendation and tone}

**{N} Total Items To Consider Addressing**
- Priority 1: {count} Build Failures and Critical Issues
- Priority 2: {count} Warnings
- Priority 3: {count} Suggestions

**Notes**
- {N} pre-existing build failures unrelated to your changes.
<!-- If aligned issues were found, include this next bullet/section.
     Note: this is a sample format; fill in actual aligned issue sets you found from the input. -->
- The following issues are likely aligned with each other and will be presented together:
  - [Priority 1] [Test Failure and Warning Review] src/api.ts:42 — Incorrect handling of null user object
    - [Priority 1] [Test Failure] tests/api.test.ts:73 — TypeError: Cannot read property 'id' of null
    - [Priority 2] [Warning Review] src/api.ts:42 — Null pointer risk
<!-- End aligned issues bullet/section. -->

**Issue List**
<!-- Note: this is a sample format; fill in actual issues from the input. -->
1. [Priority 1] [Test Failure and Warning Review] src/api.ts:42 — Incorrect handling of null user object
2. [Priority 2] [Warning Review] src/api.ts:89 — Missing error handling
3. [Priority 3] [Suggestion] src/utils.ts:15-20 — Consider refactoring

Let's work through these in order.
```

Use the following logic to assign priorities for the issues presented in the template above:
- Priority 1: Your user will likely want to fix these immediately.
  - Build failures related to changes (`related_to_changes: true`).
  - Review issues with `severity: critical`.
- Priority 2: Your user will probably want to fix these soon, also.
  - Review issues with `severity: warning`.
- Priority 3: Your user may want to fix these.
  - Review issues with `severity: suggestion`.
- Not presented (noted separately):
  - Build failures unrelated to changes (`related_to_changes: false`).
    - Don't include in issue list.
    - Don't require fixing as part of this workflow.

### Step 3: Interactive Resolution Loop

For each issue in priority order, first mention to your user:

```markdown
Next, we'll triage and consider addressing Issue {N} of {Total}: {issue brief description}...
```

Then, after displaying that to the user, you should proceed to address each issue interactively. The following steps outline the workflow you should follow in order to address the issues:
- Loop over each issue in priority order:
  - **Step 3.1: Investigate Root Cause** (gather context)
  - **Step 3.2: Present Issue Details** (show user the issue)
  - **Step 3.3: Propose Fix** (suggest solution)
  - **Step 3.4: Implement Fix** (make changes)
  - **Step 3.5: Verify Fix** (run CI)
  - **Step 3.6: Commit Decision** (based on strategy)
  - Return to Step 3.1 for next issue.

Each step is described in detail in the following sections. Be sure to track your progress through the issues, and return to Step 3.1 for each new issue until all are addressed.

#### Step 3.1: Investigate Root Cause

First, gather context for the issue:
- Use Read tool to read the file(s) referenced in the issue.
- Read surrounding code to understand how it's used.
- Identify one or more options for how to address the issue.

This context will inform the next steps.

#### Step 3.2: Present Issue Details

Then we will present the issue details to your user, based on issue type...

For build failures:
```markdown
**Issue {N}:** [{issue type, e.g. "Test Failure", "Test Failure", "Lint Issue", etc.}] {location}

**Related to your changes:** Yes
**Reasoning:** {reasoning}

**Description**
{description of the build failure, including error messages}

**Investigation Notes**
{summary of relevant code context you gathered in Step 3.1}
```

For review issues and suggestions:
```markdown
**Issue {N}:** [{issue type, e.g. "Critical Review"}] {code_references} — {brief title of issue}

**Description**
{description of the review issue, including any relevant details}

**Investigation Notes**
{summary of relevant code context you gathered in Step 3.1}
```

For aligned issues:
```markdown
**Issue {N}:** [{issue type, e.g. "Test Failure and Critical Review"}] {code_references} — {brief title of issue}

**Build Failure**
{description of each build failure included in the aligned issue, if any, including error messages}

**Review Feedback**
{description of each review issue included in the aligned issue, if any, including any relevant details}

**Investigation Notes**
{summary of relevant code context you gathered in Step 3.1}

These appear to be related to the same underlying issue.
```

#### Step 3.3: Propose Fix

Next, propose one or more approaches to address the issue to your user:
- Explain what needs to change.
- Show proposed fix approach.
- Get user approval before implementing.

#### Step 3.4: Implement Fix

Once your user approves, implement the fix:
- Make the necessary code changes.
- Edit or write files as needed.

#### Step 3.5: Verify Fix

If a fix was implemented, verify it...

Run verification in subagent:
```markdown
Use Task tool with subagent_type='quality-data-extractor':

"Run local CI to verify current state.
Use getting-build-results-local skill to run CI commands.
Use parsing-build-results skill to parse output.

Changed files for relatedness analysis:
{list all files modified in this session}

Return structured TOON with failures and relatedness determination."
```

Notes:
- Ensure all modified files in this session are listed for relatedness analysis.
- The getting-build-results-local skill runs local CI commands for the entire project, not only on the modified files, and captures output. We run CI for the entire project (not just modified files) to catch unexpected interactions between fixes. This takes a bit longer but prevents surprises.

Triage verification results:
- If status is `all_passed`:
  - ✅ Fix verified successfully, move to Step 3.6 (Commit Decision).

- If status is `fail_related`:
  - ⚠️ Failures detected in files you modified.
  - **Compare to original issue:** Review the verification failures and compare to the original issue you were fixing:
    - **Same location and error as original?** → Fix didn't work or didn't fully resolve the issue.
      - Loop back to Step 3.1 (Investigate Root Cause) to try a different approach.
      - Explain to user that the previous approach didn't resolve the issue.
      - Propose and implement an alternative solution.
      - Re-verify by repeating all sub-steps of Step 3.5.
    - **Different location or different error?** → Fix likely caused a side effect.
      - Loop back to Step 3.1 treating this as a combined problem: fix the original issue WITHOUT causing the new failure.
      - Investigate why the fix caused this side effect.
      - Propose an alternative approach that avoids the side effect.
      - Re-verify by repeating all sub-steps of Step 3.5.
    - **Note:** Some build failures are intermittent. If the new failure seems unrelated to your changes (different subsystem, timing-related, etc.), it may be coincidental. Use judgment.

- If status is `fail_unrelated`:
  - ⚠️ Pre-existing failures in files you haven't modified.
  - Note in summary but continue to Step 3.6 (your fix is still valid).

#### Step 3.6: Commit Decision

Based on chosen commit strategy from Step 1...

Incremental strategy:
- Create commit immediately for this fix.
- Use descriptive message: "Fix {issue type}: {brief description}".
- Append Claude Code attribution.
- Continue to next issue.

Accumulated strategy:
- Don't commit yet.
- Track that fix is complete.
- Continue to next issue.

Manual strategy:
- Don't commit
- Continue to next issue

**After handling commit, return to step 3.1 for next issue.**

### Step 4: Final Completion

Once all issues have been addressed, finalize based on commit strategy...

Accumulated strategy:
```bash
# Stage all fixes
git add {all modified files}

# Create single commit
git commit -m "$(cat <<'EOF'
Address feedback: {summary of all fixes}

- Fix {issue 1, brief title only}
- Fix {issue 2, brief title only}
- Fix {issue 3, brief title only}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

Incremental strategy:
- All commits already created
- Just confirm completion: "All {N} issues addressed with {N} commits."

Manual strategy:
```
All {N} issues have been fixed.

**Changed Files**
- {file1}
- {file2}

The changes are ready for you to commit when you're ready.
```

## Alignment Detection

When build failure and review issue reference the same code location, present them as aligned issues...

Issues are considered aligned if any of the following are true:
- They reference the same line in the same file AND involve the same underlying problem.
- They reference lines or line ranges in the same file(s) that overlap AND they involve the same underlying problem.
- They share the same root cause.
  - Determining this may require a brief investigation, looking at code context, and reasoning about the issues.
  - However, this should be kept lightweight to avoid excessive overhead.
  - A deeper root cause analysis will be done later, in Step 3.1, and we can always change our mind then as to whether issues are truly aligned, if needed.

Benefits:
- User understands the connection.
- Single fix addresses both issues.
- Avoids duplicate work.

## Examples (Decision Flow Only)

**IMPORTANT:** These examples illustrate decision logic and state transitions.
They are NOT conversation transcripts - use the templates in the workflow sections above for actual communication with users.

**Available examples:**

1. **TOON Input to Presentation Format** - [examples/toon-input-to-presentation.md](examples/toon-input-to-presentation.md)
   - Shows how to transform TOON feedback into Step 2 presentation summary.
   - Demonstrates alignment detection and priority assignment logic.
   - Illustrates handling of unrelated failures.

2. **Incremental Strategy with Alignment** - [examples/incremental-strategy-with-alignment.md](examples/incremental-strategy-with-alignment.md)
   - Shows alignment detection grouping related items.
   - Demonstrates commit-after-each-fix workflow.
   - Illustrates one fix resolving multiple items.

3. **Accumulated Strategy with Priority Ordering** - [examples/accumulated-strategy-with-priorities.md](examples/accumulated-strategy-with-priorities.md)
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

This skill is typically invoked after getting feedback locally or remotely, via the quality-triage or quality-triage-pr commands:
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
