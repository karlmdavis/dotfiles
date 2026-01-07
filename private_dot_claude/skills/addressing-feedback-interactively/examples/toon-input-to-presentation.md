# Example: TOON Input to Presentation Format

**Purpose:** Shows how to transform TOON feedback into Step 2 presentation summary.

## Input TOON

```toon
source: local
build_results:
  status: fail_related
  failures[2]:
    type: test
    location: tests/api.test.ts:42
    related_to_changes: true
    messages[1]: "TypeError: Cannot read property 'id' of null"

    type: lint
    location: tests/legacy.test.ts:200
    related_to_changes: false
    messages[1]: "Database timeout"

review:
  status: success
  issues[2]:
    severity: warning
    code_references[1]:
      file: src/api.ts
      line: 42
    description: "Null pointer risk - user object may be null"

    severity: suggestion
    code_references[1]:
      file: src/utils.ts
      line_range: 15-20
    description: "Consider extracting validation logic"
```

## Step 2 Presentation Output

```markdown
**Build and Review Feedback Summary**

**Build Results:** fail_related (1 related failure, 1 unrelated)
**Review Results:** 2 issues found (1 warning, 1 suggestion)

**2 Total Items To Consider Addressing**
- Priority 1: 1 Build Failure and Warning Issue (aligned)
- Priority 2: 0 Warnings
- Priority 3: 1 Suggestion

**Notes**
- 1 pre-existing build failure unrelated to your changes.
- The following issues are likely aligned with each other and will be presented together:
  - [Priority 1] src/api.ts:42 — Incorrect handling of null user object:
    - [Priority 1] [Test Failure] tests/api.test.ts:42 - TypeError: Cannot read property 'id' of null
    - [Priority 2] [Warning Review] src/api.ts:42 - Null pointer risk

**Issue List**
1. [Priority 1] [Test Failure and Warning Review] src/api.ts:42 - Null pointer issue
2. [Priority 3] [Suggestion] src/utils.ts:15-20 - Consider extracting validation logic

Let's work through these in order.
```

## Key Transformations

1. **Priority Assignment:**
   - Test (related=true) → Priority 1
   - Review (warning) → Priority 2
   - Review (suggestion) → Priority 3
2. **Alignment Detection:** Test failure at :42 + Review at :42 → Grouped as single aligned issue
3. **Unrelated Handling:** Test (related=false) → Noted but not in issue list
4. **Count Calculation:** 2 items total (1 aligned group + 1 suggestion)
