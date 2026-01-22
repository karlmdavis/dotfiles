#!/usr/bin/env python3
"""
Check branch state: local, PR, and their sync status.

Returns TOON with:
- Local branch info (branch, head, base_branch, uncommitted_files)
- PR info (exists, number, head, url)
- Comparison (local_vs_pr status, branch_vs_base changed_files)

Supports --format json for machine-readable output.
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone


# Simple TOON encoder
def encode(data, indent=0):
    """Encode data to TOON format."""
    lines = []
    prefix = "  " * indent

    if isinstance(data, dict):
        for key, value in data.items():
            if value is None:
                continue
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.append(encode(value, indent + 1))
            else:
                lines.append(f"{prefix}{key}: {value}")
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, dict):
                lines.append(encode(item, indent))
            elif isinstance(item, str) and "\n" in item:
                lines.append(f"{prefix}|")
                for line in item.split("\n"):
                    lines.append(f"{prefix}  {line}")
            else:
                lines.append(f"{prefix}{item}")

    return "\n".join(lines)


@dataclass
class LocalState:
    branch: str
    head: str
    head_short: str
    timestamp: str
    base_branch: str
    uncommitted_files: list


@dataclass
class PRState:
    exists: bool
    number: int = None
    head: str = None
    head_short: str = None
    url: str = None


@dataclass
class LocalVsPR:
    status: str  # in_sync, ahead, behind, diverged, no_pr
    ahead_count: int = 0
    behind_count: int = 0
    ahead_commits: list = None
    behind_commits: list = None


@dataclass
class BranchVsBase:
    changed_files: list


def run_cmd(cmd, check=False, timeout=60):
    """Run command and return stdout, or None on error."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=check,
            timeout=timeout
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_local_state():
    """Get local branch state."""
    # Current branch
    branch = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if not branch:
        raise SystemExit("Error: Not in a git repository")

    # Current HEAD
    head = run_cmd(["git", "rev-parse", "HEAD"])
    head_short = run_cmd(["git", "rev-parse", "--short", "HEAD"])

    # Timestamp
    timestamp = datetime.now(timezone.utc).isoformat()

    # Detect base branch (main or master)
    base_branch = run_cmd([
        "git", "symbolic-ref", "refs/remotes/origin/HEAD"
    ])
    if base_branch:
        base_branch = base_branch.replace("refs/remotes/origin/", "")
    else:
        # Fallback: check which exists
        if run_cmd(["git", "show-ref", "--verify", "refs/heads/main"]):
            base_branch = "main"
        else:
            base_branch = "master"

    # Uncommitted files (staged + unstaged, deduplicated)
    staged = run_cmd(["git", "diff", "--staged", "--name-only"]) or ""
    unstaged = run_cmd(["git", "diff", "--name-only"]) or ""

    uncommitted = set()
    if staged:
        uncommitted.update(staged.split("\n"))
    if unstaged:
        uncommitted.update(unstaged.split("\n"))
    uncommitted_files = sorted(uncommitted)

    return LocalState(
        branch=branch,
        head=head,
        head_short=head_short,
        timestamp=timestamp,
        base_branch=base_branch,
        uncommitted_files=uncommitted_files
    )


def get_pr_state(branch):
    """Get PR state for current branch."""
    # Check if PR exists
    pr_output = run_cmd([
        "gh", "pr", "list",
        "--head", branch,
        "--json", "number,headRefOid,url",
        "--limit", "1"
    ])

    if not pr_output or pr_output == "[]":
        return PRState(exists=False)

    # Parse JSON
    import json
    try:
        pr_data = json.loads(pr_output)
        if not pr_data:
            return PRState(exists=False)

        pr = pr_data[0]
        head = pr.get("headRefOid", "")

        return PRState(
            exists=True,
            number=pr.get("number"),
            head=head,
            head_short=head[:7] if head else None,
            url=pr.get("url")
        )
    except (json.JSONDecodeError, KeyError, IndexError):
        return PRState(exists=False)


def compare_local_vs_pr(local: LocalState, pr: PRState):
    """Compare local and PR state."""
    if not pr.exists:
        return LocalVsPR(status="no_pr")

    # Get commit counts
    # Ahead: commits in local but not in PR
    ahead_output = run_cmd([
        "git", "rev-list", "--count", f"{pr.head}..{local.head}"
    ])
    ahead_count = int(ahead_output) if ahead_output else 0

    # Behind: commits in PR but not in local
    behind_output = run_cmd([
        "git", "rev-list", "--count", f"{local.head}..{pr.head}"
    ])
    behind_count = int(behind_output) if behind_output else 0

    # Determine status
    if ahead_count == 0 and behind_count == 0:
        status = "in_sync"
    elif ahead_count > 0 and behind_count == 0:
        status = "ahead"
    elif ahead_count == 0 and behind_count > 0:
        status = "behind"
    else:
        status = "diverged"

    # Get commit lists if needed
    ahead_commits = None
    behind_commits = None

    if ahead_count > 0:
        ahead_log = run_cmd([
            "git", "log", "--format=%h %s", f"{pr.head}..{local.head}"
        ])
        if ahead_log:
            ahead_commits = []
            for line in ahead_log.split("\n"):
                if line:
                    sha, _, message = line.partition(" ")
                    ahead_commits.append({"sha": sha, "message": message})

    if behind_count > 0:
        behind_log = run_cmd([
            "git", "log", "--format=%h %s", f"{local.head}..{pr.head}"
        ])
        if behind_log:
            behind_commits = []
            for line in behind_log.split("\n"):
                if line:
                    sha, _, message = line.partition(" ")
                    behind_commits.append({"sha": sha, "message": message})

    return LocalVsPR(
        status=status,
        ahead_count=ahead_count,
        behind_count=behind_count,
        ahead_commits=ahead_commits,
        behind_commits=behind_commits
    )


def get_branch_vs_base(local: LocalState):
    """Get changed files: branch vs base."""
    # If on base branch, return uncommitted files
    if local.branch == local.base_branch:
        return BranchVsBase(changed_files=local.uncommitted_files)

    # Otherwise, get diff vs base
    changed = run_cmd([
        "git", "diff", f"{local.base_branch}...HEAD", "--name-only"
    ])

    changed_files = []
    if changed:
        changed_files = [f for f in changed.split("\n") if f]

    return BranchVsBase(changed_files=changed_files)


def dataclass_to_dict(obj):
    """Convert dataclass to dict, filtering None values."""
    if obj is None:
        return None

    result = {}
    for key, value in obj.__dict__.items():
        if value is None:
            continue
        if isinstance(value, list):
            if value:  # Only include non-empty lists
                # Convert nested dataclasses
                result[key] = [
                    dataclass_to_dict(item) if hasattr(item, "__dict__") else item
                    for item in value
                ]
        elif hasattr(value, "__dict__"):
            result[key] = dataclass_to_dict(value)
        else:
            result[key] = value

    return result


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(
        description="Check branch state: local, PR, and sync status"
    )
    parser.add_argument(
        "--format",
        choices=["toon", "json"],
        default="toon",
        help="Output format (default: toon)"
    )
    args = parser.parse_args()

    try:
        # Get all state
        local = get_local_state()
        pr = get_pr_state(local.branch)
        local_vs_pr = compare_local_vs_pr(local, pr)
        branch_vs_base = get_branch_vs_base(local)

        # Build output
        result = {
            "local": dataclass_to_dict(local),
            "pr": dataclass_to_dict(pr),
            "comparison": {
                "local_vs_pr": dataclass_to_dict(local_vs_pr),
                "branch_vs_base": dataclass_to_dict(branch_vs_base)
            }
        }

        # Output in requested format
        if args.format == "json":
            print(json.dumps(result, indent=2))
        else:
            print(encode(result))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
