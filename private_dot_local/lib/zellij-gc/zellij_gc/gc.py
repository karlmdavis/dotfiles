"""zellij-gc core: session parsing, abandonment classification, and deletion.

The pure functions (`parse_age`, `parse_sessions`, `count_clients`, `is_abandoned`) carry all the
logic and are unit-tested directly. `run_zellij`, `inspect`, and `main` are the thin I/O layer: they
read env seams, query zellij, and either print the would-be deletion (`--dry-run`) or run it.

A session is abandoned when it never got past the welcome screen and nobody is looking at it: no
clients, no terminal panes, the welcome-screen plugin, and a single default tab. Such a session holds
no user state, so its name plays no part. Every doubt (a failed, timed-out, or unparseable query)
resolves to "keep the session".
"""

from __future__ import annotations

import argparse
import datetime
import fcntl
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MIN_AGE_HOURS = 1.0
QUERY_TIMEOUT_SECONDS = 5
DELETE_TIMEOUT_SECONDS = 15

WELCOME_PLUGIN_URL = "welcome-screen"
DEFAULT_TAB_NAME = "Tab #1"

# `zellij list-sessions --no-formatting` line: `<name> [Created <age> ago]<flags>`. The greedy name
# anchors on the LAST ` [Created `, since session names may hold spaces, parens, and brackets.
SESSION_LINE = re.compile(r"^(?P<name>.+) \[Created (?P<age>[^\]]*) ago\](?P<flags>.*)$")
AGE_TOKEN = re.compile(r"(\d+)\s*([A-Za-z]+)")

# Unit lengths as the `humantime` crate (which zellij formats ages with) defines them.
UNIT_SECONDS = {
    "s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1,
    "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60,
    "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600,
    "d": 86400, "day": 86400, "days": 86400,
    "w": 604800, "week": 604800, "weeks": 604800,
    "M": 2630016, "month": 2630016, "months": 2630016,
    "y": 31557600, "year": 31557600, "years": 31557600,
}


@dataclass(frozen=True)
class Session:
    """One line of `zellij list-sessions`. `age_seconds` is None when the age didn't parse."""

    name: str
    age_seconds: int | None
    exited: bool = False
    current: bool = False


def parse_age(text: str) -> int | None:
    """Seconds in a humantime age like `3months 25days 20h 9m 36s`; None if any part is unknown."""
    tokens = AGE_TOKEN.findall(text)
    if not tokens or AGE_TOKEN.sub("", text).strip():
        return None
    total = 0
    for count, unit in tokens:
        seconds = UNIT_SECONDS.get(unit)
        if seconds is None:
            return None
        total += int(count) * seconds
    return total


def parse_sessions(text: str) -> list[Session]:
    """Sessions from `zellij list-sessions --no-formatting`; lines of any other shape are dropped."""
    sessions = []
    for line in text.splitlines():
        match = SESSION_LINE.match(line.rstrip())
        if not match:
            continue
        flags = match["flags"]
        sessions.append(
            Session(
                name=match["name"],
                age_seconds=parse_age(match["age"]),
                exited="EXITED" in flags,
                current="(current)" in flags,
            )
        )
    return sessions


def count_clients(text: str) -> int | None:
    """Client rows in `zellij action list-clients` output; None if the header isn't the known one."""
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines or not lines[0].startswith("CLIENT_ID"):
        return None
    return len(lines) - 1


def is_abandoned(
    session: Session,
    clients_text: str,
    panes_json: str,
    tabs_json: str,
    *,
    min_age_seconds: float,
) -> bool:
    """Whether the session is an unattended welcome screen that is safe to delete."""
    if session.exited or session.current:
        return False
    if session.age_seconds is None or session.age_seconds < min_age_seconds:
        return False
    if count_clients(clients_text) != 0:
        return False
    try:
        panes = json.loads(panes_json)
        tabs = json.loads(tabs_json)
    except ValueError:
        return False
    if not isinstance(panes, list) or not isinstance(tabs, list):
        return False
    if not all(isinstance(entry, dict) for entry in [*panes, *tabs]):
        return False
    # `is True` so that a missing or oddly-typed field counts as a terminal pane.
    if not panes or not all(pane.get("is_plugin") is True for pane in panes):
        return False
    if not any(pane.get("plugin_url") == WELCOME_PLUGIN_URL for pane in panes):
        return False
    return len(tabs) == 1 and tabs[0].get("name") == DEFAULT_TAB_NAME


def run_zellij(zellij: str, args: list[str], *, timeout: int = QUERY_TIMEOUT_SECONDS) -> str | None:
    """stdout of `zellij <args>`, or None if it failed, timed out, or couldn't be started."""
    try:
        result = subprocess.run(
            [zellij, *args],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            # Decoded as UTF-8 whatever the locale, and never raising: a name or title that isn't
            # valid UTF-8 comes through mangled, which at worst fails to parse (session kept).
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def inspect(zellij: str, session: Session, *, min_age_seconds: float) -> bool:
    """Query a live session and classify it; any failed query means it is kept."""
    # Cheap checks first, so sessions that can't qualify are never queried.
    if session.exited or session.current:
        return False
    if session.age_seconds is None or session.age_seconds < min_age_seconds:
        return False
    outputs = []
    for action in (["list-clients"], ["list-panes", "--json", "--all"], ["list-tabs", "--json"]):
        output = run_zellij(zellij, ["--session", session.name, "action", *action])
        if output is None:
            return False
        # A session in use is settled by the first query; skip the other two.
        if action == ["list-clients"] and count_clients(output) != 0:
            return False
        outputs.append(output)
    return is_abandoned(session, *outputs, min_age_seconds=min_age_seconds)


def min_age_seconds_from_env() -> float:
    """The age threshold in seconds, from $ZELLIJ_GC_MIN_AGE_HOURS (bad values → the default)."""
    try:
        hours = float(os.environ.get("ZELLIJ_GC_MIN_AGE_HOURS", ""))
    except ValueError:
        hours = DEFAULT_MIN_AGE_HOURS
    if not 0 <= hours < float("inf"):
        hours = DEFAULT_MIN_AGE_HOURS
    return hours * 3600


def xdg_dir(variable: str, fallback: str) -> Path:
    """`$<variable>/zellij-gc`, defaulting to `~/<fallback>/zellij-gc`."""
    base = os.environ.get(variable) or os.path.join(os.path.expanduser("~"), fallback)
    return Path(base) / "zellij-gc"


def log(message: str) -> None:
    """Append a timestamped line to the GC log; logging failures are never fatal."""
    try:
        directory = xdg_dir("XDG_STATE_HOME", ".local/state")
        directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        with open(directory / "gc.log", "a", encoding="utf-8") as handle:
            handle.write(f"{stamp} {message}\n")
    except OSError:
        pass


def collect(zellij: str, *, dry_run: bool) -> int:
    """Delete (or, for a dry run, print) every abandoned session. Returns the process exit status."""
    listing = run_zellij(zellij, ["list-sessions", "--no-formatting"])
    if listing is None:
        # Also the "no sessions at all" case, which zellij reports with a non-zero exit.
        return 0
    min_age_seconds = min_age_seconds_from_env()
    status = 0
    for session in parse_sessions(listing):
        if not inspect(zellij, session, min_age_seconds=min_age_seconds):
            continue
        command = ["delete-session", "--force", session.name]
        if dry_run:
            # Shell-quoted, so a name with spaces or parens can be pasted back into a shell.
            print(shlex.join([zellij, *command]))
            continue
        # Accepted race: a client could attach between the queries above and this delete. Each
        # session is deleted straight after its own inspection, so the window is a few subprocess
        # calls long, and what would be lost is a welcome screen holding no work.
        # --force kills the server first, and deleting (not just killing) leaves nothing to resurrect.
        if run_zellij(zellij, command, timeout=DELETE_TIMEOUT_SECONDS) is None:
            log(f"FAILED to delete {session.name!r} (age {session.age_seconds}s)")
            status = 1
        else:
            log(f"deleted {session.name!r} (age {session.age_seconds}s)")
    return status


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse the command line; anything unrecognised exits with status 2 before zellij is touched."""
    parser = argparse.ArgumentParser(
        prog="zellij-gc",
        description="Delete zellij sessions abandoned at the welcome screen.",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the deletions that would be made, without making them",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    dry_run = parse_args(argv).dry_run
    if os.environ.get("ZELLIJ_GC_DISABLE"):
        return 0
    zellij = os.environ.get("ZELLIJ_GC_ZELLIJ") or "zellij"
    if dry_run:
        return collect(zellij, dry_run=True)

    # One collector at a time: several terminals opening at once must not race on deletions.
    try:
        directory = xdg_dir("XDG_CACHE_HOME", ".cache")
        directory.mkdir(parents=True, exist_ok=True)
        lock = open(directory / "lock", "w", encoding="utf-8")
    except OSError:
        return 0
    with lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return 0
        return collect(zellij, dry_run=False)
