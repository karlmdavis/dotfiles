# Example: Verification Triage

**IMPORTANT:** This example illustrates decision logic and state transitions.
It is NOT a conversation transcript - use the templates in the workflow sections of SKILL.md for actual communication with users.

## Scenario

Demonstrating different verification outcomes

**Issue being fixed:** Add error handling to src/api.ts

## Verification Run 1

- Changed files: src/api.ts
- CI output: All tests pass
- Status: all_passed
- Decision: ✅ Proceed to commit

## Verification Run 2

- Changed files: src/api.ts
- CI output: New failure in tests/api.test.ts:55 - "Expected error to be thrown"
- File analysis: tests/api.test.ts was modified recently (in this session)
- Status: fail_related
- Decision: 🔴 Stop - fix the new test failure before committing
- Action: Update test expectations, re-verify

## Verification Run 3

- Changed files: src/api.ts
- CI output: Failure in tests/legacy.test.ts:200 - "Database timeout"
- File analysis: tests/legacy.test.ts not in modified files list
- Status: fail_unrelated
- Decision: ⚠️ Note pre-existing failure, proceed with commit (fix is still valid)

## Key Decisions

- Verification outcome determines next action
- Relatedness analysis based on modified files list
- Related failures block progress
- Unrelated failures noted but don't block
