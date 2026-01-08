"""Pytest configuration and shared fixtures for skills tests."""
import pytest


@pytest.fixture
def mock_subprocess_run(mocker):
    """Mock subprocess.run for command execution tests."""
    return mocker.patch('subprocess.run')


@pytest.fixture
def mock_git_commands(mock_subprocess_run, mocker):
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
