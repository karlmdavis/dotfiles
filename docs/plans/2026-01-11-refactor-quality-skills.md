# Quality Skills Refactoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Apply progressive disclosure, clear workflows, and explicit progress tracking patterns to all quality triage skills.

**Architecture:** Extract complex workflow steps into separate files under skill subdirectories. Convert nested conditionals to flat decision trees. Add checklists for progress tracking. Provide TOON format context where needed.

**Tech Stack:** Markdown documentation, TOON format examples, skill frontmatter (YAML)

---

## Task 1: Complete quality-triage-pr Refactoring (Steps 2-4)

**Files:**
- Modify: `private_dot_claude/skills/quality-triage-pr/SKILL.md`
- Create: `private_dot_claude/skills/quality-triage-pr/triage_steps/triage_step_2_gather_feedback.md`
- Create: `private_dot_claude/skills/quality-triage-pr/triage_steps/triage_step_3_address_issues.md`
- Create: `private_dot_claude/skills/quality-triage-pr/triage_steps/triage_step_4_push_changes.md`

### Step 1.1: Read current Step 2 content from SKILL.md

Read lines 38-48 from `private_dot_claude/skills/quality-triage-pr/SKILL.md` to understand current Step 2 structure.

Expected: Step 2 has 2.a and 2.b substeps, uses getting-feedback-remote skill.

### Step 1.2: Create Step 2 extracted file with checklist

Create `private_dot_claude/skills/quality-triage-pr/triage_steps/triage_step_2_gather_feedback.md`:

```markdown
# Triage Step 2: Gather Complete PR Feedback

We need to gather all feedback from the PR: workflow failures, build results, and review comments. This is done in a subagent to prevent token bloat from large log files.

This checklist specifies the Gather Feedback steps. Copy this checklist and track your progress through it:

```
Gather Feedback Progress:
[ ] Gather Feedback Step 1: Spawn Quality Data Extractor Subagent
[ ] Gather Feedback Step 2: Wait for Unified TOON Output
```

## Gather Feedback Step 1: Spawn Quality Data Extractor Subagent

Use the Task tool with the following parameters:
- `subagent_type='quality-data-extractor'`
- `description="Get complete PR feedback"`

The subagent prompt should instruct it to use the `getting-feedback-remote` skill. This skill orchestrates:
1. Waiting for workflows to complete (via awaiting-pr-workflow-results)
2. Fetching build results from failed workflows (via getting-build-results-remote)
3. Fetching review comments from PR (via getting-reviews-remote)
4. Parsing and combining everything into unified TOON format

## Gather Feedback Step 2: Wait for Unified TOON Output

Wait for the subagent to complete and return unified TOON output with complete PR feedback.

**Critical:** The skill MUST run in a subagent, never in main context. This prevents token bloat from workflow logs and review text.

Once you receive the TOON output:
1. Parse it to understand the feedback structure
2. Do NOT display the raw TOON to the user - Step 3 will present issues in user-friendly format
3. ✅ We're done with Gather Feedback steps. Proceed to Triage Step 3.
```

Expected: New file created with checklist, numbered steps, clear completion statement.

### Step 1.3: Update SKILL.md Step 2 to reference extracted file

Edit `private_dot_claude/skills/quality-triage-pr/SKILL.md` to replace Step 2 content (lines 38-48) with:

```markdown
## Triage Step 2: Gather Complete PR Feedback

See [Triage Step 2: Gather Complete PR Feedback](triage_steps/triage_step_2_gather_feedback.md) and follow its instructions.
```

Expected: SKILL.md now uses progressive disclosure for Step 2.

### Step 1.4: Read current Step 3 content from SKILL.md

Read lines 50-73 from `private_dot_claude/skills/quality-triage-pr/SKILL.md` to understand current Step 3 structure.

Expected: Step 3 has 3.a and 3.b substeps, uses addressing-feedback-interactively skill.

### Step 1.5: Create Step 3 extracted file with checklist

Create `private_dot_claude/skills/quality-triage-pr/triage_steps/triage_step_3_address_issues.md`:

```markdown
# Triage Step 3: Address Issues Interactively

We now have complete PR feedback. Let's work through each issue interactively with the user, fixing what needs to be fixed and deferring what can wait.

This checklist specifies the Address Issues steps. Copy this checklist and track your progress through it:

```
Address Issues Progress:
[ ] Address Issues Step 1: Invoke addressing-feedback-interactively Skill
[ ] Address Issues Step 2: Support User Through Issue Resolution
```

## Address Issues Step 1: Invoke addressing-feedback-interactively Skill

Use the Skill tool with the following parameters:
- `skill='addressing-feedback-interactively'`

In your prompt to the skill, pass the complete TOON feedback from Triage Step 2.

The skill will handle:
1. **Commit strategy selection** - Ask user to choose: incremental, accumulated, or manual
   - Recommend "incremental" for PR workflow (one commit per fix)
2. **Issue presentation** - Show unified summary of all issues with priorities
3. **Interactive resolution** - Work through each issue with user approval
4. **Verification** - Run tests/checks after each fix
5. **Commits** - Create commits based on user's chosen strategy

## Address Issues Step 2: Support User Through Issue Resolution

The addressing-feedback-interactively skill will guide the process, but you should:
1. Monitor progress and answer any user questions
2. Help interpret error messages or build failures
3. Clarify issue descriptions if user asks
4. Support the user's decisions about which issues to address vs defer

Once all issues are addressed (or deferred):
1. The skill will report how many commits were created
2. ✅ We're done with Address Issues steps. Proceed to Triage Step 4.
```

Expected: New file created with checklist, numbered steps, clear role delineation.

### Step 1.6: Update SKILL.md Step 3 to reference extracted file

Edit `private_dot_claude/skills/quality-triage-pr/SKILL.md` to replace Step 3 content (lines 50-73) with:

```markdown
## Triage Step 3: Address Issues Interactively

See [Triage Step 3: Address Issues Interactively](triage_steps/triage_step_3_address_issues.md) and follow its instructions.
```

Expected: SKILL.md now uses progressive disclosure for Step 3.

### Step 1.7: Read current Step 4 content from SKILL.md

Read lines 75-89 from `private_dot_claude/skills/quality-triage-pr/SKILL.md` to understand current Step 4 structure.

Expected: Step 4 has 4.a and 4.b substeps, asks about pushing.

### Step 1.8: Create Step 4 extracted file with checklist

Create `private_dot_claude/skills/quality-triage-pr/triage_steps/triage_step_4_push_changes.md`:

```markdown
# Triage Step 4: Push Changes to Remote, Maybe

All issues have been addressed and committed locally. Now we need to push those commits to the PR so workflows can run again.

This checklist specifies the Push Changes steps. Copy this checklist and track your progress through it:

```
Push Changes Progress:
[ ] Push Changes Step 1: Ask User About Pushing
[ ] Push Changes Step 2: Execute Push if Confirmed
```

## Push Changes Step 1: Ask User About Pushing

After all issues are addressed and committed, ask the user once using AskUserQuestion tool:

```markdown
**Question:** "All issues resolved with {N} commit(s). Push to remote branch?"

**Options:**
1. "Yes, Push Now"
   - Description: "Push commits to PR immediately so workflows can run"
2. "No, I'll Push Manually"
   - Description: "Exit without pushing - you can push when ready"
```

Where `{N}` is the number of commits created in Step 3.

## Push Changes Step 2: Execute Push if Confirmed

Based on user choice:

**Option 1: Yes, Push Now**
1. Execute: `git push`
2. Report success: "✅ Pushed {N} commit(s) to remote. PR workflows will run again shortly."
3. ✅ We're done! Quality triage complete.

**Option 2: No, I'll Push Manually**
1. Report: "Skipping push. You can push manually when ready with `git push`."
2. ✅ We're done! Quality triage complete (commits ready to push).
```

Expected: New file created with checklist, numbered steps, clear outcomes.

### Step 1.9: Update SKILL.md Step 4 to reference extracted file

Edit `private_dot_claude/skills/quality-triage-pr/SKILL.md` to replace Step 4 content (lines 75-89) with:

```markdown
## Triage Step 4: Push Changes to Remote, Maybe

See [Triage Step 4: Push Changes to Remote, Maybe](triage_steps/triage_step_4_push_changes.md) and follow its instructions.
```

Expected: SKILL.md now uses progressive disclosure for all 4 steps.

### Step 1.10: Verify SKILL.md structure and consistency

Read entire `private_dot_claude/skills/quality-triage-pr/SKILL.md` file.

Verify:
- [ ] Frontmatter has all required fields
- [ ] TOON example is present and clear
- [ ] Top-level checklist references Steps 1-4
- [ ] All 4 steps reference their extracted files
- [ ] Example Flow section still makes sense
- [ ] No broken internal references

Expected: Main skill file is clean, focused, uses progressive disclosure throughout.

---

## Task 2: Refactor quality-triage Skill

**Files:**
- Modify: `private_dot_claude/skills/quality-triage/SKILL.md`
- Create: `private_dot_claude/skills/quality-triage/triage_steps/triage_step_0_parse_scope.md`
- Create: `private_dot_claude/skills/quality-triage/triage_steps/triage_step_1_check_status.md`
- Create: `private_dot_claude/skills/quality-triage/triage_steps/triage_step_2_gather_feedback.md`
- Create: `private_dot_claude/skills/quality-triage/triage_steps/triage_step_3_address_issues.md`

### Step 2.1: Read current quality-triage SKILL.md

Read `private_dot_claude/skills/quality-triage/SKILL.md` to understand structure.

Expected: Similar to quality-triage-pr but for local workflow, has scope argument validation.

### Step 2.2: Add frontmatter to quality-triage SKILL.md

Add YAML frontmatter to top of `private_dot_claude/skills/quality-triage/SKILL.md`:

```yaml
---
description: Gather and triage all local quality issues (build + review) interactively
user-invocable: true
disable-model-invocation: true
tools: Bash, Edit, Skill, WebFetch, WebSearch, Write, LSP, mcp__ide__getDiagnostics, mcp__ide__executeCode
---
```

Expected: Skill now has proper frontmatter.

### Step 2.3: Add opening paragraph and TOON example

After frontmatter, add:

```markdown
I would like you to gather all local feedback (build failures and review comments) for a specified scope, then interactively guide the user through addressing all of that feedback. I will give you a checklist of Triage Steps 0 through 3 and ask you to track your progress through them. Some Triage Steps will have their own checklists and steps, which you will be asked to track your progress through, as well.

Many steps will produce and/or consume TOON-formatted data, which is a structured data format suited for use by agents. TOON is similar to JSON and YAML but uses 2-space indents and arrays show length and fields. Here's a small toy example:

```toon
context:
  task: Our favorite hikes together
  location: Boulder
  season: spring_2025
friends[3]: ana,luis,sam
hikes[3]{id,name,distanceKm,elevationGain,companion,wasSunny}:
  1,Blue Lake Trail,7.5,320,ana,true
  2,Ridge Overlook,9.2,540,luis,false
  3,Wildflower Loop,5.1,180,sam,true
```

This checklist specifies the top-level Triage Steps for the local quality triage process. Copy this checklist and track your progress through it:

```
Local Quality Triage Progress:
[ ] Triage Step 0: Parse and Validate Scope Argument
[ ] Triage Step 1: Check Branch State
[ ] Triage Step 2: Gather Complete Local Feedback
[ ] Triage Step 3: Address Issues Interactively
```
```

Expected: Introduction and checklist added.

### Step 2.4: Create directory for triage_steps

Run: `mkdir -p private_dot_claude/skills/quality-triage/triage_steps`

Expected: Directory created for step files.

### Step 2.5: Extract Step 0 (Scope Validation) to separate file

Create `private_dot_claude/skills/quality-triage/triage_steps/triage_step_0_parse_scope.md`:

```markdown
# Triage Step 0: Parse and Validate Scope Argument

The quality-triage command accepts a scope argument that determines what code to review. We need to parse and validate this argument before proceeding.

This checklist specifies the Parse Scope steps. Copy this checklist and track your progress through it:

```
Parse Scope Progress:
[ ] Parse Scope Step 1: Extract Scope Argument
[ ] Parse Scope Step 2: Validate Scope Value
[ ] Parse Scope Step 3: Determine Files to Review
```

## Parse Scope Step 1: Extract Scope Argument

The scope argument is provided by the user when they invoke the skill. Extract it from the command invocation.

Expected format: `/quality-triage <scope>`

Where `<scope>` is one of: `everything`, `uncommitted`, `branch`, `branch-dirty`

## Parse Scope Step 2: Validate Scope Value

Check if the extracted scope is one of the valid options:
1. If scope is `everything`, `uncommitted`, `branch`, or `branch-dirty` → ✅ Valid, proceed to Parse Scope Step 3
2. If scope is anything else → ❌ Invalid

**For invalid scope:**
1. Display error: "**Error:** Invalid scope '{scope}'. Valid options: everything, uncommitted, branch, branch-dirty"
2. Exit cleanly; we cannot proceed until user provides valid scope

## Parse Scope Step 3: Determine Files to Review

Based on the validated scope value, determine which files will be reviewed:

**Scope: `everything`**
- Review all files in the branch vs base branch
- This is comprehensive but may include many files

**Scope: `uncommitted`**
- Review only uncommitted changes (staged + unstaged)
- Quick local feedback before committing

**Scope: `branch`**
- Review all committed changes in current branch vs base branch
- Excludes uncommitted changes

**Scope: `branch-dirty`**
- Review all changes: committed (branch vs base) + uncommitted (staged + unstaged)
- Most comprehensive for current work

Once scope is validated and understood:
1. Store the scope value for use in later steps
2. ✅ We're done with Parse Scope steps. Proceed to Triage Step 1.
```

Expected: Step 0 extracted with clear validation logic.

### Step 2.6: Update SKILL.md to reference Step 0

Replace Step 0 content in `private_dot_claude/skills/quality-triage/SKILL.md` with:

```markdown
## Triage Step 0: Parse and Validate Scope Argument

See [Triage Step 0: Parse and Validate Scope Argument](triage_steps/triage_step_0_parse_scope.md) and follow its instructions.
```

Expected: Progressive disclosure for Step 0.

### Step 2.7: Extract Step 1 (Check Branch State) to separate file

Create `private_dot_claude/skills/quality-triage/triage_steps/triage_step_1_check_status.md`:

```markdown
# Triage Step 1: Check Branch State

We need to understand the current branch state to determine what code should be reviewed based on the scope from Step 0.

This checklist specifies the Check Status steps. Copy this checklist and track your progress through it:

```
Check Status Progress:
[ ] Check Status Step 1: Run getting-branch-state Skill
[ ] Check Status Step 2: Extract Relevant Information Based on Scope
```

## Check Status Step 1: Run getting-branch-state Skill

Use the Skill tool with skill='getting-branch-state' to retrieve TOON-formatted data on the working copy's status. We will then manually parse and interpret the TOON output it produces.

## Check Status Step 2: Extract Relevant Information Based on Scope

Parse the TOON output from Step 1 and extract information based on the scope from Triage Step 0:

**For scope: `uncommitted`**
1. Extract `local.uncommitted_files[]` - these are the files to review
2. If list is empty → Inform user: "No uncommitted changes to review"

**For scope: `branch`**
1. Extract `comparison.branch_vs_base.changed_files[]` - committed changes only
2. Exclude uncommitted files

**For scope: `branch-dirty`**
1. Extract `comparison.branch_vs_base.changed_files[]` - committed changes
2. Also extract `local.uncommitted_files[]` - uncommitted changes
3. Combine both lists (deduplicate if needed)

**For scope: `everything`**
1. Extract `comparison.branch_vs_base.changed_files[]`
2. This already includes all branch changes

Once file list is extracted:
1. Display to user: "Reviewing {N} file(s) with scope '{scope}'"
2. ✅ We're done with Check Status steps. Proceed to Triage Step 2.
```

Expected: Step 1 extracted with scope-aware logic.

### Step 2.8: Update SKILL.md to reference Step 1

Replace Step 1 content in `private_dot_claude/skills/quality-triage/SKILL.md` with:

```markdown
## Triage Step 1: Check Branch State

See [Triage Step 1: Check Branch State](triage_steps/triage_step_1_check_status.md) and follow its instructions.
```

Expected: Progressive disclosure for Step 1.

### Step 2.9: Extract Step 2 (Gather Feedback) to separate file

Create `private_dot_claude/skills/quality-triage/triage_steps/triage_step_2_gather_feedback.md`:

```markdown
# Triage Step 2: Gather Complete Local Feedback

We need to gather all local feedback: build failures, test results, and local code review. This is done in a subagent to prevent token bloat.

This checklist specifies the Gather Feedback steps. Copy this checklist and track your progress through it:

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
1. The file list from Step 1 (files to review)
2. The scope from Step 0 (for context)

This skill orchestrates:
1. Running local CI commands (via getting-build-results-local)
2. Running local code review (via getting-review-local)
3. Parsing and combining everything into unified TOON format

## Gather Feedback Step 2: Wait for Unified TOON Output

Wait for the subagent to complete and return unified TOON output with complete local feedback.

**Critical:** The skill MUST run in a subagent, never in main context. This prevents token bloat from build logs.

Once you receive the TOON output:
1. Parse it to understand the feedback structure
2. Do NOT display the raw TOON to the user - Step 3 will present issues in user-friendly format
3. ✅ We're done with Gather Feedback steps. Proceed to Triage Step 3.
```

Expected: Step 2 extracted with local-specific context.

### Step 2.10: Update SKILL.md to reference Step 2

Replace Step 2 content in `private_dot_claude/skills/quality-triage/SKILL.md` with:

```markdown
## Triage Step 2: Gather Complete Local Feedback

See [Triage Step 2: Gather Complete Local Feedback](triage_steps/triage_step_2_gather_feedback.md) and follow its instructions.
```

Expected: Progressive disclosure for Step 2.

### Step 2.11: Extract Step 3 (Address Issues) to separate file

Create `private_dot_claude/skills/quality-triage/triage_steps/triage_step_3_address_issues.md`:

```markdown
# Triage Step 3: Address Issues Interactively

We now have complete local feedback. Let's work through each issue interactively with the user, fixing what needs to be fixed and deferring what can wait.

This checklist specifies the Address Issues steps. Copy this checklist and track your progress through it:

```
Address Issues Progress:
[ ] Address Issues Step 1: Invoke addressing-feedback-interactively Skill
[ ] Address Issues Step 2: Support User Through Issue Resolution
```

## Address Issues Step 1: Invoke addressing-feedback-interactively Skill

Use the Skill tool with the following parameters:
- `skill='addressing-feedback-interactively'`

In your prompt to the skill, pass the complete TOON feedback from Triage Step 2.

The skill will handle:
1. **Commit strategy selection** - Ask user to choose: incremental, accumulated, or manual
   - For local workflow, any strategy works well
2. **Issue presentation** - Show unified summary of all issues with priorities
3. **Interactive resolution** - Work through each issue with user approval
4. **Verification** - Run tests/checks after each fix
5. **Commits** - Create commits based on user's chosen strategy

## Address Issues Step 2: Support User Through Issue Resolution

The addressing-feedback-interactively skill will guide the process, but you should:
1. Monitor progress and answer any user questions
2. Help interpret error messages or build failures
3. Clarify issue descriptions if user asks
4. Support the user's decisions about which issues to address vs defer

Once all issues are addressed (or deferred):
1. The skill will report how many commits were created
2. ✅ We're done! Local quality triage complete.
```

Expected: Step 3 extracted, similar to PR version but local-focused.

### Step 2.12: Update SKILL.md to reference Step 3

Replace Step 3 content in `private_dot_claude/skills/quality-triage/SKILL.md` with:

```markdown
## Triage Step 3: Address Issues Interactively

See [Triage Step 3: Address Issues Interactively](triage_steps/triage_step_3_address_issues.md) and follow its instructions.
```

Expected: Progressive disclosure for Step 3.

### Step 2.13: Add example flow section to SKILL.md

Add to end of `private_dot_claude/skills/quality-triage/SKILL.md`:

```markdown
## Example Flow

Note that this is a logical flow, not code to run or the exact messages to show your user.

```
Step 0: Parse scope
   - User ran: /quality-triage branch-dirty
   - Scope: branch-dirty (valid)
   - Will review: committed + uncommitted changes

Step 1: Check branch state
   - Run getting-branch-state skill
   - Branch: feature-auth
   - Committed files: 3
   - Uncommitted files: 2
   - Total to review: 5 files

Step 2: Gather local feedback
   - Run getting-feedback-local skill in subagent
   - Runs local CI (mise run ci)
   - Runs local review
   - Returns: 2 issues (1 test failure, 1 suggestion)

Step 3: Address issues interactively
   - Skill asks: "How would you like to commit fixes?"
   - User chooses: "Incremental"

   - Issue 1: [Test Failure] tests/api.test.ts:42
     - Fix test expectations
     - Verify (passed)
     - Commit "test: update api.test.ts expectations"

   - Issue 2: [Suggestion] Refactor src/utils.ts:15-20
     - User defers

   - Done: 1 commit created, 1 issue deferred

✅ Local quality triage complete!
```
```

Expected: Example flow added showing typical execution.

### Step 2.14: Verify quality-triage SKILL.md structure

Read entire `private_dot_claude/skills/quality-triage/SKILL.md` file.

Verify:
- [ ] Frontmatter has all required fields
- [ ] TOON example is present and clear
- [ ] Top-level checklist references Steps 0-3
- [ ] All 4 steps reference their extracted files
- [ ] Example Flow section makes sense
- [ ] No broken internal references

Expected: Skill is fully refactored with progressive disclosure.

---

## Task 3: Review and Refactor addressing-feedback-interactively Skill

**Files:**
- Read: `private_dot_claude/skills/addressing-feedback-interactively/SKILL.md`
- Potentially modify based on findings

### Step 3.1: Read addressing-feedback-interactively SKILL.md

Read `private_dot_claude/skills/addressing-feedback-interactively/SKILL.md` to assess current state.

Check for:
- Does it have frontmatter?
- Does it use checklists?
- Does it use progressive disclosure?
- Are conditionals flattened?
- Is TOON format explained?

Expected: Assessment of what needs refactoring.

### Step 3.2: Document findings

Create notes on what refactoring is needed for this skill. Since it's invoked BY the triage skills, it may have different requirements.

Consider:
- Is it user-invocable or only called by other skills?
- Does it have complex multi-step workflows?
- Would progressive disclosure help?

Expected: Clear list of needed changes (may be empty if already good).

### Step 3.3: Apply refactoring if needed

Based on findings, apply the 17 refactoring patterns as appropriate to addressing-feedback-interactively.

This step may involve:
- Adding frontmatter
- Adding checklists
- Extracting complex sections
- Flattening conditionals
- Adding TOON examples

Expected: Skill improved based on assessment.

---

## Task 4: Review Data-Gathering Skills for Documentation Clarity

**Files:**
- Read: All skills in `private_dot_claude/skills/getting-*/SKILL.md`
- Read: All skills in `private_dot_claude/skills/parsing-*/SKILL.md`
- Potentially modify based on findings

### Step 4.1: Review each data-gathering skill

For each of these skills:
- awaiting-pr-workflow-results
- getting-branch-state
- getting-build-results-local
- getting-build-results-remote
- getting-review-local
- getting-reviews-remote
- parsing-build-results
- parsing-review-suggestions

Read the SKILL.md and check:
1. Does it explain TOON output format clearly?
2. Are usage instructions clear and explicit?
3. Are there good examples?
4. Is the "When to Use" section clear?

Expected: Understanding of documentation quality.

### Step 4.2: Document recommended improvements

For each skill that could be improved, document specific recommendations:
- Add TOON output examples?
- Clarify usage instructions?
- Add more "When NOT to use" guidance?
- Add troubleshooting section?

Expected: List of documentation improvements.

### Step 4.3: Apply high-value improvements

Apply the most valuable documentation improvements to the data-gathering skills. Focus on:
1. Adding concrete TOON output examples where missing
2. Clarifying when to use vs not use
3. Adding common pitfalls sections

Expected: Improved documentation for data-gathering skills.

---

## Task 5: Create Skills Documentation Index

**Files:**
- Create: `private_dot_claude/skills/README.md`

### Step 5.1: Create skills overview document

Create `private_dot_claude/skills/README.md`:

```markdown
# Claude Code Skills

This directory contains custom skills for quality triage workflows.

## User-Invocable Skills

These skills can be invoked directly by users via slash commands:

- **quality-triage** - Gather and triage local build/review feedback interactively
- **quality-triage-pr** - Gather and triage PR workflow/review feedback interactively

## Orchestrator Skills

These skills coordinate multiple sub-skills to gather and parse feedback:

- **getting-feedback-local** - Orchestrate local CI + review (runs in subagent)
- **getting-feedback-remote** - Orchestrate PR workflows + reviews (runs in subagent)
- **addressing-feedback-interactively** - Guide user through fixing issues

## Data-Gathering Skills

These skills fetch raw data (build logs, reviews, etc.):

- **awaiting-pr-workflow-results** - Check PR workflow status and wait for completion
- **getting-branch-state** - Analyze git branch state and PR sync status
- **getting-build-results-local** - Run local CI commands and return output
- **getting-build-results-remote** - Fetch GitHub workflow logs
- **getting-review-local** - Perform local code review
- **getting-reviews-remote** - Fetch PR review comments from GitHub

## Parsing Skills

These skills parse raw data into structured TOON format:

- **parsing-build-results** - Parse build/test logs into structured failures
- **parsing-review-suggestions** - Parse review text into structured issues

## Architecture

The skills follow a layered architecture:

```
User-Invocable Skills (quality-triage, quality-triage-pr)
    ↓
Orchestrator Skills (getting-feedback-*, addressing-feedback-*)
    ↓
Data-Gathering Skills (getting-*, awaiting-*)
    ↓
Parsing Skills (parsing-*)
```

## TOON Format

Many skills use TOON (Token-Oriented Object Notation) for structured data exchange. TOON is similar to JSON/YAML but optimized for LLM consumption with 2-space indents and array length/field annotations.

Example:
```toon
status: success
issues[2]{id,severity,file,line,description}:
  1,critical,src/api.ts,42,Null pointer risk
  2,suggestion,src/utils.ts,15,Consider refactoring
```

## Refactoring Patterns

These skills implement best practices for Claude Code:
1. Progressive disclosure - Complex steps in separate files
2. Checklists for progress tracking
3. Flat decision trees (not nested conditionals)
4. Clear completion statements
5. Explicit error handling paths
6. Concrete examples throughout
```

Expected: Overview document created.

### Step 5.2: Verify README accuracy

Read the created README and verify all skill names and descriptions are accurate.

Expected: README is accurate and helpful.

---

## Verification

After completing all tasks, verify:

1. **quality-triage-pr** - All 4 steps use progressive disclosure, have checklists, clear transitions
2. **quality-triage** - All 4 steps (0-3) use same patterns
3. **addressing-feedback-interactively** - Assessed and improved as needed
4. **Data-gathering skills** - Documentation improved with examples
5. **Skills README** - Overview document exists and is accurate

No commits should be created yet per user request.

---

## Notes

- Do NOT commit changes - leave unstaged for user review
- Each extracted step file should have:
  - Clear explanation of why this step matters
  - Checklist for substeps
  - Numbered steps with explicit outcomes
  - Clear completion statement
- Main SKILL.md files should be thin, just linking to step files
- TOON examples should be concrete and realistic
- Decision trees should be flat, not nested
