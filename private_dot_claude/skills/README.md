# Claude Code Skills

This directory contains custom skills for quality triage workflows.

## User-Invocable Skills

These skills can be invoked directly by users via slash commands:

- **quality-triage** - Gather and triage local build/review feedback interactively.
- **quality-triage-pr** - Gather and triage PR workflow/review feedback interactively.

## Orchestrator Skills

These skills coordinate multiple sub-skills to gather and parse feedback:

- **getting-feedback-local** - Orchestrate local CI + review (runs in subagent).
- **getting-feedback-remote** - Orchestrate PR workflows + reviews (runs in subagent).
- **addressing-feedback-interactively** - Guide user through fixing issues.

## Data-Gathering Skills

These skills fetch raw data (build logs, reviews, etc.):

- **awaiting-pr-workflow-results** - Check PR workflow status and wait for completion.
- **getting-branch-state** - Analyze git branch state and PR sync status.
- **getting-build-results-local** - Run local CI commands and return output.
- **getting-build-results-remote** - Fetch GitHub workflow logs.
- **getting-review-local** - Perform local code review.
- **getting-reviews-remote** - Fetch PR review comments from GitHub.

## Parsing Skills

These skills parse raw data into structured TOON format:

- **parsing-build-results** - Parse build/test logs into structured failures.
- **parsing-review-suggestions** - Parse review text into structured issues.

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

Many skills use TOON (Token-Oriented Object Notation) for structured data exchange.
  TOON is similar to JSON/YAML but optimized for LLM consumption with 2-space indents and array
  length/field annotations.

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
