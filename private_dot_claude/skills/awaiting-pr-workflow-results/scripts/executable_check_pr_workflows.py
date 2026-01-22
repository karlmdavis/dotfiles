#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "toon-format==0.9.0b1",
# ]
# ///
"""Check PR workflow status with proper local/remote sync verification.

Returns TOON-formatted output to stdout.
All errors and status messages go to stderr.

Exit codes:
  0 - Success (actionable status determined)
  1 - Fatal error (git/gh command failed, invalid state)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TypedDict, NotRequired

from toon_format import encode


class CommandError(Exception):
    """Raised when a required command fails."""
    pass


@dataclass
class CommitInfo:
    """Git commit information."""
    sha: str
    message: str


@dataclass
class ArtifactInfo:
    """Workflow run artifact."""
    name: str
    url: str


@dataclass
class WorkflowResult:
    """Workflow run result."""
    name: str
    status: str
    conclusion: str | None
    duration_seconds: int | None
    url: str
    artifacts: list[ArtifactInfo] = field(default_factory=list)


@dataclass
class WorkflowSummary:
    """Summary of all workflow runs."""
    complete: bool
    wait_time_seconds: int
    results: list[WorkflowResult]


class TOONOutput(TypedDict):
    """TOON output structure for type safety."""
    status: str
    recommendation: str
    message: str
    local: dict
    pr: NotRequired[dict | None]
    commit_match: NotRequired[bool]
    action: NotRequired[str]
    workflows: NotRequired[dict | None]


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


def call_getting_branch_state() -> dict:
    """Call getting-branch-state skill and return parsed JSON."""
    script_path = os.path.expanduser(
        "~/.claude/skills/getting-branch-state/scripts/check_branch_state.py"
    )

    log_info("Getting branch state...")

    try:
        result = subprocess.run(
            [script_path, "--format", "json"],
            capture_output=True,
            text=True,
            check=False,
            timeout=60
        )

        if result.returncode != 0:
            log_error("getting-branch-state failed")
            if result.stderr:
                log_error(result.stderr)
            raise CommandError("Failed to get branch state")

        return json.loads(result.stdout)

    except FileNotFoundError:
        log_error(f"getting-branch-state not found: {script_path}")
        raise CommandError("getting-branch-state script not found")
    except subprocess.TimeoutExpired:
        log_error("getting-branch-state timed out")
        raise CommandError("getting-branch-state timeout")
    except json.JSONDecodeError as e:
        log_error(f"Failed to parse branch state JSON: {e}")
        raise CommandError("Invalid branch state output")


def wait_for_workflow_start(commit: str, max_wait: int = 30) -> list[dict] | None:
    """Wait for workflows to start, return None if timeout."""
    log_info("Waiting for workflows to start...")
    start_time = time.time()

    while True:
        output = run_cmd_optional([
            "gh", "run", "list", "--commit", commit, "--limit", "5",
            "--json", "databaseId,name,status,conclusion,createdAt,updatedAt,url"
        ])

        if output:
            try:
                runs = json.loads(output)
                if runs:
                    log_info(f"Found {len(runs)} workflow run(s)")
                    return runs
            except json.JSONDecodeError:
                pass

        elapsed = time.time() - start_time
        if elapsed >= max_wait:
            log_info(f"No workflows started after {max_wait}s")
            return None

        time.sleep(5)


def get_artifacts(run_id: int) -> list[ArtifactInfo]:
    """Get artifacts for a workflow run."""
    output = run_cmd_optional([
        "gh", "api", f"/repos/{{owner}}/{{repo}}/actions/runs/{run_id}/artifacts",
        "--jq", ".artifacts[] | {name: .name, url: .archive_download_url}"
    ])

    if not output:
        return []

    artifacts: list[ArtifactInfo] = []
    for line in output.split("\n"):
        if line.strip():
            try:
                data = json.loads(line)
                artifacts.append(ArtifactInfo(name=data["name"], url=data["url"]))
            except (json.JSONDecodeError, KeyError):
                continue

    return artifacts


def calculate_duration(created_at: str, updated_at: str, status: str) -> int | None:
    """Calculate workflow duration (completed) or elapsed time (running) in seconds."""
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        if status in ("completed", "cancelled", "failure", "success"):
            updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            return int((updated - created).total_seconds())
        else:
            now = datetime.now(created.tzinfo)
            return int((now - created).total_seconds())
    except (ValueError, AttributeError):
        return None


def wait_for_completion(
    commit: str,
    max_wait: int | None = None,
    initial_interval: int = 5,
    max_interval: int = 60
) -> WorkflowSummary:
    """Wait for workflows to complete with exponential backoff.

    Args:
        max_wait: Maximum seconds to wait. Defaults to 1200 (20 minutes).
                  Can be overridden with CLAUDE_WORKFLOW_TIMEOUT env var.
    """
    # Allow environment variable override for projects with long-running workflows
    if max_wait is None:
        max_wait = int(os.getenv('CLAUDE_WORKFLOW_TIMEOUT', '1200'))

    max_wait_minutes = max_wait // 60
    log_info(f"Waiting for workflows to complete (max {max_wait_minutes} minutes)...")
    start_time = time.time()
    interval = initial_interval

    runs = wait_for_workflow_start(commit)
    if not runs:
        return WorkflowSummary(complete=False, wait_time_seconds=0, results=[])

    while True:
        elapsed = int(time.time() - start_time)

        # Refresh workflow status
        output = run_cmd([
            "gh", "run", "list", "--commit", commit,
            "--json", "databaseId,name,status,conclusion,createdAt,updatedAt,url"
        ], "Failed to list workflow runs")

        try:
            runs = json.loads(output)
        except json.JSONDecodeError as e:
            log_error(f"Failed to parse workflow runs: {e}")
            break

        # Check completion
        incomplete = [r for r in runs if r["status"] in ("in_progress", "queued")]
        if not incomplete:
            log_info(f"All workflows complete after {elapsed}s")
            break

        # Check timeout
        if elapsed >= max_wait:
            log_info(f"Timeout after {elapsed}s ({len(incomplete)} still running)")
            break

        log_info(f"{len(incomplete)} workflow(s) still running ({elapsed}s elapsed)")
        time.sleep(interval)
        interval = min(interval * 2, max_interval)

    # Build results
    results: list[WorkflowResult] = []
    for run in runs:
        duration = calculate_duration(
            run["createdAt"],
            run["updatedAt"],
            run["status"]
        )
        artifacts = get_artifacts(run["databaseId"])

        results.append(WorkflowResult(
            name=run["name"],
            status=run["status"],
            conclusion=run.get("conclusion"),
            duration_seconds=duration,
            url=run["url"],
            artifacts=artifacts
        ))

    complete = all(r.status not in ("in_progress", "queued") for r in results)
    return WorkflowSummary(
        complete=complete,
        wait_time_seconds=int(time.time() - start_time),
        results=results
    )


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
    try:
        # Get branch state using getting-branch-state skill
        branch_state = call_getting_branch_state()

        local = branch_state["local"]
        pr_info = branch_state["pr"]
        comparison = branch_state["comparison"]["local_vs_pr"]

        # Build local info for output (simplified from branch state)
        local_output = {
            "branch": local["branch"],
            "commit": local["head_short"],
            "commit_full": local["head"],
            "timestamp": local["timestamp"],
        }

        result: TOONOutput = {
            "status": "",
            "recommendation": "",
            "message": "",
            "local": local_output,
        }

        # Add PR info if exists
        if pr_info["exists"]:
            result["pr"] = {
                "number": pr_info["number"],
                "commit": pr_info["head_short"],
                "commit_full": pr_info["head"],
                "url": pr_info["url"],
            }
        else:
            result["pr"] = None

        # Determine status based on branch state
        if not pr_info["exists"]:
            result["status"] = "no_pr"
            result["recommendation"] = "create_pr"
            result["message"] = f"No PR found for branch '{local['branch']}'"
            result["action"] = "ask_user_to_create_pr"

        elif comparison["status"] in ("ahead", "diverged"):
            # Local has unpushed commits or diverged from PR
            result["status"] = "warning"
            result["recommendation"] = "push_required"
            result["commit_match"] = False

            # Convert ahead_commits to expected format
            ahead_commits = comparison.get("ahead_commits", [])
            local_output["unpushed_count"] = comparison.get("ahead_count", 0)
            local_output["unpushed_commits"] = ahead_commits

            result["message"] = (
                f"Found {comparison['ahead_count']} unpushed commit(s). "
                f"PR workflows testing {pr_info['head_short']}, not your latest changes."
            )
            result["action"] = "ask_user_to_push"

        else:
            # Local and PR are in sync, check workflows
            result["commit_match"] = True
            workflow_summary = wait_for_completion(pr_info["head"])
            result["workflows"] = dataclass_to_dict(workflow_summary)

            if workflow_summary.complete:
                failures = [w for w in workflow_summary.results
                           if w.conclusion in ("failure", "cancelled")]
                if failures:
                    result["status"] = "failure"
                    result["recommendation"] = "fix_failures"
                    result["message"] = (
                        f"{len(failures)} workflow(s) failed for commit {pr_info['head_short']}"
                    )
                else:
                    result["status"] = "success"
                    result["recommendation"] = "all_passed"
                    result["message"] = (
                        f"All {len(workflow_summary.results)} workflow(s) passed "
                        f"for commit {pr_info['head_short']}"
                    )
            else:
                incomplete = [w for w in workflow_summary.results
                             if w.status in ("in_progress", "queued")]
                result["status"] = "timeout"
                result["recommendation"] = "wait_longer_or_check_logs"
                result["message"] = (
                    f"{len(incomplete)} workflow(s) still running after "
                    f"{workflow_summary.wait_time_seconds}s"
                )

        # Output TOON to stdout (only thing on stdout)
        print(encode(result))
        return 0

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
