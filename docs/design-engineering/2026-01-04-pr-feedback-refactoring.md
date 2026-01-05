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
