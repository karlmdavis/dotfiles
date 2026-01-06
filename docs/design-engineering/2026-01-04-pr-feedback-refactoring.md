# PR Feedback System Refactoring

**Date:** 2026-01-04
**Status:** Approved Design
**Context:** Refactor PR-related Claude Code skills for better reusability and token efficiency

## Overview

Refactor PR feedback skills into a layered architecture that supports both local (pre-PR) and remote (PR) workflows while maximizing code reuse and minimizing token consumption.

## Problem Statement

Current PR skills (`getting-pr-workflow-results`, `getting-pr-review-comments`, `getting-pr-artifacts`) have overlapping functionality and don't support local pre-PR workflows. We need:

1. Support for local feedback loops (local builds + local code review)
2. Support for remote feedback loops (GitHub workflows + PR reviews)
3. Shared parsing logic for build failures and review suggestions
4. Token-efficient subagent patterns throughout
5. Consistent TOON output format across all skills

## Architecture

### Three-Layer Design

**Layer 1: Parsing (source-agnostic, reusable)**
- `parsing-build-results` - Parses build output into structured failures
- `parsing-review-suggestions` - Parses reviews into structured issues with code references

**Layer 2: Fetching (source-specific)**
- `awaiting-pr-workflow-results` - (EXISTS) Waits for workflows, returns URLs
- `getting-build-results-local` - Runs local CI, returns raw output
- `getting-build-results-remote` - Fetches workflow logs from URLs
- `getting-review-local` - Calls obra review skill for local changes
- `getting-reviews-remote` - Fetches GitHub PR reviews and comments

**Layer 3: Orchestration**
- `getting-feedback-local` - Combines local build + local review
- `getting-feedback-remote` - Combines remote workflows + remote reviews

### Naming Convention

Pattern: `{action}-{subject}-{context}`
- Action: `parsing`, `getting`, `awaiting`
- Subject: `build-results`, `reviews`, `feedback`
- Context: `local`, `remote` (suffix for better sorting)

### Data Flow

**Remote Feedback:**
```
/address-feedback-remote
  ↓
getting-feedback-remote (subagent)
  ├─→ awaiting-pr-workflow-results → workflow URLs
  │     ↓
  │   getting-build-results-remote → raw logs
  │     ↓
  │   parsing-build-results → structured failures
  │
  └─→ getting-reviews-remote → raw reviews
        ↓
      parsing-review-suggestions → structured issues
  ↓
Combined TOON → Main context
```

**Local Feedback:**
```
/address-feedback-local
  ↓
getting-feedback-local (subagent)
  ├─→ getting-build-results-local → raw output
  │     ↓
  │   parsing-build-results (REUSED)
  │     ↓
  │   structured failures
  │
  └─→ getting-review-local → review data
        ↓
      parsing-review-suggestions (REUSED)
        ↓
      structured issues
  ↓
Combined TOON → Main context
```

## Skills Implementation

### Scripts Required (3 skills)

**awaiting-pr-workflow-results** (exists)
- Python script with TOON output
- Waits for workflows (up to 20min with exponential backoff)
- Returns: workflow status, URLs, artifact URLs

**getting-build-results-remote** (new)
- Python script
- Fetches workflow logs via `gh` CLI using URLs from awaiting skill
- Returns TOON: `{ci_commands, raw_output}`

**getting-reviews-remote** (new)
- Python script
- Fetches via `gh` CLI and GraphQL:
  - Claude bot comments (filtered by commit push timestamp)
  - GitHub PR reviews (filtered by commit SHA)
  - Earlier unresolved threads (with summaries and links)
- Returns TOON with raw review bodies

### Agent-Only Skills (6 skills - SKILL.md only)

**getting-build-results-local**
- Agent reads CLAUDE.md to find CI command(s)
- Runs commands via Bash tool
- Returns TOON: `{ci_commands, raw_output}`

**getting-review-local**
- Agent calls obra review skill
- Structures output as TOON
- Returns review data

**parsing-build-results**
- Agent parses raw build output
- Extracts failures with file:line locations
- Returns structured TOON (see format below)

**parsing-review-suggestions**
- Agent parses raw review text
- Extracts issues with code references
- Returns structured TOON (see format below)

**getting-feedback-local** (orchestrator)
- Runs getting-build-results-local → parsing-build-results
- Runs getting-review-local → parsing-review-suggestions
- Combines into unified TOON

**getting-feedback-remote** (orchestrator)
- Runs awaiting-pr-workflow-results
- Runs getting-build-results-remote → parsing-build-results
- Runs getting-reviews-remote → parsing-review-suggestions
- Combines into unified TOON

## TOON Output Formats

### Build Results TOON

```toon
status: fail_related

ci_commands[2]:
  id: 1
  command: MISE_EXPERIMENTAL=true mise run ':lint'
  cwd: /Users/karl/projects/myapp
  exit_code: 0
  duration_seconds: 12

  id: 2
  command: MISE_EXPERIMENTAL=true mise run ':test'
  cwd: /Users/karl/projects/myapp
  exit_code: 1
  duration_seconds: 33

failures[2]:
  type: test
  location: tests/api.test.ts:42
  source_command_id: 2
  related_to_changes: true
  reasoning: |
    This test failure is in code modified in this changeset.
  messages[2]:
    |
      FAIL tests/api.test.ts
        ● should handle null user
    |
      TypeError: Cannot read property 'id' of null
        at handler (src/api.ts:89)

recommendation: fix_related_first
```

### Review Suggestions TOON

```toon
status: success
pr_number: 123
current_commit: a1b2c3d

claude_bot_review:
  updated_at: 2026-01-04T15:30:00Z
  link: https://github.com/.../issuecomment-123
  overall_summary: |
    Overall the changes look solid! Found 2 critical issues...
    Recommendation: Address critical issues, then ready to merge.

  issues[2]:
    severity: critical
    link: https://...#ref-42
    code_references[1]:
      file: src/api.ts
      line: 42
    description: |
      The user object may be null here. Add null check...

github_reviews[2]:
  reviewer: alice
  state: changes_requested
  submitted_at: 2026-01-04T14:00:00Z
  review_link: https://github.com/.../pullrequestreview-789
  summary: |
    Nice work! See inline comments about error handling.

  inline_comments[2]:
    reviewer: alice
    link: https://github.com/.../discussion_r456
    code_references[1]:
      file: src/api.ts
      line: 89
    description: |
      Error handling missing in database call...

unresolved_earlier[5]:
  link: https://github.com/.../discussion_r789
  reviewer: alice
  code_references[1]:
    file: src/auth.ts
    line_range: 15-18
  summary: Handle edge case when user validation fails
```

### Unified Feedback TOON

```toon
status: success
pr_number: 123
current_commit: a1b2c3d

workflows:
  [output from awaiting-pr-workflow-results]

build_results:
  [output from parsing-build-results]

reviews:
  [output from parsing-review-suggestions]

summary:
  total_workflow_failures: 1
  total_build_failures: 2
  total_review_issues: 4
  unresolved_earlier_count: 5
  overall_status: needs_attention
```

## Commands

### /address-feedback-remote

**Purpose:** Interactive PR feedback loop (workflows + reviews)

**Flow:**
1. Spawn subagent running `getting-feedback-remote` skill
2. Receive unified TOON with all feedback
3. Present summary to user (counts + numbered issue list)
4. For each issue:
   - Investigate and implement fix
   - Run `getting-build-results-local` in subagent
   - Parse results via `parsing-build-results`
   - Triage: Are failures related to current fix?
     - Related → Fix before committing
     - Unrelated → Ask user how to proceed
   - Commit fix with clear message
5. Ask once to push all commits

### /address-feedback-local

**Purpose:** Pre-PR local feedback loop (local builds + local review)

**Flow:** Same as remote, but uses `getting-feedback-local` in step 1

## Key Design Decisions

### 1. Agent vs Script Split

**Scripts only for:**
- Fetching external data via APIs/CLI
- Complex API interactions (GraphQL, pagination)

**Agent (SKILL.md) for:**
- Reading project documentation
- Parsing unstructured text (logs, reviews)
- Orchestration and decision-making

**Rationale:** Leverage AI's strength in understanding context and parsing text, use scripts only for mechanical data fetching.

### 2. Triage Context

**Initial approach:** Commands handle triage in main context

**Reasoning:**
- Pre-commit: "Are failures from staged changes?" (`git diff --staged`)
- Post-push: "Are failures from branch changes?" (`git diff main...HEAD`)
- Commands have natural access to this context
- Simpler than parameterizing or duplicating skills

**Future optimization:** If token usage is high (>10k per triage), move to skill-based triage with parameters.

### 3. Code References as Lists

Reviews can reference multiple files/lines:
```toon
code_references[2]:
  file: src/api.ts
  line: 42

  file: src/utils.ts
  line_range: 15-18
```

Handles architectural suggestions that span multiple locations.

### 4. Comprehensive Issue Details

Subagents return full issue descriptions (not summaries) so main context can:
- Understand complete context
- Evaluate with user
- Implement fixes properly

### 5. Review Summaries Included

Both Claude bot and GitHub reviews include overall summaries showing tone and recommendations (approved/changes requested/commented).

### 6. Build Command IDs

Each CI command gets numeric ID for unambiguous failure attribution:
```toon
ci_commands[2]:
  id: 1
  command: npm test
  cwd: /frontend

  id: 2
  command: npm test
  cwd: /backend

failures[1]:
  source_command_id: 2  # Clearly references backend tests
```

## Implementation Plan

### Phase 1: Remote Build Results
1. Create `getting-build-results-remote` script (fetch logs via gh CLI)
2. Create `parsing-build-results` SKILL.md (agent parsing)
3. Test with real workflow failures

### Phase 2: Remote Reviews
1. Create `getting-reviews-remote` script
   - Fetch Claude bot comments (timestamp filter)
   - Fetch GitHub reviews (commit SHA filter)
   - Fetch unresolved threads
2. Create `parsing-review-suggestions` SKILL.md
3. Test with real PR reviews

### Phase 3: Remote Orchestration
1. Create `getting-feedback-remote` SKILL.md (orchestrates Phase 1 + 2)
2. Test unified output

### Phase 4: Local Feedback
1. Create `getting-build-results-local` SKILL.md (reads docs, runs CI)
2. Create `getting-review-local` SKILL.md (calls obra skill)
3. Create `getting-feedback-local` SKILL.md (orchestrates local)
4. Test local workflow

### Phase 5: Commands
1. Rename `pr-check-qa.md` → `pr-address-feedback-remote.md`
2. Update to use `getting-feedback-remote` + pre-commit verification
3. Create `pr-address-feedback-local.md`
4. Test both commands end-to-end

### Phase 6: Cleanup
1. Delete `getting-pr-workflow-results`
2. Delete `getting-pr-review-comments`
3. Delete `getting-pr-artifacts`
4. Update any remaining references

## Skills Inventory

**To Create (8 skills):**
- `getting-build-results-remote` (script)
- `getting-reviews-remote` (script)
- `parsing-build-results` (agent-only)
- `parsing-review-suggestions` (agent-only)
- `getting-build-results-local` (agent-only)
- `getting-review-local` (agent-only)
- `getting-feedback-local` (agent-only)
- `getting-feedback-remote` (agent-only)

**To Delete (3 skills):**
- `getting-pr-workflow-results`
- `getting-pr-review-comments`
- `getting-pr-artifacts`

**Unchanged (1 skill):**
- `awaiting-pr-workflow-results` (already refactored)

## Success Criteria

1. Local pre-PR workflow functional (`/address-feedback-local`)
2. Remote PR workflow functional (`/address-feedback-remote`)
3. Parsing layers successfully reused across local/remote
4. All output in consistent TOON format
5. Token usage reasonable (<5k tokens for typical feedback summary)
6. Pre-commit verification catches related failures before commit

## Future Enhancements

1. **Token usage optimization:** If triage burns >10k tokens, move to skill-based approach
2. **Parallel skill execution:** Run build results and reviews concurrently
3. **Caching:** Cache parsed results to avoid re-parsing on retry
4. **Progressive disclosure:** Return summary first, details on demand
5. **Custom parsers:** Project-specific build output parsers for complex toolchains

---

## Phase 2: Interactive Feedback Resolution Refinement

**Date:** 2026-01-05
**Status:** Design
**Context:** Extract shared issue presentation and resolution logic from commands into reusable skill

### Problem Statement

Both `pr-address-feedback-local` and `pr-address-feedback-remote` currently duplicate the logic for:
- Presenting issues in a consistent format
- Walking users through each issue interactively
- Verifying fixes after implementation
- Managing commit strategy

This duplication leads to:
1. **Inconsistency:** Commands use different commit strategies (accumulate vs incremental)
2. **Maintenance burden:** Same logic must be updated in two places
3. **Missed opportunities:** Improvements to one command don't benefit the other
4. **Unclear UX:** Users get different experiences for local vs remote workflows

### Solution: Extract Shared Workflow into Skill

Create new skill: **`addressing-feedback-interactively`**

This skill handles the common workflow (Steps 2-4 from both commands):
- Present unified summary of all issues
- Guide user through each issue with consistent UX
- Verify fixes incrementally
- Manage commit strategy based on user preference

### Updated Architecture

```
┌──────────────────────────────────────────────────────────┐
│ pr-address-feedback-local                                │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ Step 0: Determine review context (branch vs staged) │ │
│ │ Step 1: Call getting-feedback-local skill           │ │
│ └──────────────────────────────────────────────────────┘ │
│                          ▼                               │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ Step 2: Call addressing-feedback-interactively skill│ │
│ │ • Choose commit strategy                            │ │
│ │ • Present issues summary                            │ │
│ │ • Walk through each issue                           │ │
│ │ • Verify after each fix                             │ │
│ │ • Handle commits per strategy                       │ │
│ └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ pr-address-feedback-remote                               │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ Step 0: Get PR context (number, commit SHA)         │ │
│ │ Step 1: Call getting-feedback-remote skill          │ │
│ └──────────────────────────────────────────────────────┘ │
│                          ▼                               │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ Step 2: Call addressing-feedback-interactively skill│ │
│ │ • Choose commit strategy                            │ │
│ │ • Present issues summary                            │ │
│ │ • Walk through each issue                           │ │
│ │ • Verify after each fix                             │ │
│ │ • Handle commits per strategy                       │ │
│ └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### Skill Design: `addressing-feedback-interactively`

**Type:** Agent-only skill (invoked by commands, not directly)

**Input:** Unified TOON format from either `getting-feedback-local` or `getting-feedback-remote`:

```toon
build_results:
  status: fail_related | fail_unrelated | all_passed
  ci_commands[N]: {...}
  failures[M]:
    type: test | lint | build | type_check
    location: file:line
    related_to_changes: true | false
    messages[...]: ...

review:
  status: success
  issues[K]:
    severity: critical | warning | suggestion
    code_references[...]:
      file: path/to/file
      line: number
    description: |
      Detailed issue description
```

**Output:** Session completion status (all resolved / partially resolved / user aborted)

**Workflow:**

#### Step 1: Choose Commit Strategy

Ask user once at the beginning:

**How would you like to commit fixes?**
1. **Incremental** - Commit after each fix (recommended for PRs)
   - Creates checkpoint commits
   - Easier to isolate issues
   - CI can validate each step
2. **Accumulated** - Fix all issues, commit once at end (recommended for local)
   - Cleaner history
   - Single comprehensive commit
   - Easy to abort entire session
3. **Manual** - Don't auto-commit, I'll commit manually
   - Full user control
   - Good for complex changes

Store choice for entire session.

#### Step 2: Present Issues Summary

Unified presentation format:

```
## Feedback Summary

Build Results: 2 failures (1 related to your changes, 1 unrelated)
Review Issues: 4 total (1 critical, 2 warnings, 1 suggestion)
Unresolved Threads: 1 (from earlier commits)

## Issues to Address

Priority 1 - Critical (must fix):
  Issue 1: [Critical Review] Null pointer risk in src/api.ts:42
  Issue 2: [Test Failure] tests/api.test.ts:42 (related to changes)

Priority 2 - Warnings (should fix):
  Issue 3: [Warning Review] Missing error handling in src/api.ts:89
  Issue 4: [Lint Error] Unused variable in src/utils.ts:15 (unrelated)

Priority 3 - Suggestions (optional):
  Issue 5: [Suggestion] Consider refactoring validation logic

Priority 4 - Unresolved from earlier:
  Issue 6: [Unresolved] Review thread about error handling (src/auth.ts:15)
```

#### Step 3: Interactive Resolution Loop

For each issue in priority order:

**3.a. Present issue details**
```
Working on Issue 1: [Critical Review] Null pointer risk

Location: src/api.ts:42
Severity: critical
Related to your changes: yes

The user object may be null here. Add null check before accessing properties.

Suggested fix:
```typescript
if (!user) {
  throw new Error('User not found');
}
return user.id;
```
```

**3.b. Investigate and propose fix**
- Read relevant code
- Understand context
- For suggestions: Ask "Address now or defer?"
- Propose specific fix
- Get user approval

**3.c. Implement fix per user direction**

**3.d. Verify fix**

Run verification in subagent:
```markdown
Use Task tool with subagent_type='general-purpose':

"Run local CI to verify changes.
Use getting-build-results-local skill.
Use parsing-build-results skill.

Changed files: [files just modified]

Return TOON with pass/fail status and any new failures."
```

Triage verification results:
- **All passed** → Proceed to commit step
- **New related failures** → Fix before proceeding
- **New unrelated failures** → Note and ask user how to proceed

**3.e. Handle commit based on strategy**

**If Incremental:**
- Commit immediately with clear message
- Format: `fix: [brief description of what was fixed]`
- Reference issue if applicable

**If Accumulated:**
- Mark issue as resolved
- Continue to next issue
- Don't commit yet

**If Manual:**
- Inform user changes are ready
- Don't commit
- Continue to next issue

**3.f. Move to next issue**

#### Step 4: Final Completion

**If Incremental:**
- All fixes committed individually
- Ask: "Push commits to remote? (yes/no)"
- If yes, push all commits

**If Accumulated:**
- Ask: "Commit all fixes now? (yes/commit message/no)"
- If yes, create comprehensive commit with all changes
- Message format: `fix: address feedback - [summary]`

**If Manual:**
- Summarize all changes made
- List modified files
- User commits manually when ready

### Benefits

1. **Single source of truth** - Issue presentation and resolution logic in one place
2. **Consistent UX** - Same prompts, same flow for local and remote
3. **Flexible commit strategy** - User chooses what works for their context
4. **Easier to improve** - Enhance skill once, both commands benefit
5. **Testable** - Can test interaction logic independently
6. **Extensible** - Future commands can reuse same skill

### Commands After Refactoring

Both commands become much simpler:

**pr-address-feedback-local.md:**
```markdown
## 0. Determine Review Context
[unchanged - detect branch vs staged]

## 1. Gather Complete Local Feedback
[unchanged - call getting-feedback-local skill]

## 2. Address Issues Interactively
Use the `addressing-feedback-interactively` skill to guide user through
resolving all issues. The skill handles presentation, interaction,
verification, and commit management.
```

**pr-address-feedback-remote.md:**
```markdown
## 0. Get PR Context
[unchanged - get PR number and commit]

## 1. Gather Complete PR Feedback
[unchanged - call getting-feedback-remote skill]

## 2. Address Issues Interactively
Use the `addressing-feedback-interactively` skill to guide user through
resolving all issues. The skill handles presentation, interaction,
verification, and commit management.
```

### Implementation Plan

**Phase 2.1: Create addressing-feedback-interactively skill**
1. Create `SKILL.md` with complete workflow documentation
2. Include all three commit strategies
3. Include unified issue presentation format
4. Document verification and triage logic

**Phase 2.2: Update commands to use new skill**
1. Simplify `pr-address-feedback-local.md` to use skill
2. Simplify `pr-address-feedback-remote.md` to use skill
3. Remove duplicated Steps 2-4 from both

**Phase 2.3: Test end-to-end**
1. Test local workflow with all three commit strategies
2. Test remote workflow with all three commit strategies
3. Verify consistent UX across both

### Skills Inventory Update

**To Create (1 new skill):**
- `addressing-feedback-interactively` (agent-only)

**To Modify (2 commands):**
- `pr-address-feedback-local.md` (simplify Steps 2-4)
- `pr-address-feedback-remote.md` (simplify Steps 2-4)

### Success Criteria

1. Both commands use same skill for Steps 2-4
2. User gets consistent experience (local vs remote)
3. All three commit strategies work correctly
4. Commands are <50% of current size (delegating to skill)
5. Skill is reusable for future feedback workflows
