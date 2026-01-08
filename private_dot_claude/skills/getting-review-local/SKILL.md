---
name: getting-review-local
description: Get local code review of current changes - uses available review tools or Claude's own analysis to return structured feedback
---

# Getting Review Local

## Overview

Perform local code review of staged or uncommitted changes and return structured feedback.

Core principle: This is an agent-only skill. Uses available review tools or Claude's analysis capabilities.

What it does:
1. Identify changed files (staged or working directory)
2. Run available review tools (if any)
3. Perform own code analysis
4. Return structured review feedback

Output: Review feedback in format compatible with `parsing-review-suggestions` skill

## When to Use

Use when you need:
- Pre-commit code review feedback
- Local quality check before creating PR
- Quick feedback on changes without pushing

When NOT to use:
- Changes already in PR (use `getting-reviews-remote`)
- No changes to review
- Only want automated tests (use `getting-build-results-local`)

## Review Sources

### Option 1: Claude Code Builtin Review

Use Claude Code's builtin `/review` command:

```markdown
Run the builtin review command:

/review

This triggers Claude Code's native code review functionality.
Capture the output and structure into TOON format.
```

### Option 2: External Review Tools

If other review tools are available:

- CodeRabbit CLI
- SonarQube local analysis
- Custom review scripts
- Third-party code review skills

### Option 3: Claude's Own Analysis

If no external tools available, perform analysis:

1. **Get changed files:**
```bash
# Staged changes
git diff --staged --name-only

# Or unstaged changes
git diff --name-only
```

2. **Read changed files:**
Use Read tool to examine each changed file.

3. **Analyze changes:**
Look for:
- Potential bugs (null checks, error handling, edge cases)
- Code quality issues (complexity, duplication, naming)
- Security concerns (input validation, authentication, sensitive data)
- Best practices violations (patterns, conventions)

4. **Structure findings:**
Format as review feedback with:
- Severity (critical, warning, suggestion)
- Code references (file:line)
- Description of issue
- Suggested fix (if applicable)

## Return Format

Return review feedback in TOON format compatible with parsing skill:

```toon
status: success
source: claude_analysis
review_timestamp: 2026-01-04T16:00:00Z

overall_summary: |
  Reviewed 3 changed files. Found 1 critical issue and 2 suggestions.
  Changes are mostly solid, but null pointer risk in src/api.ts needs
  addressing.

issues[3]:
  severity: critical
  code_references[1]:
    file: src/api.ts
    line: 42
  description: |
    **Null pointer risk**

    The user object may be null here. Add null check before accessing
    properties.

    Suggested fix:
    ```typescript
    if (!user) {
      throw new Error('User not found');
    }
    return user.id;
    ```

  severity: warning
  code_references[1]:
    file: src/api.ts
    line: 89
  description: |
    **Missing error handling**

    Database call should have try/catch for better error handling.

  severity: suggestion
  code_references[1]:
    file: src/utils.ts
    line_range: 15-20
  description: |
    **Consider refactoring**

    This validation logic could be extracted into a separate function
    for better reusability.
```

## Analysis Guidelines

When performing own code review:

### Critical Issues (Must Fix)

- **Null pointer/undefined access** without checks
- **Security vulnerabilities** (XSS, SQL injection, etc.)
- **Resource leaks** (unclosed files, connections, etc.)
- **Race conditions** or concurrency bugs
- **Data loss risks** (overwrites without backup, etc.)

### Warnings (Should Fix)

- **Missing error handling** for fallible operations
- **Incorrect error handling** (swallowing errors, etc.)
- **Performance issues** (N+1 queries, unnecessary loops, etc.)
- **Type safety violations** (any types, forced casts, etc.)
- **Incorrect logic** (off-by-one, wrong operators, etc.)

### Suggestions (Nice to Have)

- **Code duplication** that could be extracted
- **Naming improvements** for clarity
- **Simplification opportunities**
- **Better abstractions**
- **Documentation additions**

## Detecting Changed Lines

For precise line-level feedback:

```bash
# Get unified diff
git diff --staged -U0

# Parse to find exact changed lines
# Look for @@ -X,Y +A,B @@ markers
```

Focus review on changed lines, not entire file.

## Integration with Parsing

The output from this skill can be passed directly to `parsing-review-suggestions` if further structuring needed, or used as-is since it's already in compatible format.

## Usage Pattern

This is an agent-only skill. Caller specifies what to review (staged vs unstaged), agent performs review and returns feedback.

**Example caller pattern:**
```markdown
Use Task tool with subagent_type='general-purpose':

"Use the getting-review-local skill to review staged changes.

Changed files:
- src/api.ts
- src/utils.ts
- tests/api.test.ts

Perform code review and return structured feedback in TOON format."
```

## Integration with Other Skills

Used by:
- `getting-feedback-local` - Orchestrates local feedback
- `/quality-triage` command - Pre-PR quality check

**May use:**
- Claude Code builtin `/review` command
- External review tools - If configured

**Output compatible with:**
- `parsing-review-suggestions` - Can parse if needed

## Common Review Patterns

### New Feature

Check for:
- Edge case handling
- Error scenarios
- Input validation
- Test coverage

### Bug Fix

Check for:
- Root cause addressed (not just symptom)
- Similar bugs elsewhere
- Regression tests added

### Refactoring

Check for:
- Behavior preservation
- No new features mixed in
- Test coverage maintained

### Performance Optimization

Check for:
- Benchmarks/profiling justifying change
- No correctness sacrificed
- Edge cases still handled

## Review Scope

**Focus on:**
- Changed code only (don't review entire file)
- Correctness and safety first
- Security implications
- Maintainability

**Don't focus on:**
- Style issues (let linters handle)
- Trivial naming (unless confusing)
- Pre-existing issues in unchanged code

## Special Cases

### Large Changesets

If many files changed:
- Group related changes
- Prioritize high-risk areas (auth, security, data handling)
- Note if review is partial due to size

### Auto-Generated Code

Skip review of auto-generated files:
- Lock files (package-lock.json, Cargo.lock)
- Build artifacts
- Generated migrations

### Test-Only Changes

Focus on:
- Test quality and coverage
- Test clarity and maintainability
- Don't over-critique (tests can be less DRY)

## Quick Reference

| Review Aspect | What to Check |
|---------------|---------------|
| Safety | Null checks, bounds, error handling |
| Security | Input validation, auth, sensitive data |
| Correctness | Logic, edge cases, off-by-one |
| Performance | Algorithms, unnecessary work, caching |
| Maintainability | Naming, structure, documentation |

## Example Detection Patterns

### Null Pointer Risk

```typescript
// ❌ Risk
return user.id;

// ✅ Safe
if (!user) throw new Error('User not found');
return user.id;
```

### Missing Error Handling

```typescript
// ❌ Risk
const data = await db.query(sql);

// ✅ Safe
try {
  const data = await db.query(sql);
} catch (error) {
  logger.error('Query failed:', error);
  throw error;
}
```

### Unvalidated Input

```typescript
// ❌ Risk
app.get('/user/:id', (req, res) => {
  const user = db.getUser(req.params.id);
  res.json(user);
});

// ✅ Safe
app.get('/user/:id', (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id) || id <= 0) {
    return res.status(400).json({ error: 'Invalid ID' });
  }
  const user = db.getUser(id);
  res.json(user);
});
```
