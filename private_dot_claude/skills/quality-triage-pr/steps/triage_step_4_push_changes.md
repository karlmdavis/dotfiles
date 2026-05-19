# Triage Step 4: Push Changes to Remote, Maybe

All issues have been addressed and committed locally.
We will use the process specified below to push those commits to the PR
  so that workflows can run again.

## Process for Pushing Changes to Remote

After all issues are addressed and committed, ask the user once using the AskUserQuestion tool:

```markdown
**Question:** "All issues resolved with {N} commit(s). Push to remote branch?"

**Options:**
1. "Yes, Push Now"
   - Description: "Push commits to PR immediately so workflows can run"
2. "No, I'll Push Manually"
   - Description: "Exit without pushing - you can push when ready"
```

Where `{N}` is the number of commits created in the previous Triage Step 3.

Based on the user's choice from above question, proceed as follows:

1. **Option 1: Yes, Push Now**.
  1. Execute: `git push`
  2. Report success: "✅ Pushed {N} commit(s) to remote. PR workflows will run again shortly."
  3. ✅ We're done! Quality triage complete.
2. **Option 2: No, I'll Push Manually**.
  1. Report: "Skipping push. You can push the changes manually, later, using `git push`."
  2. ✅ We're done! Quality triage complete.
