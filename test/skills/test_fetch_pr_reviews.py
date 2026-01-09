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
