#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "toon-format==0.9.0b1",
# ]
# ///
"""Fetch PR review discussion data from GitHub.

Usage: find_pr_feedback.py <pr_number> <commit_sha>

Fetches:
1. PR-level comments (from all users)
2. Formal GitHub PR reviews (filtered by commit SHA)
3. Review threads nested under their parent reviews (unresolved and not outdated)

Returns TOON-formatted output to stdout.
All errors and status messages go to stderr.

Exit codes:
  0 - Success (reviews fetched)
  1 - Fatal error (gh command failed, invalid input)

Output Format:
  Returns nested TOON structure with pr_feedback root key containing:
  - pr: Metadata (PR number, URL, commit SHA)
  - reviews: Formal PR reviews with nested threads and comments
  - other_comments: Top-level PR comments (not part of reviews)

  Example output (TOON tabular format):
    pr_feedback:
      pr:
        number: 456
        url: https://github.com/owner/repo/pull/456
        commit: 7a3f9e2c1b8d4e6f0a2b5c8d9e1f3a4b6c7d8e9f

      reviews:
        - url: 'https://github.com/owner/repo/pull/456#pullrequestreview-789'
          fullDatabaseId: '12345678'
          author: teammate-alice
          commit: 7a3f9e2c1b8d4e6f0a2b5c8d9e1f3a4b6c7d8e9f
          createdAt: '2026-02-13T15:00:00Z'
          threads:
            - path: src/api.ts
              startDiffSide: RIGHT
              diffSide: RIGHT
              startLine: 42
              line: 42
              originalStartLine: 42
              originalLine: 42
              isOutdated: false
              isResolved: false
              comments:
                - url: 'https://github.com/.../r123'
                  fullDatabaseId: '99887766'
                  author: teammate-alice
                  createdAt: '2026-02-13T15:05:00Z'
                  diffHunk: '@@ -40,6 +40,7 @@...'
                  path: src/api.ts
                  line: 42
                  startLine: 42
                  originalLine: 42
                  originalStartLine: 42
                  diffSide: RIGHT
                  startDiffSide: RIGHT
                  subjectType: LINE

      other_comments:
        - author: teammate-bob
          items[1]{url,fullDatabaseId,createdAt}:
            https://github.com/owner/repo/pull/456#issuecomment-123,11223344,2026-02-13T14:00:00Z

        - author: claude[bot]
          items[3]{url,fullDatabaseId,createdAt}:
            https://github.com/owner/repo/pull/456#issuecomment-201,55660001,2026-02-13T15:00:00Z
            https://github.com/owner/repo/pull/456#issuecomment-202,55660002,2026-02-13T15:00:18Z
            https://github.com/owner/repo/pull/456#issuecomment-203,55660003,2026-02-13T15:00:35Z
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from typing import TypedDict

from toon_format import encode


class CommandError(Exception):
    """Raised when a required command fails."""
    pass


class ThreadComment(TypedDict):
    """Comment within a review thread."""
    url: str
    fullDatabaseId: str
    author: str
    createdAt: str
    diffHunk: str
    path: str
    line: int | None
    startLine: int | None
    originalLine: int | None
    originalStartLine: int | None
    diffSide: str | None
    startDiffSide: str | None
    subjectType: str


class Thread(TypedDict):
    """Review thread with location metadata and comments."""
    path: str
    startDiffSide: str | None
    diffSide: str | None
    startLine: int | None
    line: int | None
    originalStartLine: int | None
    originalLine: int | None
    isOutdated: bool
    isResolved: bool
    comments: list[ThreadComment]


class Review(TypedDict):
    """Formal PR review with nested threads."""
    url: str
    fullDatabaseId: str
    author: str
    commit: str
    createdAt: str
    threads: list[Thread]


class PR(TypedDict):
    """PR metadata."""
    number: int
    url: str
    commit: str


class CommentItem(TypedDict):
    """Individual comment within a group (or standalone)."""
    url: str
    fullDatabaseId: str
    createdAt: str


class OtherComment(TypedDict):
    """Top-level PR comment, possibly grouping split comments."""
    author: str
    items: list[CommentItem]


class PRFeedback(TypedDict):
    """Complete PR feedback structure."""
    pr: PR
    reviews: list[Review]
    other_comments: list[OtherComment]


class TOONOutput(TypedDict):
    """TOON output structure."""
    pr_feedback: PRFeedback


def log_error(message: str) -> None:
    """Log error message to stderr."""
    print(f"ERROR: {message}", file=sys.stderr)


def log_info(message: str) -> None:
    """Log info message to stderr."""
    print(f"INFO: {message}", file=sys.stderr)


def _parse_timestamp(ts: str) -> datetime:
    """Parse ISO 8601 timestamp, handling trailing Z."""
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def get_commit_pushed_date(
    commit_sha: str, owner: str, repo: str
) -> datetime:
    """Get when commit was pushed to GitHub via GraphQL pushedDate.

    Raises CommandError if the pushed date cannot be determined.
    """
    query = """
    query($owner: String!, $repo: String!, $oid: GitObjectID!) {
      repository(owner: $owner, name: $repo) {
        object(oid: $oid) {
          ... on Commit {
            pushedDate
          }
        }
      }
    }
    """
    output = run_cmd(
        ["gh", "api", "graphql",
         "-f", f"query={query}",
         "-F", f"owner={owner}",
         "-F", f"repo={repo}",
         "-f", f"oid={commit_sha}"],
        "Failed to fetch commit pushed date"
    )
    data = json.loads(output)
    obj = data.get("data", {}).get("repository", {}).get("object")
    if not obj or not obj.get("pushedDate"):
        raise CommandError(
            f"No pushedDate for commit {commit_sha[:7]} "
            "(commit may not be pushed to GitHub yet)"
        )
    return _parse_timestamp(obj["pushedDate"])


def filter_comments_by_timestamp(
    raw_comments: list[dict], cutoff: datetime
) -> list[dict]:
    """Filter comments to only those posted at or after cutoff timestamp.

    Raises ValueError if any comment has an unparseable createdAt timestamp.
    """
    filtered = []
    for comment in raw_comments:
        ts = _parse_timestamp(comment.get("createdAt", ""))
        if ts >= cutoff:
            filtered.append(comment)
    return filtered


def group_comments(raw_comments: list[dict]) -> list[OtherComment]:
    """Group consecutive comments from the same author within 60 seconds.

    Author-agnostic heuristic:
    1. Same author - all parts from same commenter.
    2. Consecutive - no intervening comments from other authors.
    3. Within 60 seconds - gap between consecutive comments < 60s.
    """
    if not raw_comments:
        return []

    # Sort by createdAt to ensure chronological order
    sorted_comments = sorted(raw_comments, key=lambda c: c.get("createdAt", ""))

    groups: list[OtherComment] = []
    current_author: str | None = None
    current_items: list[CommentItem] = []
    last_time: datetime | None = None

    for comment in sorted_comments:
        author = comment.get("author", {}).get("login", "unknown")
        created_at = comment.get("createdAt", "")

        try:
            ts = _parse_timestamp(created_at)
        except (ValueError, TypeError):
            ts = datetime.min.replace(tzinfo=timezone.utc)

        # Start new group when author changes or gap > 60 seconds
        if (
            current_author is not None
            and (
                author != current_author
                or (last_time is not None and (ts - last_time).total_seconds() > 60)
            )
        ):
            groups.append(OtherComment(author=current_author, items=current_items))
            current_items = []

        current_author = author
        last_time = ts
        current_items.append(CommentItem(
            url=comment.get("url", ""),
            fullDatabaseId=comment.get("fullDatabaseId", ""),
            createdAt=created_at,
        ))

    # Flush last group
    if current_author is not None and current_items:
        groups.append(OtherComment(author=current_author, items=current_items))

    # Log grouping stats
    total_comments = len(sorted_comments)
    grouped = sum(1 for g in groups if len(g["items"]) > 1)
    if grouped:
        log_info(
            f"Comment grouping: {total_comments} comments → {len(groups)} groups "
            f"({grouped} merged)"
        )

    return groups


def run_cmd(cmd: list[str], error_msg: str) -> str:
    """Run command and return stdout, raising CommandError on failure."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=60  # Prevent indefinite hangs
        )

        if result.returncode != 0:
            log_error(f"{error_msg}")
            log_error(f"Command: {' '.join(cmd)}")
            log_error(f"Exit code: {result.returncode}")
            if result.stderr:
                log_error(f"stderr: {result.stderr.strip()}")
            raise CommandError(error_msg)

        return result.stdout.strip()

    except subprocess.TimeoutExpired:
        log_error(f"Command timed out after 60s: {' '.join(cmd)}")
        raise CommandError(f"Command timeout: {error_msg}") from None
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
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=60  # Prevent indefinite hangs
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    except Exception:
        return None


def get_pr_and_reviews(pr_number: int, owner: str, repo: str) -> tuple[PR, list[dict], list[Review]]:
    """Get PR metadata, raw comment dicts, and reviews via paginated GraphQL.

    Returns tuple of (pr, raw_comments, reviews) where reviews have empty threads lists.
    Raw comments are untyped dicts for downstream grouping.
    """
    log_info("Fetching PR metadata, comments, and reviews...")

    all_reviews = []
    has_next_page = True
    cursor = None
    page_count = 0
    MAX_PAGES = 50  # Safety limit

    # Store PR metadata and other_comments from first page
    pr_metadata = None
    other_comments = None

    while has_next_page and page_count < MAX_PAGES:
        page_count += 1
        log_info(f"Fetching reviews page {page_count}...")

        query = """
        query($owner: String!, $repo: String!, $number: Int!, $reviewsAfter: String) {
          repository(owner: $owner, name: $repo) {
            pullRequest(number: $number) {
              number
              url
              comments(first: 100) {
                nodes {
                  url
                  fullDatabaseId
                  author { login }
                  createdAt
                }
              }
              reviews(first: 100, after: $reviewsAfter) {
                pageInfo { hasNextPage endCursor }
                nodes {
                  id
                  url
                  fullDatabaseId
                  author { login }
                  commit { oid }
                  createdAt
                }
              }
            }
          }
        }
        """

        graphql_cmd = [
            "gh", "api", "graphql",
            "-f", f"query={query}",
            "-F", f"owner={owner}",
            "-F", f"repo={repo}",
            "-F", f"number={pr_number}"
        ]

        if cursor:
            graphql_cmd.extend(["-f", f"reviewsAfter={cursor}"])

        output = run_cmd(graphql_cmd, "Failed to fetch PR data")

        try:
            data = json.loads(output)
            pr_data = data.get("data", {}).get("repository", {}).get("pullRequest", {})

            # Get PR metadata and other_comments from first page only
            if page_count == 1:
                pr_metadata = PR(
                    number=pr_data.get("number", pr_number),
                    url=pr_data.get("url", ""),
                    commit=""  # Will be set later by caller
                )

                comments_nodes = pr_data.get("comments", {}).get("nodes", [])
                other_comments = list(comments_nodes)

            # Get reviews from this page
            reviews_data = pr_data.get("reviews", {})
            page_info = reviews_data.get("pageInfo", {})
            has_next_page = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")

            reviews_nodes = reviews_data.get("nodes", [])
            all_reviews.extend(reviews_nodes)
            log_info(f"Page {page_count}: Found {len(reviews_nodes)} reviews (total: {len(all_reviews)})")

        except (json.JSONDecodeError, KeyError) as e:
            log_error(f"Failed to parse PR data: {e}")
            raise CommandError("Failed to parse PR data") from e

    if has_next_page and page_count >= MAX_PAGES:
        log_error(f"Hit page limit ({MAX_PAGES}), some reviews may be missing")

    log_info(f"Fetched {len(all_reviews)} total reviews across {page_count} page(s)")

    # Convert raw review nodes to Review TypedDict (with empty threads)
    reviews = [
        Review(
            url=review.get("url", ""),
            fullDatabaseId=review.get("fullDatabaseId", ""),
            author=review.get("author", {}).get("login", "unknown"),
            commit=review.get("commit", {}).get("oid", ""),
            createdAt=review.get("createdAt", ""),
            threads=[]  # Will be populated later
        )
        for review in all_reviews
    ]

    # Also store node IDs for later thread assignment
    for i, review_node in enumerate(all_reviews):
        # Store node ID as a temporary attribute (will use for mapping)
        reviews[i]["_node_id"] = review_node.get("id", "")  # type: ignore

    return pr_metadata, other_comments, reviews  # type: ignore


def get_threads(pr_number: int, owner: str, repo: str) -> list[dict]:
    """Get all review threads with pullRequestReview.id link.

    Returns raw thread data (not yet filtered or assigned to reviews).
    """
    log_info("Fetching review threads...")

    all_threads = []
    has_next_page = True
    cursor = None
    page_count = 0
    MAX_PAGES = 50  # Safety limit

    while has_next_page and page_count < MAX_PAGES:
        page_count += 1
        log_info(f"Fetching review threads page {page_count}...")

        query = """
        query($owner: String!, $repo: String!, $number: Int!, $after: String) {
          repository(owner: $owner, name: $repo) {
            pullRequest(number: $number) {
              reviewThreads(first: 100, after: $after) {
                pageInfo {
                  hasNextPage
                  endCursor
                }
                nodes {
                  path
                  startDiffSide
                  diffSide
                  startLine
                  line
                  originalStartLine
                  originalLine
                  isOutdated
                  isResolved
                  comments(first: 50) {
                    nodes {
                      url
                      fullDatabaseId
                      author { login }
                      createdAt
                      diffHunk
                      path
                      line
                      startLine
                      originalLine
                      originalStartLine
                      diffSide
                      startDiffSide
                      subjectType
                      pullRequestReview { id }
                    }
                  }
                }
              }
            }
          }
        }
        """

        graphql_cmd = [
            "gh", "api", "graphql",
            "-f", f"query={query}",
            "-F", f"owner={owner}",
            "-F", f"repo={repo}",
            "-F", f"number={pr_number}"
        ]

        if cursor:
            graphql_cmd.extend(["-f", f"after={cursor}"])

        output = run_cmd_optional(graphql_cmd)
        if not output:
            log_info("Could not fetch review threads via GraphQL")
            break

        try:
            data = json.loads(output)
            review_threads = data.get("data", {}).get("repository", {}).get("pullRequest", {}).get("reviewThreads", {})

            # Get pagination info
            page_info = review_threads.get("pageInfo", {})
            has_next_page = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")

            # Accumulate threads from this page
            threads = review_threads.get("nodes", [])
            all_threads.extend(threads)
            log_info(f"Page {page_count}: Found {len(threads)} threads (total: {len(all_threads)})")

        except (json.JSONDecodeError, KeyError) as e:
            log_error(f"Failed to parse review threads: {e}")
            break

    if has_next_page and page_count >= MAX_PAGES:
        log_error(f"Hit page limit ({MAX_PAGES}), some review threads may be missing")

    log_info(f"Fetched {len(all_threads)} total review threads across {page_count} page(s)")

    return all_threads


def main() -> int:
    """Main entry point."""
    if len(sys.argv) != 3:
        log_error("Usage: find_pr_feedback.py <pr_number> <commit_sha>")
        return 1

    try:
        pr_number = int(sys.argv[1])
        commit_sha = sys.argv[2]

        log_info(f"Fetching reviews for PR #{pr_number}, commit {commit_sha[:7]}...")

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
            return 1

        # Fetch PR metadata, raw comments, and reviews (with empty threads)
        pr_metadata, raw_comments, reviews = get_pr_and_reviews(pr_number, owner, repo)
        pr_metadata["commit"] = commit_sha  # Set commit SHA

        # Get commit push timestamp and filter comments
        pushed_date = get_commit_pushed_date(commit_sha, owner, repo)
        log_info(f"Commit {commit_sha[:7]} pushed at {pushed_date.isoformat()}")
        pre_filter_count = len(raw_comments)
        raw_comments = filter_comments_by_timestamp(raw_comments, pushed_date)
        log_info(
            f"Comment filtering: {pre_filter_count} total, "
            f"{len(raw_comments)} at or after push"
        )

        # Group consecutive comments from same author within 60s
        other_comments = group_comments(raw_comments)

        # Fetch all threads
        all_threads = get_threads(pr_number, owner, repo)

        # Filter reviews by commit SHA
        commit_reviews = [r for r in reviews if r["commit"] == commit_sha]
        log_info(f"Found {len(commit_reviews)} reviews for commit {commit_sha[:7]}")

        # Build review ID → Review map
        review_map = {r["_node_id"]: r for r in commit_reviews}  # type: ignore

        # Assign threads to their parent reviews
        threads_assigned = 0
        threads_skipped_resolved = 0
        threads_skipped_outdated = 0
        threads_skipped_no_parent = 0

        for thread_raw in all_threads:
            # Skip resolved threads
            if thread_raw.get("isResolved", True):
                threads_skipped_resolved += 1
                continue

            # Skip outdated threads
            if thread_raw.get("isOutdated", True):
                threads_skipped_outdated += 1
                continue

            comments_raw = thread_raw.get("comments", {}).get("nodes", [])
            if not comments_raw:
                continue

            # Get parent review ID from first comment
            first_comment = comments_raw[0]
            parent_review_id = first_comment.get("pullRequestReview", {}).get("id")

            if not parent_review_id or parent_review_id not in review_map:
                threads_skipped_no_parent += 1
                continue

            # Convert thread to Thread TypedDict
            thread = Thread(
                path=thread_raw.get("path", ""),
                startDiffSide=thread_raw.get("startDiffSide"),
                diffSide=thread_raw.get("diffSide"),
                startLine=thread_raw.get("startLine"),
                line=thread_raw.get("line"),
                originalStartLine=thread_raw.get("originalStartLine"),
                originalLine=thread_raw.get("originalLine"),
                isOutdated=thread_raw.get("isOutdated", False),
                isResolved=thread_raw.get("isResolved", False),
                comments=[
                    ThreadComment(
                        url=comment.get("url", ""),
                        fullDatabaseId=comment.get("fullDatabaseId", ""),
                        author=comment.get("author", {}).get("login", "unknown"),
                        createdAt=comment.get("createdAt", ""),
                        diffHunk=comment.get("diffHunk", ""),
                        path=comment.get("path", ""),
                        line=comment.get("line"),
                        startLine=comment.get("startLine"),
                        originalLine=comment.get("originalLine"),
                        originalStartLine=comment.get("originalStartLine"),
                        diffSide=comment.get("diffSide"),
                        startDiffSide=comment.get("startDiffSide"),
                        subjectType=comment.get("subjectType", "LINE")
                    )
                    for comment in comments_raw
                ]
            )

            # Append thread to parent review
            review_map[parent_review_id]["threads"].append(thread)
            threads_assigned += 1

        log_info(f"Thread assignment: {threads_assigned} assigned, "
                 f"{threads_skipped_resolved} resolved, "
                 f"{threads_skipped_outdated} outdated, "
                 f"{threads_skipped_no_parent} no matching parent")

        # Clean up temporary _node_id attributes
        for review in commit_reviews:
            review.pop("_node_id", None)  # type: ignore

        result: TOONOutput = {
            "pr_feedback": {
                "pr": pr_metadata,
                "reviews": commit_reviews,
                "other_comments": other_comments
            }
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
