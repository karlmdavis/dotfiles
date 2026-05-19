# Verification Triage

After implementing a fix, we must verify it works correctly.
This involves running local CI and analyzing the results to determine next steps.

## Running Verification

Use a subagent to run verification (prevents token bloat from large output):

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
- List ALL files modified in this session for accurate relatedness analysis.
- Local CI runs for the ENTIRE project, not just modified files.
  - This catches unexpected interactions between fixes.
  - Takes longer but prevents surprises.

## Triaging Verification Results

The subagent returns TOON with `build_results.status` field.
Triage based on this status:

### Status: all_passed

**Meaning:** All tests and builds passed.

**Action:**
- ✅ Fix verified successfully.
- Move to Resolution Step 3 Substep 6 (Commit Decision).

### Status: fail_related

**Meaning:** Failures detected in files you modified.

**Action:**
- ⚠️ Failures in your changes detected.
- **Compare to original issue:** Review the verification failures and compare to the original
  issue you were fixing.

**Case 1: Same location and error as original**
- **Diagnosis:** Fix didn't work or didn't fully resolve the issue.
- **Action:**
  1. Loop back to Resolution Step 3 Substep 1 (Investigate Root Cause) to try a different
     approach.
  2. Explain to user that the previous approach didn't resolve the issue.
  3. Propose and implement an alternative solution.
  4. Re-verify by repeating all substeps of Resolution Step 3 Substep 5.

**Case 2: Different location or different error**
- **Diagnosis:** Fix likely caused a side effect or regression.
- **Action:**
  1. Loop back to Resolution Step 3 Substep 1 treating this as a combined problem: fix the
     original issue WITHOUT causing the new failure.
  2. Investigate why the fix caused this side effect.
  3. Propose an alternative approach that avoids the side effect.
  4. Re-verify by repeating all substeps of Resolution Step 3 Substep 5.

**Case 3: Possibly intermittent failure**
- **Note:** Some build failures are intermittent.
- If the new failure seems unrelated to your changes (different subsystem, timing-related, etc.),
  it may be coincidental.
- Use judgment - if truly unrelated, treat as `fail_unrelated` (see below).

### Status: fail_unrelated

**Meaning:** Pre-existing failures in files you haven't modified.

**Action:**
- ⚠️ Pre-existing failures detected but unrelated to your changes.
- Note in summary but continue to Resolution Step 3 Substep 6 (your fix is still valid).
- These failures existed before your changes and aren't introduced by your fix.

## Retry Limit

If verification fails repeatedly (same issue, different approaches):
- After **3 failed verification attempts** on the same fix, stop and ask user:
  - Try different approach (user-suggested).
  - Skip verification for this fix (risky but moves forward).
  - Abort and investigate manually.

## Example

See [examples/verification-triage.md](../examples/verification-triage.md) for concrete examples of
  all three verification outcomes and appropriate responses.
