# Triage Step 3: Address Issues Interactively

We now have complete local feedback.
Let's work through each issue interactively with the user, fixing what needs to be fixed and
  deferring what can wait.

This checklist specifies the Address Issues steps.
Copy this checklist and track your progress through it:

```
Address Issues Progress:
[ ] Address Issues Step 1: Invoke addressing-feedback-interactively Skill
[ ] Address Issues Step 2: Support User Through Issue Resolution
```

## Address Issues Step 1: Invoke addressing-feedback-interactively Skill

Use the Skill tool with the following parameters:
- `skill='addressing-feedback-interactively'`

In your prompt to the skill, pass the complete TOON feedback from Triage Step 2.

The skill will handle:
1. **Commit strategy selection** - Ask user to choose: incremental, accumulated, or manual.
   - For local workflow, any strategy works well.
2. **Issue presentation** - Show unified summary of all issues with priorities.
3. **Interactive resolution** - Work through each issue with user approval.
4. **Verification** - Run tests/checks after each fix.
5. **Commits** - Create commits based on user's chosen strategy.

## Address Issues Step 2: Support User Through Issue Resolution

The addressing-feedback-interactively skill will guide the process, but you should:
1. Monitor progress and answer any user questions.
2. Help interpret error messages or build failures.
3. Clarify issue descriptions if user asks.
4. Support the user's decisions about which issues to address vs defer.

Once all issues are addressed (or deferred):
1. The skill will report how many commits were created.
2. ✅ We're done! Local quality triage complete.
