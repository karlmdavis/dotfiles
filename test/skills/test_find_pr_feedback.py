"""Smoke test for find_pr_feedback.py script."""
import sys
from pathlib import Path
import json
from toon_format import decode

# Add script to path for direct imports
SCRIPT_DIR = (
    Path(__file__).parent.parent.parent
    / "private_dot_claude/skills/getting-reviews-remote/scripts"
)

# Test data constants
TEST_PR_NUMBER = 123
TEST_COMMIT_SHA = "abc123def"
TEST_REVIEW_NODE_ID = "PR_kwReviewNode123"


def test_find_pr_feedback_happy_path(mocker):
    """Test find_pr_feedback.py returns valid TOON output with nested structure."""
    sys.path.insert(0, str(SCRIPT_DIR))

    try:
        import executable_find_pr_feedback as script

        # Track call count to return different responses
        call_count = {"count": 0}

        # Mock subprocess.run at module level
        def mock_run(cmd, **kwargs):
            result = mocker.Mock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""

            cmd_str = ' '.join(str(arg) for arg in cmd)

            # Check which command this is
            is_repo_view = len(cmd) >= 3 and cmd[1] == "repo" and cmd[2] == "view"
            is_graphql = len(cmd) >= 3 and cmd[1] == "api" and cmd[2] == "graphql"

            if is_repo_view:
                # Mock gh repo view --json owner,name
                result.stdout = '{"owner": {"login": "test"}, "name": "repo"}'
            elif is_graphql:
                # GraphQL calls: (1) PR + reviews, (2) commit pushedDate, (3) threads
                call_count["count"] += 1

                if call_count["count"] == 1:
                    # First call: PR + reviews query
                    result.stdout = json.dumps({
                        "data": {
                            "repository": {
                                "pullRequest": {
                                    "number": TEST_PR_NUMBER,
                                    "url": f"https://github.com/test/repo/pull/{TEST_PR_NUMBER}",
                                    "comments": {
                                        "nodes": []
                                    },
                                    "reviews": {
                                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                                        "nodes": []
                                    }
                                }
                            }
                        }
                    })
                elif call_count["count"] == 2:
                    # Second call: commit pushedDate query
                    result.stdout = json.dumps({
                        "data": {
                            "repository": {
                                "object": {
                                    "pushedDate": "2026-02-13T12:00:00Z"
                                }
                            }
                        }
                    })
                else:
                    # Third call: threads query
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
        assert "pr_feedback" in result

        pr_feedback = result["pr_feedback"]

        # Validate PR metadata
        assert pr_feedback["pr"]["number"] == TEST_PR_NUMBER
        assert pr_feedback["pr"]["commit"] == TEST_COMMIT_SHA
        assert "github.com" in pr_feedback["pr"]["url"]

        # Validate structure (empty for this happy path test)
        assert pr_feedback["reviews"] == []
        assert pr_feedback["other_comments"] == []

    finally:
        # Clean up sys.path to prevent test pollution
        sys.path.remove(str(SCRIPT_DIR))


# --- group_comments() unit tests ---


def _make_comment(author: str, created_at: str, url: str = "", db_id: str = "") -> dict:
    """Helper to create a raw comment dict matching GraphQL node shape."""
    return {
        "url": url or f"https://github.com/test/repo/pull/1#issuecomment-{db_id}",
        "fullDatabaseId": db_id,
        "author": {"login": author},
        "createdAt": created_at,
    }


def _import_script():
    """Import the script module, managing sys.path."""
    sys.path.insert(0, str(SCRIPT_DIR))
    import executable_find_pr_feedback as script
    return script


def test_group_comments_single_comment():
    """Single comment produces one group with one item."""
    script = _import_script()
    try:
        raw = [_make_comment("alice", "2026-02-13T14:00:00Z", db_id="100")]
        groups = script.group_comments(raw)
        assert len(groups) == 1
        assert groups[0]["author"] == "alice"
        assert len(groups[0]["items"]) == 1
        assert groups[0]["items"][0]["fullDatabaseId"] == "100"
    finally:
        sys.path.remove(str(SCRIPT_DIR))


def test_group_comments_same_author_within_60s():
    """Consecutive comments from same author within 60s are grouped."""
    script = _import_script()
    try:
        raw = [
            _make_comment("claude[bot]", "2026-02-13T15:00:00Z", db_id="201"),
            _make_comment("claude[bot]", "2026-02-13T15:00:18Z", db_id="202"),
            _make_comment("claude[bot]", "2026-02-13T15:00:35Z", db_id="203"),
        ]
        groups = script.group_comments(raw)
        assert len(groups) == 1
        assert groups[0]["author"] == "claude[bot]"
        assert len(groups[0]["items"]) == 3
        assert [i["fullDatabaseId"] for i in groups[0]["items"]] == ["201", "202", "203"]
    finally:
        sys.path.remove(str(SCRIPT_DIR))


def test_group_comments_same_author_gap_over_60s():
    """Same author with >60s gap produces separate groups."""
    script = _import_script()
    try:
        raw = [
            _make_comment("alice", "2026-02-13T14:00:00Z", db_id="100"),
            _make_comment("alice", "2026-02-13T14:02:00Z", db_id="101"),
        ]
        groups = script.group_comments(raw)
        assert len(groups) == 2
        assert groups[0]["author"] == "alice"
        assert groups[1]["author"] == "alice"
        assert len(groups[0]["items"]) == 1
        assert len(groups[1]["items"]) == 1
    finally:
        sys.path.remove(str(SCRIPT_DIR))


def test_group_comments_different_author_breaks_group():
    """Intervening comment from different author breaks the group."""
    script = _import_script()
    try:
        raw = [
            _make_comment("claude[bot]", "2026-02-13T15:00:00Z", db_id="201"),
            _make_comment("claude[bot]", "2026-02-13T15:00:18Z", db_id="202"),
            _make_comment("alice", "2026-02-13T15:00:25Z", db_id="300"),
            _make_comment("claude[bot]", "2026-02-13T15:00:35Z", db_id="203"),
        ]
        groups = script.group_comments(raw)
        assert len(groups) == 3
        assert groups[0]["author"] == "claude[bot]"
        assert len(groups[0]["items"]) == 2
        assert groups[1]["author"] == "alice"
        assert len(groups[1]["items"]) == 1
        assert groups[2]["author"] == "claude[bot]"
        assert len(groups[2]["items"]) == 1
    finally:
        sys.path.remove(str(SCRIPT_DIR))


# --- filter_comments_by_timestamp() unit tests ---


def test_filter_comments_by_timestamp():
    """Comments before cutoff are excluded, at-or-after are kept."""
    from datetime import datetime, timezone

    script = _import_script()
    try:
        cutoff = datetime(2026, 2, 13, 14, 0, 0, tzinfo=timezone.utc)
        raw = [
            _make_comment("alice", "2026-02-13T13:00:00Z", db_id="1"),  # before
            _make_comment("bob", "2026-02-13T14:00:00Z", db_id="2"),  # at cutoff
            _make_comment("carol", "2026-02-13T15:00:00Z", db_id="3"),  # after
        ]
        result = script.filter_comments_by_timestamp(raw, cutoff)
        assert len(result) == 2
        assert result[0]["fullDatabaseId"] == "2"
        assert result[1]["fullDatabaseId"] == "3"
    finally:
        sys.path.remove(str(SCRIPT_DIR))


def test_filter_comments_bad_timestamp_raises():
    """Unparseable createdAt raises ValueError."""
    from datetime import datetime, timezone
    import pytest

    script = _import_script()
    try:
        cutoff = datetime(2026, 2, 13, 14, 0, 0, tzinfo=timezone.utc)
        raw = [_make_comment("alice", "not-a-timestamp", db_id="1")]
        with pytest.raises(ValueError):
            script.filter_comments_by_timestamp(raw, cutoff)
    finally:
        sys.path.remove(str(SCRIPT_DIR))
