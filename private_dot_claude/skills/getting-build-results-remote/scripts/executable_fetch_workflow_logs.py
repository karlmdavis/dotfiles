#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "toon-format==0.9.0b1",
# ]
# ///
"""Fetch workflow run logs from GitHub.

Returns TOON-formatted output to stdout.
All errors and status messages go to stderr.

Exit codes:
  0 - Success (logs fetched)
  1 - Fatal error (gh command failed, invalid input)
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from typing import TypedDict

from toon_format import encode


class CommandError(Exception):
    """Raised when a required command fails."""
    pass


@dataclass
class JobLog:
    """Logs from a single workflow job."""
    job_id: int
    job_name: str
    conclusion: str | None
    log_content: str


@dataclass
class WorkflowLogs:
    """Logs from a workflow run."""
    run_id: int
    run_name: str
    conclusion: str | None
    jobs: list[JobLog] = field(default_factory=list)


class TOONOutput(TypedDict):
    """TOON output structure for type safety."""
    status: str
    message: str
    workflows: list[dict]


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


def get_workflow_info(run_id: int) -> tuple[str, str | None]:
    """Get workflow run name and conclusion."""
    log_info(f"Fetching workflow info for run {run_id}...")

    output = run_cmd(
        ["gh", "run", "view", str(run_id), "--json", "name,conclusion"],
        f"Failed to get workflow info for run {run_id}"
    )

    try:
        data = json.loads(output)
        return data["name"], data.get("conclusion")
    except (json.JSONDecodeError, KeyError) as e:
        log_error(f"Failed to parse workflow info: {e}")
        raise CommandError(f"Failed to parse workflow info for run {run_id}") from e


def get_jobs_for_run(run_id: int) -> list[dict]:
    """Get all jobs for a workflow run."""
    log_info(f"Fetching jobs for run {run_id}...")

    output = run_cmd(
        ["gh", "run", "view", str(run_id), "--json", "jobs"],
        f"Failed to get jobs for run {run_id}"
    )

    try:
        data = json.loads(output)
        return data.get("jobs", [])
    except (json.JSONDecodeError, KeyError) as e:
        log_error(f"Failed to parse jobs: {e}")
        raise CommandError(f"Failed to parse jobs for run {run_id}") from e


def get_job_logs(run_id: int, job_id: int) -> str:
    """Fetch logs for a specific job."""
    log_info(f"Fetching logs for job {job_id}...")

    # Try to get logs via gh run view --job
    logs = run_cmd_optional([
        "gh", "run", "view", str(run_id),
        "--job", str(job_id),
        "--log"
    ])

    return logs if logs else "(logs unavailable)"


def fetch_workflow_logs(run_id: int) -> WorkflowLogs:
    """Fetch all logs for a workflow run."""
    run_name, conclusion = get_workflow_info(run_id)
    jobs_data = get_jobs_for_run(run_id)

    job_logs: list[JobLog] = []
    for job in jobs_data:
        job_id = job.get("databaseId")
        job_name = job.get("name", "Unknown Job")
        job_conclusion = job.get("conclusion")

        if not job_id:
            continue

        # Only fetch logs for failed jobs to save time and space
        if job_conclusion in ("failure", "cancelled"):
            log_content = get_job_logs(run_id, job_id)
        else:
            log_content = "(skipped - job passed)"

        job_logs.append(JobLog(
            job_id=job_id,
            job_name=job_name,
            conclusion=job_conclusion,
            log_content=log_content
        ))

    return WorkflowLogs(
        run_id=run_id,
        run_name=run_name,
        conclusion=conclusion,
        jobs=job_logs
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
    if len(sys.argv) < 2:
        log_error("Usage: fetch_workflow_logs.py <run_id> [<run_id> ...]")
        return 1

    try:
        run_ids = []
        for arg in sys.argv[1:]:
            try:
                run_ids.append(int(arg))
            except ValueError:
                log_error(f"Invalid run ID: {arg}")
                return 1

        workflows_logs: list[WorkflowLogs] = []
        for run_id in run_ids:
            log_info(f"Processing workflow run {run_id}...")
            workflow_logs = fetch_workflow_logs(run_id)
            workflows_logs.append(workflow_logs)

        result: TOONOutput = {
            "status": "success",
            "message": f"Fetched logs for {len(workflows_logs)} workflow run(s)",
            "workflows": [dataclass_to_dict(w) for w in workflows_logs],
        }

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
