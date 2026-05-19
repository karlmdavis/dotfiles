# Quality Command Refactoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor quality commands to use clearer names, add scope arguments, and standardize terminology.

**Architecture:** Rename commands to clearer names (/quality-triage, /quality-triage-pr), add scope arguments to local command, and standardize all "human partner" references to "user".

**Tech Stack:** Markdown documentation, Python scripts, TOON format data passing

---

## Task 1: Rename and Add Scope Arguments to Local Quality Command

**Files:**
- Rename: `private_dot_claude/commands/pr-address-feedback-local.md` → `private_dot_claude/commands/quality-triage.md`
- Modify: `private_dot_claude/commands/quality-triage.md` (after rename)

**Step 1: Rename the local quality command file**

```bash
git mv private_dot_claude/commands/pr-address-feedback-local.md \
       private_dot_claude/commands/quality-triage.md
```

Expected: File renamed in git staging

**Step 2: Update command header with new name and argument**

In `private_dot_claude/commands/quality-triage.md`:

```markdown
---
description: Gather and triage all local quality issues (build + review) interactively
argument-hint: everything | uncommitted | branch | branch-dirty
---
```

**Step 3: Add scope argument documentation section**

After description, before Step 0, add:

```markdown
## Scope Argument

The `<scope>` argument determines what code to review:

- `everything` - Full project as it appears in working copy (all files, regardless of git state).
- `uncommitted` - Only staged and unstaged changes (what Git calls "working tree changes").
- `branch` - Committed changes on current branch vs base branch (clean branch comparison).
- `branch-dirty` - Current branch + uncommitted changes vs base branch (branch with WIP).

If no argument provided, defaults to `branch-dirty` (most common use case).

## Review Scope Determination

Based on the scope argument:

- `everything` → Review all files in project.
- `uncommitted` → Review files from `local.uncommitted_files` (from getting-branch-state).
- `branch` → Review files from `comparison.branch_vs_base.changed_files` (committed only).
- `branch-dirty` → Review files from `comparison.branch_vs_base.changed_files` + `local.uncommitted_files` (union).
```

**Step 4: Update Step 0 to use scope argument**

Replace current Step 0 with:

```markdown
## 0. Determine Review Context

**0.a.** Parse scope argument from command invocation:
- If argument provided: Use specified scope.
- If no argument: Default to `branch-dirty`.

**0.b.** Run the getting-branch-state skill to get branch info:

```bash
cd ~/.claude/skills/getting-branch-state
scripts/check_branch_state.py
```

Parse the TOON output and store for later use.

**0.c.** Determine file list based on scope:

- If scope is `everything`:
  - Get all tracked files: `git ls-files`
  - Review scope: "full project"

- If scope is `uncommitted`:
  - Use `local.uncommitted_files` from branch state
  - Review scope: "uncommitted changes"

- If scope is `branch`:
  - Use `comparison.branch_vs_base.changed_files` from branch state
  - Review scope: "branch changes"

- If scope is `branch-dirty`:
  - Combine `comparison.branch_vs_base.changed_files` + `local.uncommitted_files` (deduplicated)
  - Review scope: "branch with uncommitted changes"

**0.d.** Pass context to feedback gathering subagent:
- Provide the list of changed files from step 0.c
- Specify the review scope for context
- Pass complete branch state TOON for potential use by parsing skills
```

**Step 5: Update Example Flow to show scope usage**

Update example to show:

```markdown
Step 0: Determine review context
   - Scope argument: branch-dirty (default)
   - Run getting-branch-state skill
   - Local branch: feature-auth
   - Base branch: main
   - Changed files (branch): src/api.ts, tests/api.test.ts
   - Uncommitted files: src/utils.ts
   - Combined scope: src/api.ts, tests/api.test.ts, src/utils.ts
   - Review scope: "branch with uncommitted changes"
```

**Step 6: Commit**

```bash
git add private_dot_claude/commands/quality-triage.md
git commit -m "refactor: rename pr-address-feedback-local to quality-triage with scope args"
```

---

## Task 2: Rename Remote Quality Command

**Files:**
- Rename: `private_dot_claude/commands/pr-address-feedback-remote.md` → `private_dot_claude/commands/quality-triage-pr.md`

**Step 1: Rename the remote quality command file**

```bash
git mv private_dot_claude/commands/pr-address-feedback-remote.md \
       private_dot_claude/commands/quality-triage-pr.md
```

Expected: File renamed in git staging

**Step 2: Update command header**

In `private_dot_claude/commands/quality-triage-pr.md`:

```markdown
---
description: Gather and triage all PR quality issues (workflows + reviews) interactively
---
```

**Step 3: Commit**

```bash
git add private_dot_claude/commands/quality-triage-pr.md
git commit -m "refactor: rename pr-address-feedback-remote to quality-triage-pr"
```

---

## Task 3: Remove Obsolete Quality Loop Command

**Files:**
- Delete: `private_dot_claude/commands/pr-quality-loop.md`

**Step 1: Remove the obsolete file**

```bash
git rm private_dot_claude/commands/pr-quality-loop.md
```

Expected: File deleted and staged

**Step 2: Commit**

```bash
git commit -m "refactor: remove obsolete pr-quality-loop command"
```

---

## Task 4: Update Commands README for New Names

**Files:**
- Modify: `private_dot_claude/commands/README.md`

**Step 1: Update command names in overview section**

Replace:
```markdown
### `/pr-address-feedback-local`
### `/pr-address-feedback-remote`
### `/pr-quality-loop`
```

With:
```markdown
### `/quality-triage <scope>`
### `/quality-triage-pr`
```

Remove the pr-quality-loop section entirely.

**Step 2: Update workflow diagram**

Change command names in ASCII diagram:
- `/pr-address-feedback-local` → `/quality-triage`
- `/pr-address-feedback-remote` → `/quality-triage-pr`
- Remove `/pr-quality-loop` box

**Step 3: Update skill dependency graph**

Change:
```
/pr-address-feedback-local ──┬──▶ getting-branch-state
```

To:
```
/quality-triage <scope> ──┬──▶ getting-branch-state
```

And:
```
/pr-address-feedback-remote ──┬──▶ getting-branch-state
```

To:
```
/quality-triage-pr ──┬──▶ getting-branch-state
```

**Step 4: Update usage examples section**

Change examples to use new command names:
```bash
# Pre-commit quality check
git add .
/quality-triage uncommitted
# Fix issues, commit when clean

# Full branch review before PR
/quality-triage branch
# Fix issues, commit when clean

# Create PR and address feedback
gh pr create
/quality-triage-pr
# Fix issues, push when clean
```

**Step 5: Commit**

```bash
git add private_dot_claude/commands/README.md
git commit -m "docs: update README for renamed commands"
```

---

## Task 5: Change "human partner" to "user" Throughout Skills

**Files:**
- Modify: All SKILL.md files that reference "human partner"
- Modify: Both quality-triage command files

**Step 1: Find all files with "human partner" references**

```bash
cd private_dot_claude
grep -r "human partner" commands/ skills/ | cut -d: -f1 | sort -u
```

**Step 2: Replace "human partner" with "user" in all files**

```bash
# Find and replace in all relevant files
cd private_dot_claude
find commands/ skills/ -name "*.md" -type f -exec sed -i '' 's/human partner/user/g' {} +
```

Expected: All references changed

**Step 3: Verify changes look correct**

```bash
git diff commands/ skills/ | grep -A2 -B2 "user"
```

Review output to ensure replacements are correct.

**Step 4: Commit**

```bash
git add commands/ skills/
git commit -m "refactor: standardize terminology from 'human partner' to 'user'"
```

---

## Task 6: Evaluate passing branch state to parsing-build-results

**Analysis Step: Determine if optimization is worth the complexity**

**Considerations:**

1. **Token usage tradeoff:**
   - Branch state TOON: ~500-1000 tokens
   - Current approach: changed files passed as simple list: ~50-200 tokens
   - Additional cost: 300-800 tokens per parsing-build-results invocation
   - Frequency: Called once per failed workflow

2. **Benefit analysis:**
   - Current: parsing-build-results gets changed files list for relatedness
   - With branch state: Would get ahead/behind status, PR info, base branch
   - **Question:** Does relatedness analysis benefit from PR/sync info?
   - **Answer:** No - it only needs changed file paths for file matching

3. **Complexity cost:**
   - Would need to thread branch state through multiple skills:
     - getting-feedback-remote → getting-build-results-remote → parsing-build-results
     - getting-feedback-local → getting-build-results-local → parsing-build-results
   - Each skill needs updates to accept and pass through the data

**Decision: Skip this optimization**

The parsing-build-results skill only uses changed file paths for relatedness analysis. It doesn't need PR sync status, ahead/behind info, or base branch detection. The current approach of passing a simple file list is more efficient (50-200 tokens vs 500-1000 tokens).

**Step 1: Document decision in this plan**

Decision recorded above - no implementation needed.

**Step 2: No commit needed**

This task is analysis only.

---

## Task 7: Update quality-triage-pr to use new command name in cross-references

**Files:**
- Modify: `private_dot_claude/commands/quality-triage-pr.md`

**Step 1: Update any cross-references to other commands**

Search for references to old command names and update:
- "pr-address-feedback-local" → "quality-triage"
- "pr-address-feedback-remote" → "quality-triage-pr"

**Step 2: Update use case descriptions**

Update any usage examples or recommendations to use new names.

**Step 3: Commit**

```bash
git add private_dot_claude/commands/quality-triage-pr.md
git commit -m "docs: update cross-references in quality-triage-pr"
```

---

## Task 8: Update all skill documentation references to renamed commands

**Files:**
- Modify: All SKILL.md files in skills/ directory

**Step 1: Find all references to old command names**

```bash
cd private_dot_claude/skills
grep -r "pr-address-feedback-local\|pr-address-feedback-remote\|pr-quality-loop" . | cut -d: -f1 | sort -u
```

**Step 2: Update references to new command names**

For each file found:
- "pr-address-feedback-local" → "quality-triage"
- "pr-address-feedback-remote" → "quality-triage-pr"
- Remove references to "pr-quality-loop"

Common locations:
- "Used by:" sections
- "Integration with Commands:" sections
- Example usage sections

**Step 3: Verify all changes**

```bash
git diff skills/
```

Review to ensure all command references updated correctly.

**Step 4: Commit**

```bash
git add skills/
git commit -m "docs: update command references in skill documentation"
```

---

## Task 9: Add formal context field to skills requiring isolation

**Files:**
- Modify: Skills that run in forked/subagent context

**Step 1: Identify skills that need context: fork**

Skills that orchestrate/process large data (must run in isolation):
- `getting-feedback-local` - Orchestrates local CI + review, returns unified TOON
- `getting-feedback-remote` - Waits for workflows, fetches build/review data, returns unified TOON
- `awaiting-pr-workflow-results` - Waits for workflows (up to 20 min), can be long-running
- `getting-build-results-local` - Runs local CI commands, captures output
- `getting-build-results-remote` - Fetches workflow logs from GitHub
- `getting-review-local` - Performs code review, generates feedback
- `getting-reviews-remote` - Fetches PR review comments from GitHub
- `parsing-build-results` - Processes large build logs (50k+ tokens)
- `parsing-review-suggestions` - Processes large review text (20k+ tokens)

Skills that must stay in main context:
- `addressing-feedback-interactively` - Requires user interaction

Skills that can run in either (fast, small output):
- `getting-branch-state` - Quick git/gh commands, small TOON output

**Step 2: Add context field to all isolation skills**

For each of these 9 skills, update the YAML frontmatter:
- `getting-feedback-local/SKILL.md`
- `getting-feedback-remote/SKILL.md`
- `awaiting-pr-workflow-results/SKILL.md`
- `getting-build-results-local/SKILL.md`
- `getting-build-results-remote/SKILL.md`
- `getting-review-local/SKILL.md`
- `getting-reviews-remote/SKILL.md`
- `parsing-build-results/SKILL.md`
- `parsing-review-suggestions/SKILL.md`

Add after the description field:

```yaml
---
name: getting-feedback-local
description: ...
context: fork
---
```

**Step 3: Update documentation to reference context field**

For skills **without** scripts (just Task tool invocation):
- `getting-feedback-local`
- `getting-feedback-remote`
- `getting-build-results-local`
- `getting-review-local`
- `parsing-build-results`
- `parsing-review-suggestions`

Before:
```markdown
## Usage

CRITICAL: Always run in subagent.

Use Task tool with subagent_type='general-purpose'
```

After:
```markdown
## Usage

**Context:** This skill uses `context: fork` to always run in isolated subagent context.

```
Use Task tool with subagent_type='general-purpose'
```
```

For skills **with** scripts that can be called directly:
- `awaiting-pr-workflow-results`
- `getting-build-results-remote`
- `getting-reviews-remote`

Before:
```markdown
## Usage

CRITICAL: Always run in subagent.
```

After:
```markdown
## Usage

**Context:** This skill uses `context: fork` to always run in isolated subagent context.

When invoking via Task tool, the context field ensures automatic isolation.

When invoking script directly via Bash, caller is responsible for running in appropriate context.
```

**Step 4: Verify all frontmatter is valid YAML**

```bash
cd private_dot_claude/skills
for file in */SKILL.md; do
  echo "Checking $file..."
  head -20 "$file" | grep -A10 "^---$" | head -n -1
done
```

Review output to ensure all YAML frontmatter is valid.

**Step 5: Commit**

```bash
git add skills/getting-feedback-local/SKILL.md \
        skills/getting-feedback-remote/SKILL.md \
        skills/awaiting-pr-workflow-results/SKILL.md \
        skills/getting-build-results-local/SKILL.md \
        skills/getting-build-results-remote/SKILL.md \
        skills/getting-review-local/SKILL.md \
        skills/getting-reviews-remote/SKILL.md \
        skills/parsing-build-results/SKILL.md \
        skills/parsing-review-suggestions/SKILL.md
git commit -m "feat: add context:fork to skills requiring isolation"
```

---

## Testing Plan

After all tasks complete:

**Test 1: Verify quality-triage with different scopes**

```bash
# Test each scope argument
/quality-triage everything
/quality-triage uncommitted
/quality-triage branch
/quality-triage branch-dirty
```

Expected: Each should determine correct file scope and run successfully.

**Test 2: Verify quality-triage-pr works**

```bash
# On branch with PR
/quality-triage-pr
```

Expected: Should check branch state, wait for workflows, gather feedback.

**Test 3: Verify no "human partner" references remain**

```bash
cd private_dot_claude
grep -r "human partner" commands/ skills/
```

Expected: No matches found.

**Test 4: Verify context: fork added to isolation skills**

```bash
cd private_dot_claude/skills
grep -l "context: fork" getting-feedback-local/SKILL.md \
                         getting-feedback-remote/SKILL.md \
                         awaiting-pr-workflow-results/SKILL.md \
                         getting-build-results-local/SKILL.md \
                         getting-build-results-remote/SKILL.md \
                         getting-review-local/SKILL.md \
                         getting-reviews-remote/SKILL.md \
                         parsing-build-results/SKILL.md \
                         parsing-review-suggestions/SKILL.md
```

Expected: All 9 files listed (all have context: fork in frontmatter).

**Test 5: Verify all command cross-references updated**

```bash
cd private_dot_claude
grep -r "pr-address-feedback-local\|pr-address-feedback-remote\|pr-quality-loop" commands/ skills/
```

Expected: No matches found (except in commit messages or historical references).

---

## Final Verification Checklist

- [ ] Commands renamed: quality-triage, quality-triage-pr
- [ ] pr-quality-loop removed
- [ ] quality-triage accepts scope arguments (everything/uncommitted/branch/branch-dirty)
- [ ] All "human partner" changed to "user"
- [ ] context: fork added to isolation-requiring skills
- [ ] README.md updated with new names and diagrams
- [ ] All skill docs updated with new command references
- [ ] All tests pass
- [ ] No references to old names remain

---

## Notes

- Git uses "working tree" for uncommitted changes (staged + unstaged), so "uncommitted" is clear enough for our purposes
- Passing branch state to parsing-build-results was evaluated and rejected as unnecessary complexity
- The scope argument defaults to "branch-dirty" (most common use case)
- awaiting-pr-workflow-results internally calls getting-branch-state (current approach works well)
