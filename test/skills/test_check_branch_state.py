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
