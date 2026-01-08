# Claude Code Commands

This directory contains custom slash commands for Claude Code that orchestrate PR workflows and
  quality checks.

## Commands Overview

### `/pr-address-feedback-local`
**Description:** Iteratively address local feedback (build + review) before committing or creating PR.

**Skills used:**
- `getting-branch-state` - Determine review scope (uncommitted vs branch_vs_base).
- `getting-feedback-local` - Orchestrate local CI + code review.
- `addressing-feedback-interactively` - Resolve all issues with user approval.

**When to use:** Before committing or creating a PR to ensure code quality.

### `/pr-address-feedback-remote`
**Description:** Iteratively address PR feedback from workflows and reviews until all issues resolved.

**Skills used:**
- `getting-branch-state` - Check local/PR sync status, warn about mismatches.
- `getting-feedback-remote` - Wait for workflows, fetch build results and reviews.
- `addressing-feedback-interactively` - Resolve all issues with user approval.

**When to use:** After creating a PR to address CI failures and review comments.

### `/pr-quality-loop`
**Description:** Monitor and fix CI checks until all pass (iterative loop).

**Skills used:**
- None explicitly (manual workflow orchestration).
- Indirectly uses CI checking and review addressing patterns.

**When to use:** For iterative PR refinement until all quality checks pass.

### `/pr-merge`
**Description:** Squash merge PR and clean up local branch.

**Skills used:**
- None (uses `gh` CLI directly).

**When to use:** After all PR checks pass and ready to merge.

## Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PR Development Workflow                         │
└─────────────────────────────────────────────────────────────────────────┘

  Local Development
  ─────────────────
        │
        │  Make changes
        │
        ▼
  ┌─────────────────────────────────────────┐
  │  /pr-address-feedback-local             │
  │  ────────────────────────────────────   │
  │  • Check branch state                   │
  │  • Run local CI (build/test/lint)       │
  │  • Perform code review                  │
  │  • Address issues interactively         │
  │  • Commit fixes (accumulated strategy)  │
  └─────────────────────────────────────────┘
        │
        │  Create PR (gh pr create)
        │
        ▼
  ┌─────────────────────────────────────────┐
  │  /pr-address-feedback-remote            │
  │  ────────────────────────────────────   │
  │  • Check local/PR sync (warn if needed) │
  │  • Wait for workflows to complete       │
  │  • Fetch build failures                 │
  │  • Fetch review comments                │
  │  • Address issues interactively         │
  │  • Commit fixes (incremental strategy)  │
  │  • Push to PR                           │
  └─────────────────────────────────────────┘
        │
        │  (Optional) Iterative refinement
        │
        ▼
  ┌─────────────────────────────────────────┐
  │  /pr-quality-loop                       │
  │  ────────────────────────────────────   │
  │  Loop until clean:                      │
  │  1. Local quality checks                │
  │  2. Verify acceptance criteria          │
  │  3. CI checks (wait, review, fix)       │
  │  4. Repeat                              │
  └─────────────────────────────────────────┘
        │
        │  All checks passing
        │
        ▼
  ┌─────────────────────────────────────────┐
  │  /pr-merge                              │
  │  ────────────────────────────────────   │
  │  • Squash merge PR (gh pr merge)        │
  │  • Switch to main branch                │
  │  • Pull latest                          │
  │  • Delete feature branch                │
  └─────────────────────────────────────────┘
        │
        ▼
   Merged to main
```

## Skill Dependency Graph

```
Commands and their skill dependencies:

/pr-address-feedback-local ──┬──▶ getting-branch-state
                              │      │
                              │      ├──▶ (git state detection)
                              │      └──▶ (PR state via gh CLI)
                              │
                              ├──▶ getting-feedback-local
                              │      │
                              │      ├──▶ getting-build-results-local
                              │      │      └──▶ parsing-build-results
                              │      │
                              │      └──▶ getting-review-local
                              │
                              └──▶ addressing-feedback-interactively
                                     (Phase 2 unified resolver)


/pr-address-feedback-remote ──┬──▶ getting-branch-state
                               │      (sync status checking)
                               │
                               ├──▶ getting-feedback-remote
                               │      │
                               │      ├──▶ awaiting-pr-workflow-results
                               │      │      └──▶ getting-branch-state
                               │      │
                               │      ├──▶ getting-build-results-remote
                               │      │      └──▶ parsing-build-results
                               │      │
                               │      └──▶ getting-reviews-remote
                               │             └──▶ parsing-review-suggestions
                               │
                               └──▶ addressing-feedback-interactively
                                      (Phase 2 unified resolver)


/pr-quality-loop ─────────────▶ (manual orchestration)

/pr-merge ────────────────────▶ (gh CLI only)
```

## Phase 2 Architecture

Both feedback commands use the Phase 2 unified feedback resolution workflow:

1. **Gather feedback** (in subagent to save context):
   - `getting-feedback-local` or `getting-feedback-remote`.
   - Returns unified TOON summary with all issues.

2. **Address interactively** (in main context):
   - `addressing-feedback-interactively` skill.
   - Presents unified summary.
   - Works through issues with user approval.
   - Verifies fixes after each change.
   - Creates commits based on strategy (accumulated for local, incremental for PR).

## Common Patterns

### Branch State Checking
All commands that interact with git/PR use `getting-branch-state` for:
- Base branch detection (main vs master).
- Uncommitted files tracking.
- PR existence and sync status (ahead/behind/diverged).
- Changed files list for review context.

### Feedback Gathering
Feedback skills run in subagents to prevent token bloat:
- Raw logs (50k+ tokens) never loaded into main context.
- Only structured TOON summaries returned (~2-5k tokens).

### Interactive Resolution
The `addressing-feedback-interactively` skill provides:
- User choice of commit strategy (incremental/accumulated/manual).
- Priority-based issue presentation.
- Per-issue approval and verification.
- Automatic commit creation based on chosen strategy.

## Usage Examples

**Pre-commit quality check:**
```bash
# Make changes
git add .
/pr-address-feedback-local
# Fix issues, commit when clean
```

**Create PR and address feedback:**
```bash
gh pr create
/pr-address-feedback-remote
# Fix issues, push when clean
```

**Iterative PR refinement:**
```bash
/pr-quality-loop
# Runs until all checks pass
```

**Merge when ready:**
```bash
/pr-merge
# Squash merges and cleans up
```

## See Also

- `../skills/` - Individual skill implementations.
- `../skills/getting-branch-state/` - Single source of truth for branch/PR state.
- `../skills/addressing-feedback-interactively/` - Phase 2 unified resolver.
