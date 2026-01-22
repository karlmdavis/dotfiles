"""Smoke test for fetch_workflow_logs.py script."""
import sys
from pathlib import Path
import json
from toon_format import decode

# Test data constants
TEST_RUN_ID = 123456
TEST_JOB_ID = 789
TEST_RUN_NAME = "CI"
TEST_JOB_NAME = "Test Job"
TEST_LOG_OUTPUT = "test output\nerror: test failed"


def test_fetch_workflow_logs_happy_path(mocker):
    """Test fetch_workflow_logs.py returns valid TOON output in happy path."""
    # Add script to path and import
    script_dir = (
        Path(__file__).parent.parent.parent
        / "private_dot_claude/skills/getting-build-results-remote/scripts"
    )
    sys.path.insert(0, str(script_dir))

    try:
        import executable_fetch_workflow_logs as script

        # Mock subprocess.run at module level
        def mock_run(cmd, **kwargs):
            result = mocker.Mock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""

            if "view" in str(cmd) and "name,conclusion" in str(cmd):
                # Mock gh run view --json name,conclusion - Get workflow run info
                result.stdout = json.dumps({
                    "name": TEST_RUN_NAME,
                    "conclusion": "failure"
                })
            elif "view" in str(cmd) and "jobs" in str(cmd):
                # Mock gh run view --json jobs - Get workflow jobs
                jobs = {
                    "jobs": [{
                        "databaseId": TEST_JOB_ID,
                        "name": TEST_JOB_NAME,
                        "conclusion": "failure",
                        "steps": [{
                            "name": "Run tests",
                            "conclusion": "failure",
                            "number": 1
                        }]
                    }]
                }
                result.stdout = json.dumps(jobs)
            elif "view" in str(cmd) and "--job" in cmd and "--log" in cmd:
                # Mock gh run view --job --log - Get job logs (only for failed jobs)
                result.stdout = TEST_LOG_OUTPUT

            return result

        # Patch subprocess.run and call main
        mocker.patch.object(script.subprocess, 'run', side_effect=mock_run)

        # Mock sys.argv for script arguments (run ID)
        mocker.patch.object(script.sys, 'argv', ['script.py', str(TEST_RUN_ID)])

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
        assert "1 workflow run" in result["message"]
        assert len(result["workflows"]) == 1

        # Validate workflow structure
        workflow = result["workflows"][0]
        assert workflow["run_id"] == TEST_RUN_ID
        assert workflow["run_name"] == TEST_RUN_NAME
        assert workflow["conclusion"] == "failure"
        assert len(workflow["jobs"]) == 1

        # Validate job structure
        job = workflow["jobs"][0]
        assert job["job_id"] == TEST_JOB_ID
        assert job["job_name"] == TEST_JOB_NAME
        assert job["conclusion"] == "failure"
        assert job["log_content"] == TEST_LOG_OUTPUT

    finally:
        # Clean up sys.path to prevent test pollution
        sys.path.remove(str(script_dir))
