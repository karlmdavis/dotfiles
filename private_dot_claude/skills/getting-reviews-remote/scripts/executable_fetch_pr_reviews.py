#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "toon-format==0.9.0b1",
# ]
# ///
"""Fetch PR review comments from GitHub.

Fetches:
1. Claude bot review comments (filtered by commit push timestamp)
2. GitHub PR reviews (filtered by commit SHA)
3. Unresolved review threads from earlier commits

Returns TOON-formatted output to stdout.
All errors and status messages go to stderr.

Exit codes:
  0 - Success (reviews fetched)
  1 - Fatal error (gh command failed, invalid input)
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import TypedDict

from toon_format import encode


class CommandError(Exception):
    """Raised when a required command fails."""
    pass


@dataclass
class ClaudeBotComment:
    """Claude bot review comment."""
    link: str
    updated_at: str
    body: str


@dataclass
class GitHubReview:
    """GitHub PR review."""
    reviewer: str
    state: str
    submitted_at: str
    review_link: str
    body: str


@dataclass
class UnresolvedThread:
    """Unresolved review thread from earlier commits."""
    link: str
    reviewer: str
    created_at: str
    body: str
    resolved: bool


class TOONOutput(TypedDict):
    """TOON output structure for type safety."""
    status: str
    pr_number: int
    current_commit: str
    commit_pushed_at: str
    claude_bot_comment: dict | None
    github_reviews: list[dict]
    unresolved_threads: list[dict]


def log_error(message: str) -> None:
    """Log error message to stderr."""
    print(f"ERROR: {message}", file=sys.stderr)


def log_info(message: str) -> None:
    """Log info message to stderr."""
    print(f"INFO: {message}", file=sys.stderr)


def run_cmd(cmd: list[str], error_msg: str) -> str:
    """Run command and return stdout, raising CommandError on failure."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            log_error(f"{error_msg}")
            log_error(f"Command: {' '.join(cmd)}")
            log_error(f"Exit code: {result.returncode}")
            if result.stderr:
                log_error(f"stderr: {result.stderr.strip()}")
            raise CommandError(error_msg)

        return result.stdout.strip()

    except FileNotFoundError as e:
        log_error(f"Command not found: {cmd[0]}")
        log_error(f"Ensure {cmd[0]} is installed and in PATH")
        raise CommandError(f"Command not found: {cmd[0]}") from e
    except Exception as e:
        log_error(f"Unexpected error running command: {e}")
        raise CommandError(f"Unexpected error: {e}") from e


def run_cmd_optional(cmd: list[str]) -> str | None:
    """Run command and return stdout, returning None on failure."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def get_commit_push_timestamp(pr_number: int, commit_sha: str) -> str:
    """Get when commit was pushed to PR (not just created)."""
    log_info(f"Finding push timestamp for commit {commit_sha[:7]}...")

    # Get timeline of commits pushed to PR
    output = run_cmd(
        ["gh", "api", f"/repos/{{owner}}/{{repo}}/pulls/{pr_number}/commits"],
        f"Failed to get PR commits for #{pr_number}"
    )

    try:
        commits = json.loads(output)
        for commit in commits:
            if commit["sha"] == commit_sha:
                # Use commit date from GitHub API (when it was pushed to PR)
                commit_date = commit["commit"]["committer"]["date"]
                log_info(f"Commit pushed at: {commit_date}")
                return commit_date

        # Fallback: use current time if commit not found in PR yet
        log_info(f"Commit {commit_sha[:7]} not found in PR timeline, using current time")
        return datetime.utcnow().isoformat() + "Z"

    except (json.JSONDecodeError, KeyError) as e:
        log_error(f"Failed to parse commit timeline: {e}")
        # Fallback to current time
        return datetime.utcnow().isoformat() + "Z"


def get_claude_bot_comment(pr_number: int, after_timestamp: str) -> ClaudeBotComment | None:
    """Get most recent Claude bot comment after given timestamp."""
    log_info("Fetching Claude bot comments...")

    output = run_cmd(
        ["gh", "pr", "view", str(pr_number), "--json", "comments"],
        f"Failed to get comments for PR #{pr_number}"
    )

    try:
        data = json.loads(output)
        comments = data.get("comments", [])

        # Filter for Claude bot comments
        claude_comments = [
            c for c in comments
            if c.get("author", {}).get("login", "").lower() in [
                "claude", "github-actions[bot]", "claude-code-bot", "anthropic-claude[bot]"
            ]
        ]

        if not claude_comments:
            log_info("No Claude bot comments found")
            return None

        # Filter for comments after timestamp
        after_dt = datetime.fromisoformat(after_timestamp.replace("Z", "+00:00"))
        recent_comments = []
        for comment in claude_comments:
            updated_at = comment.get("updatedAt", comment.get("createdAt", ""))
            comment_dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            if comment_dt >= after_dt:
                recent_comments.append(comment)

        if not recent_comments:
            log_info(f"No Claude bot comments after {after_timestamp}")
            return None

        # Get most recent
        most_recent = max(recent_comments, key=lambda c: c.get("updatedAt", c.get("createdAt", "")))

        return ClaudeBotComment(
            link=most_recent.get("url", ""),
            updated_at=most_recent.get("updatedAt", most_recent.get("createdAt", "")),
            body=most_recent.get("body", "")
        )

    except (json.JSONDecodeError, KeyError) as e:
        log_error(f"Failed to parse Claude bot comments: {e}")
        return None


def get_github_reviews(pr_number: int, commit_sha: str) -> list[GitHubReview]:
    """Get GitHub PR reviews for specific commit."""
    log_info(f"Fetching GitHub reviews for commit {commit_sha[:7]}...")

    output = run_cmd(
        ["gh", "api", f"/repos/{{owner}}/{{repo}}/pulls/{pr_number}/reviews"],
        f"Failed to get reviews for PR #{pr_number}"
    )

    try:
        reviews = json.loads(output)

        # Filter for reviews on this commit
        commit_reviews = [
            r for r in reviews
            if r.get("commit_id") == commit_sha
        ]

        github_reviews: list[GitHubReview] = []
        for review in commit_reviews:
            github_reviews.append(GitHubReview(
                reviewer=review.get("user", {}).get("login", "unknown"),
                state=review.get("state", "").lower(),
                submitted_at=review.get("submitted_at", ""),
                review_link=review.get("html_url", ""),
                body=review.get("body", "")
            ))

        log_info(f"Found {len(github_reviews)} reviews for this commit")
        return github_reviews

    except (json.JSONDecodeError, KeyError) as e:
        log_error(f"Failed to parse GitHub reviews: {e}")
        return []


def get_unresolved_threads(pr_number: int, current_commit: str) -> list[UnresolvedThread]:
    """Get unresolved review threads from earlier commits."""
    log_info("Fetching unresolved review threads...")

    # Use GraphQL to get review threads
    query = """
    query($owner: String!, $repo: String!, $number: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $number) {
          reviewThreads(first: 100) {
            nodes {
              id
              isResolved
              comments(first: 1) {
                nodes {
                  author { login }
                  body
                  createdAt
                  url
                  commit { oid }
                }
              }
            }
          }
        }
      }
    }
    """

    # Get owner/repo from gh
    repo_info = run_cmd(
        ["gh", "repo", "view", "--json", "owner,name"],
        "Failed to get repo info"
    )

    try:
        repo_data = json.loads(repo_info)
        owner = repo_data["owner"]["login"]
        repo = repo_data["name"]
    except (json.JSONDecodeError, KeyError) as e:
        log_error(f"Failed to parse repo info: {e}")
        return []

    # Run GraphQL query
    graphql_cmd = [
        "gh", "api", "graphql",
        "-f", f"query={query}",
        "-F", f"owner={owner}",
        "-F", f"repo={repo}",
        "-F", f"number={pr_number}"
    ]

    output = run_cmd_optional(graphql_cmd)
    if not output:
        log_info("Could not fetch review threads via GraphQL")
        return []

    try:
        data = json.loads(output)
        threads = data.get("data", {}).get("repository", {}).get("pullRequest", {}).get("reviewThreads", {}).get("nodes", [])

        unresolved: list[UnresolvedThread] = []
        for thread in threads:
            # Skip resolved threads
            if thread.get("isResolved", True):
                continue

            comments = thread.get("comments", {}).get("nodes", [])
            if not comments:
                continue

            first_comment = comments[0]
            comment_commit = first_comment.get("commit", {}).get("oid", "")

            # Skip threads on current commit (those are handled by github_reviews)
            if comment_commit == current_commit:
                continue

            unresolved.append(UnresolvedThread(
                link=first_comment.get("url", ""),
                reviewer=first_comment.get("author", {}).get("login", "unknown"),
                created_at=first_comment.get("createdAt", ""),
                body=first_comment.get("body", ""),
                resolved=False
            ))

        log_info(f"Found {len(unresolved)} unresolved threads from earlier commits")
        return unresolved

    except (json.JSONDecodeError, KeyError) as e:
        log_error(f"Failed to parse review threads: {e}")
        return []


def dataclass_to_dict(obj) -> dict:
    """Convert dataclass to dict for TOON serialization."""
    if isinstance(obj, list):
        return [dataclass_to_dict(item) for item in obj]
    elif hasattr(obj, "__dataclass_fields__"):
        return {k: dataclass_to_dict(v) for k, v in obj.__dict__.items()}
    else:
        return obj


def main() -> int:
    """Main entry point."""
    if len(sys.argv) != 3:
        log_error("Usage: fetch_pr_reviews.py <pr_number> <commit_sha>")
        return 1

    try:
        pr_number = int(sys.argv[1])
        commit_sha = sys.argv[2]

        log_info(f"Fetching reviews for PR #{pr_number}, commit {commit_sha[:7]}...")

        # Get commit push timestamp
        commit_pushed_at = get_commit_push_timestamp(pr_number, commit_sha)

        # Fetch all review data
        claude_comment = get_claude_bot_comment(pr_number, commit_pushed_at)
        github_reviews = get_github_reviews(pr_number, commit_sha)
        unresolved = get_unresolved_threads(pr_number, commit_sha)

        result: TOONOutput = {
            "status": "success",
            "pr_number": pr_number,
            "current_commit": commit_sha[:7],
            "commit_pushed_at": commit_pushed_at,
            "claude_bot_comment": dataclass_to_dict(claude_comment) if claude_comment else None,
            "github_reviews": [dataclass_to_dict(r) for r in github_reviews],
            "unresolved_threads": [dataclass_to_dict(t) for t in unresolved],
        }

        # Output TOON to stdout
        print(encode(result))
        return 0

    except ValueError:
        log_error(f"Invalid PR number: {sys.argv[1]}")
        return 1
    except CommandError:
        return 1
    except KeyboardInterrupt:
        log_error("Interrupted by user")
        return 1
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
