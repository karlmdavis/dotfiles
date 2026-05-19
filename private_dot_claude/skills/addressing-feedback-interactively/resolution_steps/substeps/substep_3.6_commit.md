# Substep 3.6: Commit Decision

Based on the commit strategy chosen in Resolution Step 1, decide whether to commit now or defer.

## Retrieve Strategy

Recall the commit strategy the user chose in Resolution Step 1:
- **Incremental**: Commit after each fix
- **Accumulated**: Fix all issues, commit once at end
- **Manual**: Don't auto-commit, user will commit manually

## Actions by Strategy

### Incremental Strategy

Create commit immediately for this fix:

```bash
# Stage only the files modified for this fix
git add {files modified for this specific fix}

# Create descriptive commit
git commit -m "$(cat <<'EOF'
Fix {issue type}: {brief description}

{Optional: More details if needed}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

**Commit message guidelines:**
- Issue type: "Test Failure", "Lint Issue", "Critical Review", etc.
- Brief description: One-line summary of what was fixed
- Optional details: Add more context if the fix is complex

**Example:**
```
Fix Test Failure: add null check in api.ts

Prevents TypeError when user object is null.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Code <noreply@anthropic.com>
```

### Accumulated Strategy

Don't commit yet:
- Track that this fix is complete.
- Continue to next issue.
- All fixes will be committed together in Resolution Step 4 (Final Completion).

### Manual Strategy

Don't commit:
- Track that this fix is complete.
- Continue to next issue.
- User will create commits themselves when ready.

## When Done

After handling the commit decision (or deferring it):
- ✅ Substep 3.6 complete.
- ✅ All substeps for this issue are complete.
- Return to Resolution Step 3 for the next issue, or proceed to Resolution Step 4 if all issues are addressed.
