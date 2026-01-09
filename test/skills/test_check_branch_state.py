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
