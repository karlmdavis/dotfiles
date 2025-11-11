#!/usr/bin/env python3
"""
Zellij Clients Mapper

OVERVIEW
========
Maps Zellij server processes to their connected client processes using OS-level
socket inspection. Since Zellij servers don't track client PIDs internally, this
tool uses lsof to match Unix domain socket addresses between processes.

USAGE
=====
    python3 zellij-clients.py <PID>
    uv run zellij-clients.py <PID>

Arguments:
    PID: Process ID to inspect (must be a Zellij server)

Output:
    JSON object with process details and connected clients (if server)
    Writes to stdout

Exit Codes:
    0: Input PID is a Zellij server
    1: Input PID is not a Zellij server, not found, or fatal error occurred

Example Output:
    {
      "origin": {
        "pid": 32976,
        "command": "/opt/homebrew/bin/zellij --server .../dotfiles.git",
        "tty": "??",
        "started_at": "2024-10-24T15:23:45-07:00",
        "status": "S",
        "classifier": "zellij-server",
        "zellij_session": "dotfiles.git",
        "clients": [
          {
            "pid": 88661,
            "command": "/opt/homebrew/bin/zellij -l welcome",
            "tty": "s012",
            "started_at": "2024-11-10T22:10:15-08:00",
            "status": "S",
            "classifier": "zellij-client",
            "zellij_session": null
          }
        ]
      },
      "warnings": [
        "Failed to get details for client PID 12345: ..."
      ]
    }

ARCHITECTURE
============

Problem:
    Zellij servers maintain client connections but do NOT track client process IDs.
    The server's SessionState (zellij-server/src/lib.rs) only stores:
    - Sequential ClientId numbers (u16)
    - Terminal sizes
    - Socket connections

    No OS-level process information is maintained, making it impossible to query
    the server directly for connected client PIDs.

Solution:
    Use Unix domain socket inspection via lsof to correlate processes:

    1. Server Process → Socket Addresses
       Run lsof on the server PID to get all Unix socket addresses it holds

    2. Socket Addresses → Client PIDs
       Search all processes for those same socket addresses
       Any non-server process sharing a socket is a connected client

    3. Client PIDs → Process Details
       Use ps to gather details for each discovered client

Why Not /proc?
    The /proc filesystem (common on Linux) doesn't exist on macOS.
    lsof is portable across both platforms.

Communication Mechanism:
    Zellij uses Unix domain sockets with length-prefixed Protobuf messages.
    Socket paths: $XDG_RUNTIME_DIR/zellij/contract_version_1/<session-name>
    On macOS: ~/Library/Caches/org.Zellij-Contributors.Zellij/...

TTY vs PTY:
    - TTY (Terminal): Controlling terminal for a process (e.g., "s012")
    - PTY (Pseudo-Terminal): Virtual terminal pair (master/slave)

    Zellij servers daemonize and detach from their controlling terminal,
    showing "??" for TTY. This is expected behavior for daemon processes.

    Zellij clients maintain their TTY from the terminal they were launched in.
    Each pane inside Zellij gets its own PTY (not visible in this mapping).

Race Conditions:
    Client processes can exit at any time, creating race conditions:

    1. lsof captures socket state at time T
    2. We find client PID 12345 in the socket list
    3. Client 12345 exits before we call ps
    4. ps fails with "no such process"

    This is an EXPECTED condition, not an error. The design accommodates this by:
    - Treating per-client failures as warnings, not fatal errors
    - Collecting warnings with detailed context
    - Continuing to process remaining clients
    - Only failing fatally if system commands fail entirely (lsof unavailable, etc.)

    This makes the tool robust against the inherently dynamic nature of the
    client list while still surfacing unexpected issues.

Data Flow:
    main()
      ├─> get_process_details(origin_pid) → (ProcessDetails, error)
      │   └─> run_ps(...) → subprocess calls
      │
      ├─> get_lsof_data() → all Unix socket info
      │
      ├─> extract_server_sockets(pid, lsof_lines) → set of hex addresses
      │
      └─> find_client_pids(server_sockets, lsof_lines) → set of PIDs
          └─> get_process_details(each_client_pid) → (ProcessDetails, error)

Type Safety:
    All functions use strong typing with no 'Any' types.
    Unexpected data formats from system commands raise exceptions.
    TypedDict classes ensure JSON structure matches specification.
"""

import subprocess
import sys
import json
import re
import os
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional, Literal, TypedDict


# Type Definitions
# ================

Classifier = Optional[Literal['zellij-server', 'zellij-client']]


class ProcessDetails(TypedDict):
    """Details for a single process (origin or client)."""
    pid: int
    command: Optional[str]
    tty: Optional[str]
    started_at: Optional[str]  # ISO 8601 with timezone
    status: Optional[str]      # ps state code (R/S/Z/T/I)
    classifier: Classifier
    zellij_session: Optional[str]


class OriginDetails(TypedDict):
    """Details for the origin process including its clients."""
    pid: int
    command: Optional[str]
    tty: Optional[str]
    started_at: Optional[str]
    status: Optional[str]
    classifier: Classifier
    zellij_session: Optional[str]
    clients: list[ProcessDetails]


class Output(TypedDict, total=False):
    """Top-level output structure."""
    origin: OriginDetails
    warnings: list[str]  # Only present if non-empty
    error: str           # Only present on fatal errors


# Logging Support
# ================

def log_debug(component: str, message: str) -> None:
    """
    Log a debug message using the wkflw-ntfy logging system.

    Args:
        component: Component name (e.g., "zellij-clients")
        message: Log message

    Note:
        Only logs if WKFLW_NTFY_DEBUG=1 in config.
        Calls the bash logging script for consistency.
    """
    # Find the logging script relative to this Python script
    script_dir = Path(__file__).parent.parent / "core"
    log_script = script_dir / "wkflw-ntfy-log"

    subprocess.run(
        [str(log_script), "debug", component, message],
        capture_output=True,
        timeout=2,
        check=True
    )


# Helper Functions
# ================

def run_ps(pid: int, field: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Run ps command to get a specific field for a PID.

    Args:
        pid: Process ID to query
        field: ps field name (e.g., 'args', 'tty', 'state', 'lstart')

    Returns:
        Tuple of (field_value, error_message)
        - On success: (value, None)
        - On failure: (None, error message with command details)
    """
    try:
        result = subprocess.run(
            ['ps', '-p', str(pid), '-o', f'{field}='],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            error = (
                f"Failed to get {field} for PID {pid}: "
                f"Command 'ps -p {pid} -o {field}=' exited with code {result.returncode}, "
                f"stderr: {result.stderr.strip()!r}"
            )
            return (None, error)

        return (result.stdout.strip(), None)

    except subprocess.TimeoutExpired:
        return (None, f"Timeout getting {field} for PID {pid}: ps command took >5s")
    except Exception as e:
        return (None, f"Unexpected error getting {field} for PID {pid}: {type(e).__name__}: {e}")


def parse_timestamp(lstart: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse ps lstart timestamp to ISO 8601 format with timezone.

    Args:
        lstart: Timestamp from ps in format "Thu Nov  7 14:23:45 2024"

    Returns:
        Tuple of (iso_timestamp, error_message)
        - On success: ("2024-11-07T14:23:45-08:00", None)
        - On failure: (None, error message)
    """
    try:
        # Parse the timestamp (assumes local time)
        dt_naive = datetime.strptime(lstart.strip(), "%a %b %d %H:%M:%S %Y")

        # Add local timezone information
        local_tz = datetime.now().astimezone().tzinfo
        dt_aware = dt_naive.replace(tzinfo=local_tz)

        # Convert to ISO 8601 with timezone
        return (dt_aware.isoformat(), None)

    except ValueError as e:
        return (None, f"Failed to parse timestamp '{lstart}': {e}")
    except Exception as e:
        return (None, f"Unexpected error parsing timestamp: {type(e).__name__}: {e}")


def classify_process(command: Optional[str]) -> Classifier:
    """
    Classify a process as zellij-server, zellij-client, or neither.

    Args:
        command: Full command line string

    Returns:
        'zellij-server', 'zellij-client', or None
    """
    if command is None:
        return None

    if '--server' in command:
        return 'zellij-server'
    elif 'zellij' in command:
        return 'zellij-client'
    else:
        return None


def extract_session_name(command: Optional[str], lsof_lines: list[str], pid: int) -> Optional[str]:
    """
    Extract Zellij session name for a server process.

    Only works for servers (returns None for clients).
    Session name is extracted from the socket path in lsof output.

    Args:
        command: Process command line
        lsof_lines: All lsof output lines
        pid: Process ID

    Returns:
        Session name (e.g., "dotfiles.git") or None
    """
    # Only servers have session names we can extract
    if classify_process(command) != 'zellij-server':
        return None

    # Find lsof lines for this server that contain socket paths
    pid_str = str(pid)
    for line in lsof_lines:
        # Match lines for this PID
        match = re.match(r'zellij\s+(\d+)', line)
        if not match or match.group(1) != pid_str:
            continue

        # Extract session name from socket path
        # Format: /var/folders/.../zellij-501/0.43.1/<session-name>
        session_match = re.search(r'/zellij[^/]*/[^/]*/([^/\s]+)', line)
        if session_match:
            return session_match.group(1)

    return None


def get_process_details(
    pid: int,
    lsof_lines: list[str]
) -> Tuple[Optional[ProcessDetails], Optional[str]]:
    """
    Gather all details for a process.

    Args:
        pid: Process ID to inspect
        lsof_lines: Pre-fetched lsof output for session extraction

    Returns:
        Tuple of (ProcessDetails, error_message)
        - On success: (ProcessDetails, None)
        - On failure: (None, detailed error message)

    Note:
        Failure can occur due to race conditions (process exited) or
        permission issues. Caller should handle gracefully.
    """
    # Get command (most important field)
    command, error = run_ps(pid, 'args')
    if error:
        return (None, error)

    # Get TTY
    tty, error = run_ps(pid, 'tty')
    if error:
        return (None, error)

    # Get status
    status, error = run_ps(pid, 'state')
    if error:
        return (None, error)

    # Get start time
    lstart, error = run_ps(pid, 'lstart')
    if error:
        return (None, error)

    started_at: Optional[str] = None
    if lstart:
        started_at, error = parse_timestamp(lstart)
        if error:
            return (None, error)

    # Classify process
    classifier = classify_process(command)

    # Extract session name (servers only)
    zellij_session = extract_session_name(command, lsof_lines, pid)

    details: ProcessDetails = {
        'pid': pid,
        'command': command,
        'tty': tty,
        'started_at': started_at,
        'status': status,
        'classifier': classifier,
        'zellij_session': zellij_session
    }

    return (details, None)


def get_lsof_data() -> Tuple[Optional[list[str]], Optional[str]]:
    """
    Get all Unix domain socket information via lsof.

    Returns:
        Tuple of (lsof_output_lines, error_message)
        - On success: (list of lines, None)
        - On failure: (None, error message with command details)
    """
    try:
        result = subprocess.run(
            ['lsof', '-U'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            error = (
                f"Failed to execute lsof: "
                f"Command 'lsof -U' exited with code {result.returncode}, "
                f"stderr: {result.stderr.strip()!r}"
            )
            return (None, error)

        return (result.stdout.split('\n'), None)

    except subprocess.TimeoutExpired:
        return (None, "Timeout executing lsof: command took >10s")
    except FileNotFoundError:
        return (None, "lsof command not found: ensure lsof is installed")
    except Exception as e:
        return (None, f"Unexpected error running lsof: {type(e).__name__}: {e}")


def extract_server_sockets(pid: int, lsof_lines: list[str]) -> set[str]:
    """
    Extract all Unix socket addresses for a server process.

    Args:
        pid: Server process ID
        lsof_lines: Output from lsof -U

    Returns:
        Set of hex socket addresses (e.g., {"0xabc123...", "0xdef456..."})
    """
    server_sockets: set[str] = set()
    pid_str = str(pid)

    for line in lsof_lines:
        # Check if this line is for our server PID
        match = re.match(r'zellij\s+(\d+)', line)
        if not match or match.group(1) != pid_str:
            continue

        # Extract all hex socket addresses from this line
        hex_addrs = re.findall(r'0x[0-9a-f]+', line)
        server_sockets.update(hex_addrs)

    return server_sockets


def find_client_pids(server_sockets: set[str], lsof_lines: list[str], server_pid: int) -> set[int]:
    """
    Find all client PIDs that share socket addresses with the server.

    Args:
        server_sockets: Set of hex socket addresses from the server
        lsof_lines: Output from lsof -U
        server_pid: Server process ID (to exclude from results)

    Returns:
        Set of client process IDs
    """
    client_pids: set[int] = set()
    server_pid_str = str(server_pid)

    for line in lsof_lines:
        # Only look at zellij processes
        match = re.match(r'zellij\s+(\d+)', line)
        if not match:
            continue

        pid_str = match.group(1)
        if pid_str == server_pid_str:
            continue

        # Check if this line contains any of the server's socket addresses
        for sock_addr in server_sockets:
            if sock_addr in line:
                client_pids.add(int(pid_str))
                break

    return client_pids


def create_empty_origin(pid: int) -> OriginDetails:
    """
    Create an empty origin details object for a non-existent process.

    Args:
        pid: Process ID that was requested

    Returns:
        OriginDetails with all fields null except pid
    """
    return {
        'pid': pid,
        'command': None,
        'tty': None,
        'started_at': None,
        'status': None,
        'classifier': None,
        'zellij_session': None,
        'clients': []
    }


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Parse arguments
    if len(sys.argv) != 2:
        print("Usage: zellij-clients.py <PID>", file=sys.stderr)
        return 1

    try:
        origin_pid = int(sys.argv[1])
    except ValueError:
        output: Output = {
            'origin': create_empty_origin(0),
            'error': f"Invalid PID argument: {sys.argv[1]!r} is not a number"
        }
        print(json.dumps(output, indent=2))
        return 1

    warnings: list[str] = []

    try:
        log_debug("zellij-clients", f"Checking PID {origin_pid}")

        # Get lsof data (needed for session name extraction and client finding)
        lsof_lines, error = get_lsof_data()
        if error:
            log_debug("zellij-clients", f"lsof failed: {error}")
            output = {
                'origin': create_empty_origin(origin_pid),
                'error': error
            }
            print(json.dumps(output, indent=2))
            return 1

        assert lsof_lines is not None, "lsof_lines should not be None after successful get_lsof_data"

        # Get origin process details
        origin_details, error = get_process_details(origin_pid, lsof_lines)
        if error:
            # Process not found or inaccessible
            log_debug("zellij-clients", f"Failed to get process details: {error}")
            output = {
                'origin': create_empty_origin(origin_pid),
                'error': f"Process {origin_pid} not found or inaccessible: {error}"
            }
            print(json.dumps(output, indent=2))
            return 1

        assert origin_details is not None, "origin_details should not be None after successful get_process_details"

        classifier = origin_details['classifier']
        log_debug("zellij-clients", f"PID {origin_pid} classifier: {classifier}")

        # Build origin with empty clients list
        origin: OriginDetails = {
            **origin_details,
            'clients': []
        }

        # If origin is a server, find connected clients
        if origin_details['classifier'] == 'zellij-server':
            session_name = origin_details.get('zellij_session', 'unknown')
            log_debug("zellij-clients", f"PID {origin_pid} is zellij server (session: {session_name})")

            server_sockets = extract_server_sockets(origin_pid, lsof_lines)
            client_pids = find_client_pids(server_sockets, lsof_lines, origin_pid)
            log_debug("zellij-clients", f"Found {len(client_pids)} client PIDs: {sorted(client_pids)}")

            # Get details for each client
            for client_pid in sorted(client_pids):
                client_details, error = get_process_details(client_pid, lsof_lines)
                if error:
                    log_debug("zellij-clients", f"Failed to get client {client_pid} details: {error}")
                    warnings.append(error)
                elif client_details is not None:
                    origin['clients'].append(client_details)
        else:
            log_debug("zellij-clients", f"PID {origin_pid} is not a zellij server")

        # Build output
        output: Output = {'origin': origin}
        if warnings:
            output['warnings'] = warnings

        print(json.dumps(output, indent=2))

        # Exit code: 0 only if origin is a zellij server, 1 otherwise
        return 0 if origin_details['classifier'] == 'zellij-server' else 1

    except Exception as e:
        # Unexpected fatal error
        import traceback
        output = {
            'origin': create_empty_origin(origin_pid),
            'error': f"Unexpected error: {type(e).__name__}: {e}\n\nTraceback:\n{traceback.format_exc()}"
        }
        print(json.dumps(output, indent=2))
        return 1


if __name__ == '__main__':
    sys.exit(main())
