# Python Skill Smoke Tests Implementation Plan (UPDATED)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add minimal happy-path smoke tests for 4 Python skill scripts to verify basic functionality.

**Architecture:** Create pytest-based tests in `test/skills/` directory.
Each script gets one smoke test covering the happy path only.
- **For check_branch_state.py**: Integration test with real git repository
- **For gh-based scripts**: Import module and mock subprocess at module level

**Tech Stack:** pytest, pytest-mock (for gh scripts only), Python 3.x

---

## Task 0: Setup Pytest Infrastructure

**Files:**
- Create: `test/skills/__init__.py`
- Create: `pyproject.toml`
- Modify: `.mise.toml`

**Step 1: Create test directory structure**

```bash
mkdir -p test/skills
touch test/skills/__init__.py
```

**Step 2: Create pyproject.toml**

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

**Step 3: Add pytest task to mise.toml**

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

**Step 4: Update CI task**

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

**Step 5: Commit infrastructure**

```bash
git add test/skills/__init__.py pyproject.toml .mise.toml
git commit -m "test: add pytest infrastructure for skill smoke tests"
```

---

## Task 1: Test check_branch_state.py

**Files:**
- Create: `test/skills/test_check_branch_state.py`

**Step 1: Write the test**

Create `test/skills/test_check_branch_state.py`:

```python
"""Smoke test for check_branch_state.py script."""
import subprocess
import sys
from pathlib import Path


def test_check_branch_state_happy_path(tmp_path):
    """Test check_branch_state.py returns valid TOON output in happy path."""
    # Create a real git repository for testing
    repo = tmp_path / "test_repo"
    repo.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True
    )

    # Create initial commit on main branch
    test_file = repo / "test.txt"
    test_file.write_text("initial content\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo,
        check=True,
        capture_output=True
    )

    # Rename to main branch
    subprocess.run(
        ["git", "branch", "-m", "main"],
        cwd=repo,
        check=True,
        capture_output=True
    )

    # Create and checkout feature branch
    subprocess.run(
        ["git", "checkout", "-b", "feature-branch"],
        cwd=repo,
        check=True,
        capture_output=True
    )

    # Make a change
    test_file.write_text("modified content\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Feature work"],
        cwd=repo,
        check=True,
        capture_output=True
    )

    # Run the script in the test repository
    script_path = (
        Path(__file__).parent.parent.parent
        / "private_dot_claude/skills/getting-branch-state/scripts"
        / "executable_check_branch_state.py"
    )

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=repo,
        capture_output=True,
        text=True
    )

    # Verify it succeeded and returned TOON-like output
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    assert "local:" in result.stdout
    assert "branch: feature-branch" in result.stdout
    assert "pr:" in result.stdout
```

**Step 2: Run test to verify it passes**

```bash
uv run --extra test pytest test/skills/test_check_branch_state.py
```

Expected: PASSED

**Step 3: Commit**

```bash
git add test/skills/test_check_branch_state.py
git commit -m "test: add smoke test for check_branch_state.py"
```

---

## Task 2: Test fetch_pr_reviews.py

**Files:**
- Create: `test/skills/test_fetch_pr_reviews.py`

**Step 1: Write the test**

Create `test/skills/test_fetch_pr_reviews.py`:

```python
"""Smoke test for fetch_pr_reviews.py script."""
import sys
from pathlib import Path
import json


def test_fetch_pr_reviews_happy_path(mocker):
    """Test fetch_pr_reviews.py returns valid TOON output in happy path."""
    # Add script to path and import
    script_dir = (
        Path(__file__).parent.parent.parent
        / "private_dot_claude/skills/getting-reviews-remote/scripts"
    )
    sys.path.insert(0, str(script_dir))

    import executable_fetch_pr_reviews as script

    # Mock subprocess.run at module level
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
            result.stdout = json.dumps(commits)
        elif "view" in str(cmd) and "comments" in str(cmd):
            # Mock PR comments (no Claude bot comments)
            result.stdout = '{"comments": []}'
        elif "api" in str(cmd) and "reviews" in str(cmd):
            # Mock PR reviews (empty)
            result.stdout = '[]'
        elif "repo" in str(cmd) and "view" in str(cmd):
            # Mock repo info for GraphQL
            result.stdout = '{"owner": {"login": "test"}, "name": "repo"}'
        elif "graphql" in str(cmd):
            # Mock GraphQL reviewThreads response
            result.stdout = json.dumps({
                "data": {
                    "repository": {
                        "pullRequest": {
                            "reviewThreads": {
                                "pageInfo": {"hasNextPage": False, "endCursor": None},
                                "nodes": []
                            }
                        }
                    }
                }
            })

        return result

    # Patch subprocess.run and call main
    mocker.patch.object(script.subprocess, 'run', side_effect=mock_run)

    # Mock sys.argv for script arguments
    mocker.patch.object(script.sys, 'argv', ['script.py', '123', 'abc123def'])

    # Capture stdout
    import io
    from contextlib import redirect_stdout

    f = io.StringIO()
    with redirect_stdout(f):
        try:
            script.main()
        except SystemExit:
            pass  # Script calls sys.exit(0)

    output = f.getvalue()

    # Verify TOON output
    assert "status:" in output
    assert "pr_number:" in output
    assert "current_commit" in output
```

**Step 2: Run test to verify it passes**

```bash
uv run --extra test pytest test/skills/test_fetch_pr_reviews.py
```

Expected: PASSED

**Step 3: Commit**

```bash
git add test/skills/test_fetch_pr_reviews.py
git commit -m "test: add smoke test for fetch_pr_reviews.py"
```

---

## Task 3: Test fetch_workflow_logs.py

**Files:**
- Create: `test/skills/test_fetch_workflow_logs.py`

**Step 1: Write the test**

Create `test/skills/test_fetch_workflow_logs.py`:

```python
"""Smoke test for fetch_workflow_logs.py script."""
import sys
from pathlib import Path
import json


def test_fetch_workflow_logs_happy_path(mocker):
    """Test fetch_workflow_logs.py returns valid TOON output in happy path."""
    # Add script to path and import
    script_dir = (
        Path(__file__).parent.parent.parent
        / "private_dot_claude/skills/getting-build-results-remote/scripts"
    )
    sys.path.insert(0, str(script_dir))

    import executable_fetch_workflow_logs as script

    # Mock subprocess.run at module level
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
            result.stdout = json.dumps(jobs)
        elif "logs" in str(cmd):
            # Mock job logs
            result.stdout = "test output\nerror: test failed"

        return result

    # Patch subprocess.run and call main
    mocker.patch.object(script.subprocess, 'run', side_effect=mock_run)

    # Mock sys.argv for script arguments
    mocker.patch.object(script.sys, 'argv', ['script.py', '123456'])

    # Capture stdout
    import io
    from contextlib import redirect_stdout

    f = io.StringIO()
    with redirect_stdout(f):
        try:
            script.main()
        except SystemExit:
            pass

    output = f.getvalue()

    # Verify TOON output
    assert "status:" in output
    assert "run_id:" in output or "workflow" in output.lower()
```

**Step 2: Run test to verify it passes**

```bash
uv run --extra test pytest test/skills/test_fetch_workflow_logs.py
```

Expected: PASSED

**Step 3: Commit**

```bash
git add test/skills/test_fetch_workflow_logs.py
git commit -m "test: add smoke test for fetch_workflow_logs.py"
```

---

## Task 4: Test check_pr_workflows.py

**Files:**
- Create: `test/skills/test_check_pr_workflows.py`

**Step 1: Write the test**

Create `test/skills/test_check_pr_workflows.py`:

```python
"""Smoke test for check_pr_workflows.py script."""
import sys
from pathlib import Path
import json


def test_check_pr_workflows_happy_path(mocker):
    """Test check_pr_workflows.py returns valid TOON output in happy path."""
    # Add script to path and import
    script_dir = (
        Path(__file__).parent.parent.parent
        / "private_dot_claude/skills/awaiting-pr-workflow-results/scripts"
    )
    sys.path.insert(0, str(script_dir))

    import executable_check_pr_workflows as script

    # Mock subprocess.run at module level
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
                result.stdout = json.dumps(pr_data)
            elif "checks" in cmd:
                # Mock PR checks (all passed)
                checks = [{
                    "name": "CI",
                    "status": "COMPLETED",
                    "conclusion": "SUCCESS",
                    "detailsUrl": "https://github.com/..."
                }]
                result.stdout = json.dumps(checks)

        return result

    # Patch subprocess.run and call main
    mocker.patch.object(script.subprocess, 'run', side_effect=mock_run)

    # Capture stdout
    import io
    from contextlib import redirect_stdout

    f = io.StringIO()
    with redirect_stdout(f):
        try:
            script.main()
        except SystemExit:
            pass

    output = f.getvalue()

    # Verify TOON output
    assert "status:" in output
    assert "workflows:" in output or "checks" in output.lower()
```

**Step 2: Run test to verify it passes**

```bash
uv run --extra test pytest test/skills/test_check_pr_workflows.py
```

Expected: PASSED

**Step 3: Commit**

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

Add to the "Testing and Quality" section in `CLAUDE.md` after the bash testing section (around line 213):

```markdown
### Python Skill Testing

**Minimal smoke test coverage:**
- One happy-path test per Python skill script
- Integration test approach for git-based scripts (real git repository)
- Module import and mocking for gh-based scripts
- Verify TOON output format

**Test structure:**
- `test/skills/` - Python smoke tests using pytest framework
- Integration tests use `tmp_path` for isolated git repositories
- Mock-based tests import scripts as modules and patch subprocess at module level

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
3. Verify `test/skills/` contains 4 test files
4. Verify CLAUDE.md documents the Python testing approach

---

## Notes

- **check_branch_state.py**: Integration test with real git repo (fast, authentic)
- **gh-based scripts**: Import module and mock subprocess (avoids GitHub API dependency)
- Scripts use defensive programming, so minimal testing is acceptable
- Future enhancement: add tests for error handling and edge cases

## Key Design Decision: Hybrid Testing Approach

**Why not use subprocess mocking for all tests?**
Mocking `subprocess.run` globally and then using `subprocess.run` to launch the script doesn't work - the mock intercepts the launch call, preventing the script from running.

**Solution:**
- **Git scripts**: Integration tests with real git repos in `tmp_path`
- **GitHub scripts**: Import as module, mock subprocess at module level
