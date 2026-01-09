"""Smoke test for fetch_pr_reviews.py script."""
import sys
from pathlib import Path
import json
from toon_format import decode

# Test data constants
TEST_PR_NUMBER = 123
TEST_COMMIT_SHA = "abc123def"
TEST_COMMIT_PUSH_TIME = "2026-01-08T20:00:00Z"


def test_fetch_pr_reviews_happy_path(mocker):
    """Test fetch_pr_reviews.py returns valid TOON output in happy path."""
    # Add script to path and import
    script_dir = (
        Path(__file__).parent.parent.parent
        / "private_dot_claude/skills/getting-reviews-remote/scripts"
    )
    sys.path.insert(0, str(script_dir))

    try:
        import executable_fetch_pr_reviews as script

        # Mock subprocess.run at module level
        def mock_run(cmd, **kwargs):
            result = mocker.Mock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""

            if "pulls" in str(cmd) and "commits" in str(cmd):
                # Mock gh pr view --json commits - Get PR commit history
                commits = [{
                    "sha": TEST_COMMIT_SHA,
                    "commit": {"committer": {"date": TEST_COMMIT_PUSH_TIME}}
                }]
                result.stdout = json.dumps(commits)
            elif "view" in str(cmd) and "comments" in str(cmd):
                # Mock gh pr view --comments --json - Get PR comments (no Claude bot)
                result.stdout = '{"comments": []}'
            elif "api" in str(cmd) and "reviews" in str(cmd):
                # Mock gh api pulls/reviews - Get GitHub PR reviews (empty)
                result.stdout = '[]'
            elif "repo" in str(cmd) and "view" in str(cmd):
                # Mock gh repo view --json - Get repo info for GraphQL query
                result.stdout = '{"owner": {"login": "test"}, "name": "repo"}'
            elif "graphql" in str(cmd):
                # Mock gh api graphql - Get unresolved review threads (none)
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

        # Mock sys.argv for script arguments (PR number and commit SHA)
        mocker.patch.object(
            script.sys,
            'argv',
            ['script.py', str(TEST_PR_NUMBER), TEST_COMMIT_SHA]
        )

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
        assert result["pr_number"] == TEST_PR_NUMBER
        assert result["current_commit_full"] == TEST_COMMIT_SHA
        assert result["claude_bot_comment"] is None
        assert result["github_reviews"] == []
        assert result["unresolved_threads"] == []

    finally:
        # Clean up sys.path to prevent test pollution
        sys.path.remove(str(script_dir))
