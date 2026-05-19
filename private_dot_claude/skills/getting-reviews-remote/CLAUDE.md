# Agent Skill: `getting-reviews-remote`

## Files

- `README.md`: Feature summary, dependencies, and test location.
- `SKILL.md`: Skill definition (workflow, filtering strategy, usage pattern).
- `scripts/executable_find_pr_feedback.py`: Script implementation.
- `../../test/skills/test_find_pr_feedback.py`: Tests for the script
    (the relative path from the repo root is `test/skills/test_find_pr_feedback.py`).

## Keeping Things in Sync

- When changing script behavior or adding features,
    update the **Features** section in `README.md` to match.
- When changing script behavior,
    update or add tests in `test/skills/test_find_pr_feedback.py`.
