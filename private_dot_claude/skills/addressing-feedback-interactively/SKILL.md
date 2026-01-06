---
name: addressing-feedback-interactively
description: Guide user through resolving feedback issues with commit strategy choice and priority-based workflow
---

# Addressing Feedback Interactively

## Overview

Unified workflow for guiding users through resolving feedback issues one at a time, with user control over commit strategy.

**Core principle:** Present all issues in priority order, work through them interactively, and commit based on user preference.

**What it does:**
1. Ask user to choose commit strategy (incremental/accumulated/manual)
2. Present unified summary of all issues with priority levels
3. Work through each issue in priority order
4. Handle commits based on chosen strategy
5. Verify fixes after each change
6. Complete workflow based on strategy

**Output:** All feedback addressed, commits created per user preference

## When to Use

Use when you have parsed feedback (build failures + review issues) and need to:
- Guide user through resolving issues one by one
- Let user control when/how commits are created
- Maintain consistent workflow across local and remote contexts
- Verify fixes after each change

**When NOT to use:**
- No feedback to address (all clear)
- Feedback not yet parsed (use parsing skills first)
- User wants to address issues themselves without guidance

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

**Ask user once at the beginning:**

How would you like to commit fixes?

**1. Incremental** - Commit after each fix (recommended for PRs)
  - Each fix gets its own commit
  - Easy to revert individual changes
  - Clean git history showing progression
  - Best when working on PR with CI feedback

**2. Accumulated** - Fix all issues, commit once at end (recommended for local)
  - All fixes in single commit
  - Cleaner final history
  - Good for local development before creating PR
  - Best when addressing pre-commit feedback

**3. Manual** - Don't auto-commit, I'll commit manually
  - You control all commits
  - Fixes are implemented but not committed
  - Maximum flexibility
  - Best when you want to review changes first

**Store choice for use in Steps 3 and 4.**

### Step 2: Present Issues Summary

**Unified presentation format:**

```
Found {N} issues across build and review:

Priority 1: Critical Issues and Build Failures (MUST FIX)
{count} issues

Priority 2: Warnings (SHOULD FIX)
{count} issues

Priority 3: Suggestions (OPTIONAL - discuss with user)
{count} issues

Issue List:
1. [Priority 1] [Test Failure] tests/api.test.ts:42 - TypeError: Cannot read property 'id' of null
2. [Priority 1] [Critical Review] src/api.ts:42 - Null pointer risk
3. [Priority 2] [Warning Review] src/api.ts:89 - Missing error handling
4. [Priority 3] [Suggestion] src/utils.ts:15-20 - Consider refactoring

Let's work through these in order.
```

**Priority assignment logic:**

**Priority 1 (MUST FIX):**
- Build failures related to changes (`related_to_changes: true`)
- Review issues with `severity: critical`

**Priority 2 (SHOULD FIX):**
- Review issues with `severity: warning`

**Priority 3 (OPTIONAL):**
- Review issues with `severity: suggestion`

**Not presented (noted separately):**
- Build failures unrelated to changes (`related_to_changes: false`)
  - Display count: "Note: {N} pre-existing build failures unrelated to your changes"
  - Don't include in issue list
  - Don't require fixing

### Step 3: Interactive Resolution Loop

**For each issue in priority order:**

#### 3.1. Present Issue Details

**For build failures:**
```
Issue {N}: [Test Failure] {location}

Related to your changes: Yes
Reasoning: {reasoning}

Error messages:
{messages joined}
```

**For review issues:**
```
Issue {N}: [Critical Review] {code_references}

{description}
```

**For issues that align (same location):**
```
Issue {N}: [Test Failure + Critical Review] {location}

Build failure:
{build failure details}

Review feedback:
{review description}

These appear to be related to the same underlying issue.
```

#### 3.2. Investigate Root Cause

- Read relevant code files
- Understand context around the issue
- Identify what needs to change

#### 3.3. Handle Suggestions (Priority 3 only)

**For suggestions, ask user:**

```
This is a suggestion, not a critical issue.

Would you like to:
1. Address now
2. Defer (create follow-up issue/note)
3. Skip

What would you like to do?
```

**Based on user choice:**
- **Address now:** Continue to step 3.4
- **Defer:** Create note/issue, mark as handled, move to next issue
- **Skip:** Mark as skipped, move to next issue

#### 3.4. Propose Fix

- Explain what needs to change
- Show proposed fix approach
- Get user approval before implementing

#### 3.5. Implement Fix

- Make the necessary code changes
- Edit or write files as needed

#### 3.6. Verify Fix

**Run verification in subagent:**

```markdown
Use Task tool with subagent_type='general-purpose':

"Run local CI to verify current state.
Use getting-build-results-local skill to run CI commands.
Use parsing-build-results skill to parse output.

Changed files for relatedness analysis:
{list all files modified in this session}

Return structured TOON with failures and relatedness determination."
```

**Triage verification results:**

**If status is `all_passed`:**
- ✅ Fix verified, move to next step

**If status is `fail_related` (new failures in files you just modified):**
- 🔴 Fix introduced new issues
- Investigate and fix before proceeding
- Re-verify after fixing

**If status is `fail_unrelated`:**
- ⚠️ Pre-existing failures, not caused by your fix
- Note in summary
- Continue with commit decision (fix is still good)

#### 3.7. Commit Decision (based on strategy)

**Incremental strategy:**
- Create commit immediately for this fix
- Use descriptive message: "Fix {issue type}: {brief description}"
- Append Claude Code attribution
- Continue to next issue

**Accumulated strategy:**
- Don't commit yet
- Track that fix is complete
- Continue to next issue

**Manual strategy:**
- Don't commit
- Continue to next issue

**After handling commit, return to step 3.1 for next issue.**

### Step 4: Final Completion

**Accumulated strategy:**
```bash
# Stage all fixes
git add {all modified files}

# Create single commit
git commit -m "$(cat <<'EOF'
Address feedback: {summary of all fixes}

- Fix {issue 1}
- Fix {issue 2}
- Fix {issue 3}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

**Incremental strategy:**
- All commits already created
- Just confirm completion: "All {N} issues addressed with {N} commits."

**Manual strategy:**
```
All {N} issues have been fixed.

Changed files:
- {file1}
- {file2}

The changes are ready for you to commit when you're ready.
```

**Final verification (all strategies):**

Run one final verification to confirm overall status:

```markdown
Use Task tool with subagent_type='general-purpose':

"Run local CI to verify final state.
Use getting-build-results-local skill.
Return status: all_passed | fail_related | fail_unrelated"
```

**Report final status:**

**All passed:**
```
✅ All issues resolved
✅ All tests passing
✅ Ready to {proceed based on context}
```

**Some failures unrelated:**
```
✅ All addressed issues resolved
✅ Your changes verified
⚠️ Note: {N} pre-existing failures unrelated to your changes
✅ Ready to {proceed based on context}
```

**New related failures:**
```
🔴 New failures detected in modified files
These need to be addressed before proceeding.

{details}
```

## Alignment Detection

When build failure and review issue reference the same code location, present them as aligned issue:

**Detection logic:**
```
build_failure.location == review_issue.code_reference (file:line match)
OR
build_failure.location is within review_issue.code_reference (line_range match)
```

**Presentation:**
```
Issue {N}: [Test Failure + Critical Review] src/api.ts:42

Build failure:
TypeError: Cannot read property 'id' of null

Review feedback:
Null pointer risk - user object may be null

These appear to be related to the same underlying issue.
```

**Benefits:**
- User understands the connection
- Single fix addresses both issues
- Avoids duplicate work

## Verification Workflow

**After each fix (Step 3.6):**
1. Run local CI in subagent
2. Parse results
3. Triage:
   - All passed → Continue
   - New related failures → Fix immediately
   - Unrelated failures → Note and continue

**Changed files tracking:**
- Maintain list of all files modified in this session
- Pass to verification for relatedness analysis
- Helps distinguish new failures from pre-existing

**Verification timeout:**
- If verification takes too long, ask user:
  - Continue waiting
  - Skip verification for this fix
  - Skip all remaining verifications

## Examples

### Example 1: Incremental Strategy

```
Input: 3 issues (2 critical, 1 suggestion)

Step 1: User chooses "Incremental"

Step 2: Present summary
  - Issue 1: [Critical] Null pointer src/api.ts:42
  - Issue 2: [Test Failure] tests/api.test.ts:42
  - Issue 3: [Suggestion] Refactor src/utils.ts:15-20

Step 3: Work through issues
  Issue 1:
    - Read src/api.ts
    - Add null check
    - Verify (passed)
    - Commit "Fix null pointer in API handler"

  Issue 2:
    - Read tests/api.test.ts
    - Update test expectations
    - Verify (passed)
    - Commit "Update API tests for null handling"

  Issue 3:
    - Ask user: address/defer/skip?
    - User says "defer"
    - Create note, skip

Step 4: Final completion
  - All 2 critical issues fixed with 2 commits
  - 1 suggestion deferred
  - Final verification (all passed)
  - Ready to push
```

### Example 2: Accumulated Strategy

```
Input: 3 issues (2 critical, 1 warning)

Step 1: User chooses "Accumulated"

Step 2: Present summary
  - Issue 1: [Critical] Null pointer src/api.ts:42
  - Issue 2: [Critical] SQL injection src/db.ts:89
  - Issue 3: [Warning] Missing error handling src/api.ts:120

Step 3: Work through issues
  Issue 1:
    - Add null check
    - Verify (passed)
    - Don't commit yet

  Issue 2:
    - Use parameterized query
    - Verify (passed)
    - Don't commit yet

  Issue 3:
    - Add try/catch
    - Verify (passed)
    - Don't commit yet

Step 4: Final completion
  - Create single commit with all 3 fixes
  - Message: "Address feedback: fix null pointer, SQL injection, add error handling"
  - Final verification (all passed)
  - Ready for PR
```

### Example 3: Manual Strategy with Alignment

```
Input: 2 issues (aligned - same location)

Step 1: User chooses "Manual"

Step 2: Present summary
  - Issue 1: [Test Failure + Critical Review] src/api.ts:42

Step 3: Work through issues
  Issue 1 (aligned):
    - Present both failure and review together
    - User sees they're related
    - Add null check (fixes both)
    - Verify (passed)
    - Don't commit

Step 4: Final completion
  - All issues fixed
  - Changed files: src/api.ts
  - User will commit when ready
```

## Integration with Commands

### pr-address-feedback-local

```markdown
## 1. Gather Complete Local Feedback

[Step 1.a: Run getting-feedback-local skill in subagent]
[Wait for unified TOON output]

## 2. Address Issues Interactively

**2.a.** Pass feedback to addressing-feedback-interactively skill:
- Provide complete TOON output from step 1
- Skill handles:
  - Commit strategy selection
  - Issue presentation
  - Interactive resolution
  - Verification after fixes
  - Final commits based on strategy

**2.b.** Skill returns when complete:
- All issues addressed
- Commits created per user preference
- Final verification completed
```

### pr-address-feedback-remote

```markdown
## 1. Gather Complete PR Feedback

[Step 1.a: Run getting-feedback-remote skill in subagent]
[Wait for unified TOON output]

## 2. Address Issues Interactively

**2.a.** Pass feedback to addressing-feedback-interactively skill:
- Provide complete TOON output from step 1
- Skill handles:
  - Commit strategy selection (default: incremental for PRs)
  - Issue presentation
  - Interactive resolution
  - Verification after fixes
  - Final commits based on strategy
  - Push commits to remote

**2.b.** Skill returns when complete:
- All issues addressed
- Commits created and pushed per user preference
- Final verification completed
```

## Common Mistakes

**Not tracking changed files:**
- **Problem:** Can't determine if new failures are related
- **Fix:** Maintain list of all files modified in session

**Committing before verification:**
- **Problem:** Commit might introduce new failures
- **Fix:** Always verify before commit decision

**Skipping suggestions without asking:**
- **Problem:** User misses optional improvements
- **Fix:** Always ask user for suggestions (address/defer/skip)

**Not presenting aligned issues together:**
- **Problem:** User fixes same issue twice
- **Fix:** Detect alignment, present as single issue

**Not explaining commit strategies:**
- **Problem:** User picks wrong strategy for context
- **Fix:** Show recommendations (incremental for PRs, accumulated for local)

## Error Handling

**If verification fails repeatedly:**
- After 3 failed verification attempts on same fix
- Ask user:
  - Try different approach
  - Skip verification for this fix
  - Abort and investigate manually

**If user wants to change commit strategy mid-workflow:**
- Allow strategy change
- Adjust remaining workflow accordingly
- Don't undo commits already created

**If fix introduces new critical issues:**
- Stop immediately
- Investigate new issue
- Fix before proceeding with original issues

## Usage Pattern

**Called from commands:**

```markdown
Use Skill tool with skill='addressing-feedback-interactively':

Pass the complete TOON feedback from getting-feedback-local or getting-feedback-remote.

The skill will handle all user interaction for resolving issues.
```

**Skill expectations:**
- Input is well-formed TOON with parsed feedback
- User is available for interactive decisions
- Local CI commands are available (for verification)
- Git operations are available (for commits)

## Benefits

**Consistency:**
- Same workflow for local and remote
- Same issue presentation format
- Same priority logic

**User Control:**
- Choose commit strategy upfront
- Decide on each suggestion
- Full transparency

**Verification:**
- After each fix
- Catches regressions early
- Distinguishes new vs pre-existing failures

**Efficiency:**
- Priority-based ordering
- Aligned issues presented together
- Subagent verification (low token cost)
