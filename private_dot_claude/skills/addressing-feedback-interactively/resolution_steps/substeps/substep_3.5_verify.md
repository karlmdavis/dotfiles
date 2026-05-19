# Substep 3.5: Verify Fix

After implementing a fix, verify it works correctly by running local CI and analyzing the results.

## Run Verification in Subagent

Use Task tool with subagent to prevent token bloat from large CI output:

```markdown
Use Task tool with subagent_type='quality-data-extractor':

"Run local CI to verify current state.
Use getting-build-results-local skill to run CI commands.
Use parsing-build-results skill to parse output.

Changed files for relatedness analysis:
{list all files modified in this session}

Return structured TOON with failures and relatedness determination."
```

**Critical Notes:**
- **List ALL files modified in this session** (from Substep 3.4 tracking).
- Local CI runs for the **ENTIRE project**, not just modified files.
  - This catches unexpected interactions between fixes.
  - Takes a bit longer but prevents surprises.

## Triage Verification Results

The subagent returns TOON with `build_results.status` field.
See [Verification Triage](../../supporting/verification_triage.md) for complete details.

**Quick reference:**

### Status: all_passed

- ✅ Fix verified successfully.
- Move to Substep 3.6 (Commit Decision).

### Status: fail_related

- ⚠️ Failures detected in files you modified.
- **Compare to original issue:**

**Same location and error as original?**
- Fix didn't work or didn't fully resolve the issue.
- Loop back to Substep 3.1 (Investigate Root Cause) to try a different approach.
- Explain to user that the previous approach didn't resolve the issue.
- Propose and implement an alternative solution.
- Re-verify by repeating Substep 3.5 from the beginning.

**Different location or different error?**
- Fix likely caused a side effect or regression.
- Loop back to Substep 3.1 treating this as a combined problem: fix the original issue WITHOUT
  causing the new failure.
- Investigate why the fix caused this side effect.
- Propose an alternative approach that avoids the side effect.
- Re-verify by repeating Substep 3.5 from the beginning.

**Note:** Some build failures are intermittent.
If the new failure seems unrelated to your changes (different subsystem, timing-related, etc.), it
  may be coincidental.
Use judgment.

### Status: fail_unrelated

- ⚠️ Pre-existing failures in files you haven't modified.
- Note in summary but continue to Substep 3.6 (your fix is still valid).
- These failures existed before your changes.

## Retry Limit

If verification fails repeatedly:
- After **3 failed verification attempts** on the same fix, stop and ask user:
  - Try different approach (user-suggested).
  - Skip verification for this fix (risky but moves forward).
  - Abort and investigate manually.

## When Done

Once verification passes (all_passed or fail_unrelated):
- ✅ Substep 3.5 complete.
- Proceed to Substep 3.6 (Commit Decision).
