# Resolution Step 4: Final Completion

Once all issues have been addressed, finalize the workflow based on the commit strategy chosen in
  Resolution Step 1.

## Retrieve Strategy

Recall the commit strategy the user chose in Resolution Step 1:
- **Incremental**: Commit after each fix (already done)
- **Accumulated**: Fix all issues, commit once at end (do now)
- **Manual**: Don't auto-commit (just summarize)

## Actions by Strategy

### Incremental Strategy

All commits were already created during Resolution Step 3 Substep 6.

Simply confirm completion:

```markdown
✅ All {N} issues addressed with {N} commits.

**Commits Created:**
- Fix {issue 1, brief title only}
- Fix {issue 2, brief title only}
- Fix {issue 3, brief title only}
```

### Accumulated Strategy

Create a single commit with all fixes:

```bash
# Stage all modified files
git add {all modified files from the session}

# Create single comprehensive commit
git commit -m "$(cat <<'EOF'
Address feedback: {summary of all fixes}

- Fix {issue 1, brief title only}
- Fix {issue 2, brief title only}
- Fix {issue 3, brief title only}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

**Commit message guidelines:**
- First line: High-level summary (e.g., "Address feedback: resolve test failures and review issues")
- Bullet points: One per issue fixed
- Keep bullets concise (just the brief title, not full details)

**Example:**
```
Address feedback: resolve null pointer issues and improve error handling

- Fix test failure: add null check in api.ts
- Fix critical review: handle edge case in user validation
- Fix warning: improve error messages

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Code <noreply@anthropic.com>
```

Then confirm:

```markdown
✅ All {N} issues addressed in 1 commit.
```

### Manual Strategy

Summarize the changes made and list files for user to commit:

```markdown
✅ All {N} issues have been fixed.

**Issues Addressed:**
- {issue 1, brief title and outcome}
- {issue 2, brief title and outcome}
- {issue 3, brief title and outcome}

**Changed Files:**
- {file1}
- {file2}
- {file3}

The changes are ready for you to commit when you're ready.
```

## When Done

After finalizing based on strategy:
- ✅ Resolution Step 4 complete.
- ✅ All Resolution Steps complete.
- The addressing-feedback-interactively skill is finished.
