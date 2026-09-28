"""zellij-gc core: session parsing, abandonment classification, and deletion.

Parsing and classification are pure functions, unit-tested directly. Everything that touches the
environment, the zellij CLI, or the filesystem sits in the I/O layer below them, which is tested end
to end against a fake `zellij`.

A session is abandoned when it never got past the welcome screen and nobody is looking at it: it is
running, older than the minimum age, and has no clients, no terminal panes, the welcome-screen
plugin, and a single default tab. Such a session holds no user state, so its name plays no part.
Every doubt (a failed, timed-out, or unparseable query) resolves to "keep the session".

A background run must never write to the terminal, so it reports to a size-capped log instead. Every
run that gets the lock leaves one line there, which is what tells "nothing to do" apart from "broken".
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
import traceback
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MIN_AGE_HOURS = 1.0
QUERY_TIMEOUT_SECONDS = 5
DELETE_TIMEOUT_SECONDS = 15
# gc.log is rotated to a single gc.log.1 past this size, capping the pair at about twice it.
LOG_MAX_BYTES = 256 * 1024

WELCOME_PLUGIN_URL = "welcome-screen"
DEFAULT_TAB_NAME = "Tab #1"

# `zellij list-sessions --no-formatting` line: `<name> [Created <age> ago]<flags>`. The greedy name
# anchors on the LAST ` [Created `, since session names may hold spaces, parens, and brackets.
SESSION_LINE = re.compile(r"^(?P<name>.+) \[Created (?P<age>[^\]]*) ago\](?P<flags>.*)$")
AGE_TOKEN = re.compile(r"(\d+)\s*([A-Za-z]+)")

# The units zellij prints, with lengths as the `humantime` crate (which formats them) defines
# them. Deliberately no other spellings: an age in a unit not listed here is unreadable, and a
# session whose age is unreadable is kept.
UNIT_SECONDS = {
    "s": 1,
    "m": 60,
    "h": 3600,
    "day": 86400, "days": 86400,
    "month": 2630016, "months": 2630016,
    "year": 31557600, "years": 31557600,
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


@dataclass(frozen=True)
class Result:
    """Outcome of one zellij call: `stdout` on success, else None with `failure` saying why."""

    stdout: str | None
    failure: str = ""


def run_zellij(zellij: str, args: list[str], *, timeout: float = QUERY_TIMEOUT_SECONDS) -> Result:
    """Run `zellij <args>`; a non-zero exit, a timeout, and a failure to start are all failures."""
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
    except subprocess.TimeoutExpired:
        return Result(None, f"timed out after {timeout}s")
    except (OSError, subprocess.SubprocessError) as error:
        return Result(None, f"could not run: {error}")
    if result.returncode != 0:
        # zellij reports some errors on stdout, so take the first line of whichever has one.
        detail = (result.stderr.strip() or result.stdout.strip()).partition("\n")[0][:200]
        return Result(None, f"exit {result.returncode}" + (f": {detail}" if detail else ""))
    return Result(result.stdout)


def keep_reason(zellij: str, session: Session, *, min_age_seconds: float) -> str | None:
    """Why a session is kept, or None if it is abandoned; any failed query means it is kept."""
    # Cheap checks first, so sessions that can't qualify are never queried.
    if session.exited:
        return "exited"
    if session.current:
        return "current session"
    if session.age_seconds is None:
        return "age unreadable"
    if session.age_seconds < min_age_seconds:
        return "younger than the minimum age"
    outputs = []
    for action in (["list-clients"], ["list-panes", "--json", "--all"], ["list-tabs", "--json"]):
        result = run_zellij(zellij, ["--session", session.name, "action", *action])
        if result.stdout is None:
            return f"{action[0]} failed ({result.failure})"
        # A session in use is settled by the first query; skip the other two.
        if action == ["list-clients"] and count_clients(result.stdout):
            return "client attached"
        outputs.append(result.stdout)
    if not is_abandoned(session, *outputs, min_age_seconds=min_age_seconds):
        return "not a bare welcome screen"
    return None


def min_age_seconds_from_env() -> float | None:
    """The age threshold in seconds, from $ZELLIJ_GC_MIN_AGE_HOURS; None if it is set but invalid.

    Unset or empty means the default. An invalid value is not replaced by the default, which could
    be shorter than the retention the owner meant to ask for; the caller deletes nothing instead.
    """
    raw = os.environ.get("ZELLIJ_GC_MIN_AGE_HOURS", "").strip()
    if not raw:
        return DEFAULT_MIN_AGE_HOURS * 3600
    try:
        hours = float(raw)
    except ValueError:
        return None
    if not 0 <= hours < float("inf"):
        return None
    return hours * 3600


def xdg_dir(variable: str, fallback: str) -> Path:
    """`$<variable>/zellij-gc`, defaulting to `~/<fallback>/zellij-gc`."""
    base = os.environ.get(variable) or os.path.join(os.path.expanduser("~"), fallback)
    return Path(base) / "zellij-gc"


def log(message: str) -> None:
    """Append a timestamped line to the size-capped GC log; logging failures are never fatal.

    Only ever called while holding the collector lock, so rotation cannot race another writer.
    """
    try:
        directory = xdg_dir("XDG_STATE_HOME", ".local/state")
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "gc.log"
        if path.exists() and path.stat().st_size > LOG_MAX_BYTES:
            os.replace(path, directory / "gc.log.1")
        stamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"{stamp} {message}\n")
    except OSError:
        pass


def report_to_stderr(message: str) -> None:
    print(f"zellij-gc: {message}", file=sys.stderr)


def collect(zellij: str, *, dry_run: bool) -> int:
    """Delete (or, for a dry run, print) every abandoned session. Returns the process exit status.

    A dry run prints the deletions on stdout and its reasoning on stderr, and logs nothing. A real
    run prints nothing, and logs one line per deletion plus one for the run.
    """
    report = report_to_stderr if dry_run else log

    min_age_seconds = min_age_seconds_from_env()
    if min_age_seconds is None:
        report(
            f"invalid ZELLIJ_GC_MIN_AGE_HOURS={os.environ.get('ZELLIJ_GC_MIN_AGE_HOURS')!r} "
            "(want a number of hours, 0 or more); nothing deleted"
        )
        return 1
    listing = run_zellij(zellij, ["list-sessions", "--no-formatting"])
    if listing.stdout is None:
        # Not an error in itself: zellij also exits non-zero when there are no sessions at all.
        report(f"run: no sessions listed ({listing.failure})")
        return 0

    sessions = parse_sessions(listing.stdout)
    unparsed = sum(1 for line in listing.stdout.splitlines() if line.strip()) - len(sessions)
    kept = deleted = failed = 0
    for session in sessions:
        reason = keep_reason(zellij, session, min_age_seconds=min_age_seconds)
        if reason is not None:
            kept += 1
            if dry_run:
                report(f"kept {session.name!r}: {reason}")
            continue
        command = ["delete-session", "--force", session.name]
        if dry_run:
            # Shell-quoted, so a name with spaces or parens can be pasted back into a shell.
            print(shlex.join([zellij, *command]))
            deleted += 1
            continue
        # Accepted race: a client could attach between the queries above and this delete. Each
        # session is deleted straight after its own inspection, so the window is a few subprocess
        # calls long, and what would be lost is a welcome screen holding no work.
        #
        # --force kills the server first, and deleting (not just killing) leaves nothing to resurrect.
        result = run_zellij(zellij, command, timeout=DELETE_TIMEOUT_SECONDS)
        if result.stdout is None:
            log(f"FAILED to delete {session.name!r} (age {session.age_seconds}s): {result.failure}")
            failed += 1
        else:
            log(f"deleted {session.name!r} (age {session.age_seconds}s)")
            deleted += 1
    report(
        f"run: {len(sessions)} listed, {kept} kept, "
        f"{deleted} {'to delete' if dry_run else 'deleted'}, {failed} failed to delete, "
        f"{unparsed} unparsed lines"
    )
    return 1 if failed else 0


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
        help="print the deletions that would be made, and why each other session is kept, "
        "without deleting anything",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    dry_run = parse_args(argv).dry_run
    zellij = os.environ.get("ZELLIJ_GC_ZELLIJ") or "zellij"
    disabled = bool(os.environ.get("ZELLIJ_GC_DISABLE"))
    if dry_run:
        # A preview deletes nothing, so the switch that stops real runs doesn't stop it.
        if disabled:
            report_to_stderr("ZELLIJ_GC_DISABLE is set, so a real run would do nothing")
        return collect(zellij, dry_run=True)
    if disabled:
        return 0

    # One collector at a time: several terminals opening at once must not race on deletions.
    # Failures here go to stderr, which zellij-welcome keeps, since the log needs the lock.
    directory = xdg_dir("XDG_CACHE_HOME", ".cache")
    try:
        directory.mkdir(parents=True, exist_ok=True)
        lock = open(directory / "lock", "w", encoding="utf-8")
    except OSError as error:
        report_to_stderr(f"cannot open the lock in {directory}: {error}")
        return 1
    with lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0  # Another collector is running, and it will do the work.
        except OSError as error:
            report_to_stderr(f"cannot lock {lock.name}: {error}")
            return 1
        try:
            return collect(zellij, dry_run=False)
        except Exception:  # Recorded, not hidden: a background run has nowhere else to report.
            log(f"run: crashed\n{traceback.format_exc().rstrip()}")
            return 1
