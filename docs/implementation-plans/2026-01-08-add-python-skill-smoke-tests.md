# Python Skill Smoke Tests Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add minimal happy-path smoke tests for 4 Python skill scripts to verify basic functionality.

**Architecture:** Create pytest-based tests in `test/skills/` directory that mock external commands (gh, git) and verify TOON output format.
Each script gets one smoke test covering the happy path only.

**Tech Stack:** pytest, pytest-mock, Python 3.x

---

## Task 0: Setup Pytest Infrastructure

**Files:**
- Create: `test/skills/__init__.py`
- Create: `test/skills/conftest.py`
- Create: `pyproject.toml`
- Modify: `.mise.toml`

**Step 1: Create test directory structure**

```bash
mkdir -p test/skills
touch test/skills/__init__.py
```

**Step 2: Create pytest configuration**

Create `test/skills/conftest.py`:

```python
"""Pytest configuration and shared fixtures for skills tests."""
import pytest


@pytest.fixture
def mock_subprocess_run(mocker):
    """Mock subprocess.run for command execution tests."""
    return mocker.patch('subprocess.run')


@pytest.fixture
def mock_git_commands(mock_subprocess_run):
    """Pre-configured mocks for common git commands."""
    def _run(cmd, **kwargs):
        # Default to success
        result = mocker.Mock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""

        # Handle specific commands
        if cmd == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            result.stdout = "feature-branch"
        elif cmd == ["git", "rev-parse", "HEAD"]:
            result.stdout = "abc123def456"
        elif cmd == ["git", "symbolic-ref", "refs/remotes/origin/HEAD"]:
            result.stdout = "refs/remotes/origin/main"

        return result

    mock_subprocess_run.side_effect = _run
    return mock_subprocess_run
```

**Step 3: Create pyproject.toml**

Create `pyproject.toml` in repository root:

```toml
[project]
name = "dotfiles-skills"
version = "0.1.0"
description = "Dotfiles repository with Claude Code skill scripts"
requires-python = ">=3.10"

[project.optional-dependencies]
test = [
    "pytest>=7.0.0",
    "pytest-mock>=3.10.0",
]

[tool.pytest.ini_options]
testpaths = ["test/skills"]
python_files = "test_*.py"
addopts = "-v"
```

**Step 4: Add pytest task to mise.toml**

Add after the existing `[tasks.test]` section in `.mise.toml`:

```toml
[tasks.test-python]
description = "Run Python skill smoke tests"
run = """
echo "Running Python skill smoke tests..."
uv run --extra test pytest
"""

[tasks.test-all]
description = "Run all tests (bash + python)"
run = """
mise run test
mise run test-python
"""
```

**Step 5: Update CI task**

Modify `[tasks.ci]` in `.mise.toml` to include python tests:

```toml
[tasks.ci]
description = "Run complete CI suite (lint + all tests in parallel)"
run = """
mise run lint &
LINT_PID=$!
mise run test-all &
TEST_PID=$!

wait $LINT_PID
LINT_EXIT=$?

wait $TEST_PID
TEST_EXIT=$?

if [ $LINT_EXIT -ne 0 ] || [ $TEST_EXIT -ne 0 ]; then
  echo ""
  echo "❌ CI failed!"
  exit 1
fi

echo ""
echo "✓ All CI checks passed!"
"""
```

**Step 6: Commit infrastructure**

```bash
git add test/skills/__init__.py test/skills/conftest.py pyproject.toml .mise.toml
git commit -m "test: add pytest infrastructure for skill smoke tests"
```

---

## Task 1: Test check_branch_state.py

**Files:**
- Create: `test/skills/test_check_branch_state.py`

**Step 1: Write the failing test**

Create `test/skills/test_check_branch_state.py`:

```python
"""Smoke test for check_branch_state.py script."""
import subprocess
import sys
from pathlib import Path


def test_check_branch_state_happy_path(mocker, tmp_path):
    """Test check_branch_state.py returns valid TOON output in happy path."""
    # Mock subprocess.run to fake git/gh commands
    def mock_run(cmd, **kwargs):
        result = mocker.Mock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""

        # Mock git commands
        if "rev-parse" in cmd and "--abbrev-ref" in cmd:
            result.stdout = "feature-branch\n"
        elif "rev-parse" in cmd and "HEAD" in cmd:
            result.stdout = "abc123def456789\n"
        elif "symbolic-ref" in cmd:
            result.stdout = "refs/remotes/origin/main\n"
        elif "diff" in cmd and "--name-only" in cmd:
            result.stdout = "file1.py\nfile2.py\n"
        elif cmd[:2] == ["gh", "pr"]:
            # Mock PR data
            pr_data = {
                "number": 123,
                "headRefOid": "abc123def456789",
                "url": "https://github.com/owner/repo/pull/123"
            }
            result.stdout = str(pr_data).replace("'", '"')

        return result

    mocker.patch('subprocess.run', side_effect=mock_run)

    # Run the script
    script_path = Path(__file__).parent.parent.parent / \
        "private_dot_claude/skills/getting-branch-state/scripts/executable_check_branch_state.py"

    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True
    )

    # Verify it succeeded and returned TOON-like output
    assert result.returncode == 0
    assert "local:" in result.stdout
    assert "branch:" in result.stdout
    assert "pr:" in result.stdout
```

**Step 2: Run test to verify it fails**

```bash
uv run --extra test pytest test/skills/test_check_branch_state.py
```

Expected output:
```
FAILED test/skills/test_check_branch_state.py::test_check_branch_state_happy_path
```

**Step 3: Fix the test (the script already exists)**

The test should pass because the script is already implemented.
If it fails, debug the mocking to match actual script behavior.

**Step 4: Run test to verify it passes**

```bash
uv run --extra test pytest test/skills/test_check_branch_state.py
```

Expected output:
```
PASSED test/skills/test_check_branch_state.py::test_check_branch_state_happy_path
```

**Step 5: Commit**

```bash
git add test/skills/test_check_branch_state.py
git commit -m "test: add smoke test for check_branch_state.py"
```

---

## Task 2: Test fetch_pr_reviews.py

**Files:**
- Create: `test/skills/test_fetch_pr_reviews.py`

**Step 1: Write the failing test**

Create `test/skills/test_fetch_pr_reviews.py`:

```python
"""Smoke test for fetch_pr_reviews.py script."""
import subprocess
import sys
from pathlib import Path


def test_fetch_pr_reviews_happy_path(mocker):
    """Test fetch_pr_reviews.py returns valid TOON output in happy path."""
    # Mock subprocess.run for gh commands
    def mock_run(cmd, **kwargs):
        result = mocker.Mock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""

        if "pulls" in str(cmd) and "commits" in str(cmd):
            # Mock PR commits
            commits = [{
                "sha": "abc123def",
                "commit": {"committer": {"date": "2026-01-08T20:00:00Z"}}
            }]
            import json
            result.stdout = json.dumps(commits)
        elif "view" in cmd and "comments" in cmd:
            # Mock PR comments (no Claude bot comments)
            result.stdout = '{"comments": []}'
        elif "api" in cmd and "reviews" in cmd:
            # Mock PR reviews (empty)
            result.stdout = '[]'
        elif "repo" in cmd and "view" in cmd:
            # Mock repo info for GraphQL
            result.stdout = '{"owner": {"login": "test"}, "name": "repo"}'
        elif "graphql" in cmd:
            # Mock GraphQL reviewThreads response
            result.stdout = '''{
                "data": {
                    "repository": {
                        "pullRequest": {
                            "reviewThreads": {
                                "pageInfo": {"hasNextPage": false, "endCursor": null},
                                "nodes": []
                            }
                        }
                    }
                }
            }'''

        return result

    mocker.patch('subprocess.run', side_effect=mock_run)

    # Run the script with test args
    script_path = Path(__file__).parent.parent.parent / \
        "private_dot_claude/skills/getting-reviews-remote/scripts/executable_fetch_pr_reviews.py"

    result = subprocess.run(
        [str(script_path), "123", "abc123def"],
        capture_output=True,
        text=True
    )

    # Verify it succeeded and returned TOON output
    assert result.returncode == 0
    assert "status:" in result.stdout
    assert "pr_number:" in result.stdout
    assert "current_commit" in result.stdout
```

**Step 2: Run test to verify it fails**

```bash
uv run --extra test pytest test/skills/test_fetch_pr_reviews.py
```

Expected: FAILED (script not yet tested with mocks)

**Step 3: Adjust mocks if needed**

Debug and adjust the mock responses to match what the script actually expects.

**Step 4: Run test to verify it passes**

```bash
uv run --extra test pytest test/skills/test_fetch_pr_reviews.py
```

Expected: PASSED

**Step 5: Commit**

```bash
git add test/skills/test_fetch_pr_reviews.py
git commit -m "test: add smoke test for fetch_pr_reviews.py"
```

---

## Task 3: Test fetch_workflow_logs.py

**Files:**
- Create: `test/skills/test_fetch_workflow_logs.py`

**Step 1: Write the failing test**

Create `test/skills/test_fetch_workflow_logs.py`:

```python
"""Smoke test for fetch_workflow_logs.py script."""
import subprocess
import sys
from pathlib import Path


def test_fetch_workflow_logs_happy_path(mocker):
    """Test fetch_workflow_logs.py returns valid TOON output in happy path."""
    # Mock subprocess.run for gh api commands
    def mock_run(cmd, **kwargs):
        result = mocker.Mock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""

        if "jobs" in str(cmd):
            # Mock workflow jobs
            jobs = {
                "jobs": [{
                    "id": 123,
                    "name": "Test Job",
                    "conclusion": "failure",
                    "steps": [{
                        "name": "Run tests",
                        "conclusion": "failure",
                        "number": 1
                    }]
                }]
            }
            import json
            result.stdout = json.dumps(jobs)
        elif "logs" in str(cmd):
            # Mock job logs
            result.stdout = "test output\nerror: test failed"

        return result

    mocker.patch('subprocess.run', side_effect=mock_run)

    # Run the script with test run ID
    script_path = Path(__file__).parent.parent.parent / \
        "private_dot_claude/skills/getting-build-results-remote/scripts/executable_fetch_workflow_logs.py"

    result = subprocess.run(
        [str(script_path), "123456"],
        capture_output=True,
        text=True
    )

    # Verify it succeeded and returned TOON output
    assert result.returncode == 0
    assert "status:" in result.stdout
    assert "run_id:" in result.stdout or "workflow" in result.stdout.lower()
```

**Step 2: Run test to verify it fails**

```bash
uv run --extra test pytest test/skills/test_fetch_workflow_logs.py
```

Expected: FAILED

**Step 3: Adjust mocks to match script behavior**

Debug the test to match actual script expectations.

**Step 4: Run test to verify it passes**

```bash
uv run --extra test pytest test/skills/test_fetch_workflow_logs.py
```

Expected: PASSED

**Step 5: Commit**

```bash
git add test/skills/test_fetch_workflow_logs.py
git commit -m "test: add smoke test for fetch_workflow_logs.py"
```

---

## Task 4: Test check_pr_workflows.py

**Files:**
- Create: `test/skills/test_check_pr_workflows.py`

**Step 1: Write the failing test**

Create `test/skills/test_check_pr_workflows.py`:

```python
"""Smoke test for check_pr_workflows.py script."""
import subprocess
import sys
from pathlib import Path


def test_check_pr_workflows_happy_path(mocker):
    """Test check_pr_workflows.py returns valid TOON output in happy path."""
    # Mock subprocess.run for git/gh commands
    def mock_run(cmd, **kwargs):
        result = mocker.Mock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""

        if cmd[:2] == ["git", "rev-parse"] and "HEAD" in cmd:
            result.stdout = "abc123def456"
        elif cmd[:2] == ["git", "log"]:
            result.stdout = ""  # No unpushed commits
        elif cmd[:2] == ["gh", "pr"]:
            if "view" in cmd:
                # Mock PR data
                pr_data = {
                    "number": 123,
                    "headRefOid": "abc123def456",
                    "url": "https://github.com/owner/repo/pull/123"
                }
                import json
                result.stdout = json.dumps(pr_data)
            elif "checks" in cmd:
                # Mock PR checks (all passed)
                checks = [{
                    "name": "CI",
                    "status": "COMPLETED",
                    "conclusion": "SUCCESS",
                    "detailsUrl": "https://github.com/..."
                }]
                import json
                result.stdout = json.dumps(checks)

        return result

    mocker.patch('subprocess.run', side_effect=mock_run)

    # Run the script
    script_path = Path(__file__).parent.parent.parent / \
        "private_dot_claude/skills/awaiting-pr-workflow-results/scripts/executable_check_pr_workflows.py"

    result = subprocess.run(
        [str(script_path)],
        capture_output=True,
        text=True
    )

    # Verify it succeeded and returned TOON output
    assert result.returncode == 0
    assert "status:" in result.stdout
    assert "workflows:" in result.stdout or "checks" in result.stdout.lower()
```

**Step 2: Run test to verify it fails**

```bash
uv run --extra test pytest test/skills/test_check_pr_workflows.py
```

Expected: FAILED

**Step 3: Adjust mocks to match script behavior**

Debug and fix mocks to match actual script.

**Step 4: Run test to verify it passes**

```bash
uv run --extra test pytest test/skills/test_check_pr_workflows.py
```

Expected: PASSED

**Step 5: Commit**

```bash
git add test/skills/test_check_pr_workflows.py
git commit -m "test: add smoke test for check_pr_workflows.py"
```

---

## Task 5: Run Full Test Suite

**Step 1: Run all Python tests**

```bash
mise run test-python
```

Expected output:
```
Running Python skill smoke tests...
test/skills/test_check_branch_state.py::test_check_branch_state_happy_path PASSED
test/skills/test_fetch_pr_reviews.py::test_fetch_pr_reviews_happy_path PASSED
test/skills/test_fetch_workflow_logs.py::test_fetch_workflow_logs_happy_path PASSED
test/skills/test_check_pr_workflows.py::test_check_pr_workflows_happy_path PASSED
```

**Step 2: Run complete CI suite**

```bash
mise run ci
```

Expected: All checks pass (shellcheck + bash tests + python tests)

**Step 3: Update CLAUDE.md with testing documentation**

Add to the "Testing and Quality" section in `CLAUDE.md` after the bash testing section:

```markdown
### Python Skill Testing

**Minimal smoke test coverage:**
- One happy-path test per Python skill script
- Mock external dependencies (gh, git commands) using pytest-mock
- Verify TOON output format

**Test structure:**
- `test/skills/` - Python smoke tests using pytest framework
- `test/skills/conftest.py` - Shared fixtures for mocking

**Running tests:**
```bash
mise run test-python  # Python tests only
mise run test-all     # Bash + Python tests
```

**Note:** Tests focus on happy path only.
The scripts use defensive programming (timeouts, error handling) to handle edge cases in production.
```

**Step 4: Final commit**

```bash
git add CLAUDE.md
git commit -m "docs: add Python skill testing documentation"
```

---

## Verification

After completing all tasks:

1. Run `mise run test-python` - all 4 tests should pass
2. Run `mise run ci` - complete CI should pass (lint + all tests)
3. Verify `test/skills/` contains 4 test files + conftest.py
4. Verify CLAUDE.md documents the Python testing approach

---

## Notes

- These are **smoke tests only** - happy path verification
- Mocks may need adjustment based on actual script behavior
- Scripts use defensive programming, so minimal testing is acceptable
- Future enhancement: add tests for error handling and edge cases
