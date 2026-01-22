"""Smoke test for check_pr_workflows.py script."""
import sys
from pathlib import Path
import json
from toon_format import decode

# Test data constants
TEST_BRANCH = "feature-branch"
TEST_COMMIT_SHORT = "abc123d"
TEST_COMMIT_FULL = "abc123def456"
TEST_COMMIT_TIMESTAMP = "2026-01-08T10:00:00-08:00"
TEST_PR_NUMBER = 123
TEST_PR_URL = "https://github.com/owner/repo/pull/123"
TEST_WORKFLOW_NAME = "CI"
TEST_WORKFLOW_URL = "https://github.com/owner/repo/actions/runs/456"
TEST_WORKFLOW_ID = 456
TEST_WORKFLOW_CREATED = "2026-01-08T18:00:00Z"
TEST_WORKFLOW_UPDATED = "2026-01-08T18:05:00Z"


def test_check_pr_workflows_happy_path(mocker):
    """Test check_pr_workflows.py returns valid TOON output in happy path."""
    # Add script to path and import
    script_dir = (
        Path(__file__).parent.parent.parent
        / "private_dot_claude/skills/awaiting-pr-workflow-results/scripts"
    )
    sys.path.insert(0, str(script_dir))

    try:
        import executable_check_pr_workflows as script

        # Mock subprocess.run at module level
        def mock_run(cmd, **kwargs):
            result = mocker.Mock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""

            # Mock getting-branch-state skill call (returns JSON output)
            if str(cmd[0]).endswith("check_branch_state.py"):
                branch_state = {
                    "local": {
                        "branch": TEST_BRANCH,
                        "head": TEST_COMMIT_FULL,
                        "head_short": TEST_COMMIT_SHORT,
                        "timestamp": TEST_COMMIT_TIMESTAMP,
                    },
                    "pr": {
                        "exists": True,
                        "number": TEST_PR_NUMBER,
                        "head": TEST_COMMIT_FULL,
                        "head_short": TEST_COMMIT_SHORT,
                        "url": TEST_PR_URL,
                    },
                    "comparison": {
                        "local_vs_pr": {
                            "status": "synced",
                            "ahead_count": 0,
                            "ahead_commits": [],
                        }
                    }
                }
                result.stdout = json.dumps(branch_state)
            elif "gh" in cmd and "run" in cmd and "list" in cmd:
                # Mock gh run list - Get workflow runs for commit (all complete)
                runs = [{
                    "databaseId": TEST_WORKFLOW_ID,
                    "name": TEST_WORKFLOW_NAME,
                    "status": "completed",
                    "conclusion": "success",
                    "createdAt": TEST_WORKFLOW_CREATED,
                    "updatedAt": TEST_WORKFLOW_UPDATED,
                    "url": TEST_WORKFLOW_URL
                }]
                result.stdout = json.dumps(runs)
            elif "gh" in cmd and "api" in cmd and "artifacts" in cmd:
                # Mock gh api artifacts - Get workflow artifacts (none)
                result.stdout = json.dumps({"artifacts": []})

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
                pass  # Script calls sys.exit(0)

        output = f.getvalue()

        # Parse and validate TOON output
        result = decode(output)  # Will raise if invalid TOON format
        assert result["status"] == "success"
        assert result["recommendation"] == "all_passed"
        assert result["commit_match"] is True

        # Validate local info
        assert result["local"]["branch"] == TEST_BRANCH
        assert result["local"]["commit"] == TEST_COMMIT_SHORT
        assert result["local"]["commit_full"] == TEST_COMMIT_FULL

        # Validate PR info
        assert result["pr"]["number"] == TEST_PR_NUMBER
        assert result["pr"]["commit_full"] == TEST_COMMIT_FULL

        # Validate workflow results
        assert result["workflows"]["complete"] is True
        assert len(result["workflows"]["results"]) == 1

        workflow = result["workflows"]["results"][0]
        assert workflow["name"] == TEST_WORKFLOW_NAME
        assert workflow["status"] == "completed"
        assert workflow["conclusion"] == "success"
        assert workflow["url"] == TEST_WORKFLOW_URL

    finally:
        # Clean up sys.path to prevent test pollution
        sys.path.remove(str(script_dir))
