"""zellij-gc core: session parsing, abandonment classification, and deletion.

Parsing and classification are pure functions, unit-tested directly. Everything that touches the
environment, the zellij CLI, or the filesystem sits in the I/O layer below them, which is tested
end to end against a fake `zellij`.

A session is abandoned when it never got past the welcome screen and nobody is looking at it: it is
running, older than the minimum age, and has no clients, no terminal panes, the welcome-screen
plugin, and a single default tab. Such a session holds no user state, so its name plays no part.
Every doubt (a failed, timed-out, or unparseable query) resolves to "keep the session".

A real run happens while a terminal waits for its chooser, so it is built to be quick and bounded.
Every zellij command probes every session on the machine before it does anything else, so commands
are what cost time, and the run avoids them: it first reads the metadata file that each zellij
server keeps about itself, and sessions which that shows to be in use are kept without a single
query. The file is only ever a reason to keep a session. One that looks abandoned, or has no
readable file, is put to zellij itself, and nothing is deleted on the file's word. The run also
has a time budget, and Ctrl-C ends it.

What a run did goes to a size-capped log, since zellij clears the screen straight afterwards.
Every run that gets the lock leaves one line there, which is what tells "nothing to do" apart from
"broken".

POSIX only: the lock is `fcntl.flock`, and the shim's shebang needs an `env` that has `-S`.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import glob
import json
import logging
import logging.handlers
import os
import re
import shlex
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

DEFAULT_MIN_AGE_HOURS = 1.0
QUERY_TIMEOUT_SECONDS = 5
DELETE_TIMEOUT_SECONDS = 15
# A real run gives up after this long, leaving the rest for the next launch.
BUDGET_SECONDS = 10
# A real run that is still going after this long says so on the terminal.
NOTICE_AFTER_SECONDS = 1
# The conventional exit status for "ended by Ctrl-C".
EXIT_INTERRUPTED = 130
# gc.log is rotated to a single gc.log.1 before it would pass this size.
LOG_MAX_BYTES = 256 * 1024

METADATA_FILE = "session-metadata.kdl"
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
    "day": 86400,
    "days": 86400,
    "month": 2630016,
    "months": 2630016,
    "year": 31557600,
    "years": 31557600,
}


@dataclass(frozen=True, slots=True)
class Session:
    """One line of `zellij list-sessions`. `age_seconds` is None when the age didn't parse."""

    name: str
    age_seconds: int | None
    exited: bool = False
    current: bool = False


@dataclass(frozen=True, slots=True)
class Result:
    """Outcome of one zellij call: `stdout` on success, else None with `failure` saying why."""

    stdout: str | None
    failure: str = ""


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
    """Sessions from `zellij list-sessions --no-formatting`; other lines are dropped."""
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
    """Client rows in `zellij action list-clients` output; None if the header is unfamiliar."""
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines or not lines[0].startswith("CLIENT_ID"):
        return None
    return len(lines) - 1


# A chain of early exits, each a reason to keep the session, reads better than one expression.
def is_abandoned(  # noqa: PLR0911
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


def metadata_keep_reason(text: str) -> str | None:
    """Why a session's own metadata file shows it to be in use, or None if it shows no such thing.

    The file is zellij's, in KDL, and its format is not a documented interface, so this reads only
    the few lines it needs and treats everything else as unknown. It can only ever say "keep": None
    covers both a session that looks abandoned and a file this cannot make sense of, and either
    way the session is then put to zellij itself.
    """
    clients = re.search(r"^connected_clients (\d+)$", text, re.MULTILINE)
    if clients and int(clients[1]) > 0:
        return "client attached"
    if re.search(r"^ {8}is_plugin false$", text, re.MULTILINE):
        return "has a terminal pane"
    tabs = re.search(r"^tabs \{\n(.*?)^\}$", text, re.MULTILINE | re.DOTALL)
    if tabs:
        names = re.findall(r"^ {8}name (.*)$", tabs[1], re.MULTILINE)
        if len(names) > 1:
            return "has more than one tab"
        if names and names[0] != json.dumps(DEFAULT_TAB_NAME):
            return "has a renamed tab"
    return None


def zellij_cache_dir() -> Path:
    """Where zellij keeps its cache, which differs by operating system."""
    if sys.platform == "darwin":
        return Path.home() / "Library/Caches/org.Zellij-Contributors.Zellij"
    base = os.environ.get("XDG_CACHE_HOME")
    return (Path(base) if base else Path.home() / ".cache") / "zellij"


def read_metadata(name: str) -> str | None:
    """The text of a running session's metadata file, or None if there is none to be read.

    The folder above `session_info` is named for a version of zellij's file format, and folders
    from earlier versions are left behind, so the most recently written file is the one used.
    """
    try:
        files = list(zellij_cache_dir().glob(f"*/session_info/{glob.escape(name)}/{METADATA_FILE}"))
        newest = max(files, key=lambda path: path.stat().st_mtime, default=None)
        return None if newest is None else newest.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


class Budget:
    """The time a run may still spend; unlimited unless given a number of seconds."""

    def __init__(self, seconds: float | None = None) -> None:
        """Start the clock."""
        self._deadline = None if seconds is None else time.monotonic() + seconds

    def remaining(self) -> float:
        """Seconds left; zero or less means out of time."""
        if self._deadline is None:
            return float("inf")
        return self._deadline - time.monotonic()


UNLIMITED = Budget()


def run_zellij(
    zellij: str,
    args: list[str],
    *,
    timeout: float = QUERY_TIMEOUT_SECONDS,
    budget: Budget = UNLIMITED,
) -> Result:
    """Run `zellij <args>`; a non-zero exit, a timeout, and a failure to start are all failures."""
    remaining = budget.remaining()
    if remaining <= 0:
        return Result(None, "out of time")
    timeout = min(timeout, remaining)
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
        return Result(None, f"timed out after {timeout:.1f}s")
    except (OSError, subprocess.SubprocessError) as error:
        return Result(None, f"could not run: {error}")
    if result.returncode != 0:
        # zellij reports some errors on stdout, so take the first line of whichever has one.
        detail = (result.stderr.strip() or result.stdout.strip()).partition("\n")[0][:200]
        return Result(None, f"exit {result.returncode}" + (f": {detail}" if detail else ""))
    return Result(result.stdout)


# A chain of early exits, each naming one reason, reads better than one expression.
def keep_reason(  # noqa: PLR0911
    zellij: str, session: Session, *, min_age_seconds: float, budget: Budget = UNLIMITED
) -> str | None:
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
    # Then the session's own metadata file, which costs no zellij command at all.
    metadata = read_metadata(session.name)
    if metadata is not None and (reason := metadata_keep_reason(metadata)):
        return f"{reason}, by its metadata file"
    outputs = []
    for action in (["list-clients"], ["list-panes", "--json", "--all"], ["list-tabs", "--json"]):
        query = ["--session", session.name, "action", *action]
        result = run_zellij(zellij, query, budget=budget)
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
    base = os.environ.get(variable)
    return (Path(base) if base else Path.home() / fallback) / "zellij-gc"


@contextlib.contextmanager
def run_log() -> Iterator[logging.Logger]:
    """The size-capped GC log, open for one run; a log that can't be opened swallows its lines.

    Only ever used while holding the collector lock, so rotation cannot race another writer.
    """
    logger = logging.getLogger("zellij-gc")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler: logging.Handler
    try:
        directory = xdg_dir("XDG_STATE_HOME", ".local/state")
        directory.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            directory / "gc.log", maxBytes=LOG_MAX_BYTES, backupCount=1, encoding="utf-8"
        )
    except OSError:
        handler = logging.NullHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%Y-%m-%dT%H:%M:%S%z"))
    logger.addHandler(handler)
    try:
        yield logger
    finally:
        logger.removeHandler(handler)
        handler.close()


def report_to_stderr(message: str) -> None:
    """Print a message for the person running a dry run."""
    print(f"zellij-gc: {message}", file=sys.stderr)


def notify_slow_run() -> None:
    """Tell whoever is waiting for their chooser what the wait is for."""
    print("zellij-gc: clearing out abandoned sessions (Ctrl-C to skip)...", flush=True)


@dataclass(slots=True)
class Tally:
    """What a run has done so far, kept as it goes so that an interrupted run can still say."""

    listed: int = 0
    unparsed: int = 0
    kept: int = 0
    deleted: int = 0
    failed: int = 0

    def summary(self, *, dry_run: bool) -> str:
        """The run's one-line report."""
        return (
            f"{self.listed} listed, {self.kept} kept, "
            f"{self.deleted} {'to delete' if dry_run else 'deleted'}, "
            f"{self.failed} failed to delete, {self.unparsed} unparsed lines"
        )


def delete(zellij: str, session: Session) -> Result:
    """Delete one abandoned session."""
    # Accepted race: a client could attach between the queries that found the session abandoned
    # and this delete. It follows them directly, so the window is a few subprocess calls long, and
    # what would be lost is a welcome screen holding no work.
    #
    # --force kills the server first, and deleting (not just killing) leaves nothing to resurrect.
    command = ["delete-session", "--force", session.name]
    return run_zellij(zellij, command, timeout=DELETE_TIMEOUT_SECONDS)


def collect(zellij: str, *, dry_run: bool, report: Callable[[str], None]) -> int:
    """Delete (or, for a dry run, print) every abandoned session. Returns the process exit status.

    A dry run prints the deletions on stdout and reports its reasoning. A real run reports one
    line per deletion plus one for the run, and prints only if it turns out to be slow.
    """
    # A dry run is a diagnostic, so it takes as long as it takes.
    budget = UNLIMITED if dry_run else Budget(BUDGET_SECONDS)
    notice = threading.Timer(NOTICE_AFTER_SECONDS, notify_slow_run)
    notice.daemon = True
    if not dry_run:
        notice.start()
    tally = Tally()
    try:
        return collect_within(zellij, tally, dry_run=dry_run, report=report, budget=budget)
    except KeyboardInterrupt:
        report(f"run: interrupted after {tally.summary(dry_run=dry_run)}")
        return EXIT_INTERRUPTED
    finally:
        notice.cancel()


def collect_within(
    zellij: str, tally: Tally, *, dry_run: bool, report: Callable[[str], None], budget: Budget
) -> int:
    """Do the work of `collect`, inside its time budget, keeping the tally as it goes."""
    min_age_seconds = min_age_seconds_from_env()
    if min_age_seconds is None:
        report(
            f"invalid ZELLIJ_GC_MIN_AGE_HOURS={os.environ.get('ZELLIJ_GC_MIN_AGE_HOURS')!r} "
            "(want a number of hours, 0 or more); nothing deleted"
        )
        return 1
    listing = run_zellij(zellij, ["list-sessions", "--no-formatting"], budget=budget)
    if listing.stdout is None:
        # Not an error in itself: zellij also exits non-zero when there are no sessions at all.
        report(f"run: no sessions listed ({listing.failure})")
        return 0

    sessions = parse_sessions(listing.stdout)
    tally.listed = len(sessions)
    tally.unparsed = sum(1 for line in listing.stdout.splitlines() if line.strip()) - len(sessions)

    # One session at a time, oldest first, as zellij lists them. Every zellij command makes every
    # server on the machine answer a probe, so running several at once mostly makes them contend.
    for session in sessions:
        name = session.name
        age = f"age {session.age_seconds}s"
        reason = keep_reason(zellij, session, min_age_seconds=min_age_seconds, budget=budget)
        if reason is not None:
            tally.kept += 1
            if dry_run:
                report(f"kept {name!r}: {reason}")
        elif dry_run:
            # Shell-quoted, so a name with spaces or parens can be pasted back into a shell.
            print(shlex.join([zellij, "delete-session", "--force", name]))
            tally.deleted += 1
        else:
            # Reported as each one happens, so that the log holds it whatever comes next.
            result = delete(zellij, session)
            if result.stdout is None:
                report(f"FAILED to delete {name!r} ({age}): {result.failure}")
                tally.failed += 1
            else:
                report(f"deleted {name!r} ({age})")
                tally.deleted += 1
    report(f"run: {tally.summary(dry_run=dry_run)}")
    return 1 if tally.failed else 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse the command line; anything unrecognised exits with status 2, zellij untouched."""
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


# Each way a run can end without collecting (disabled, lock unusable, lock busy, crashed) is its
# own early return.
def main(argv: list[str] | None = None) -> int:  # noqa: PLR0911
    """Run the collector; returns the process exit status."""
    dry_run = parse_args(argv).dry_run
    zellij = os.environ.get("ZELLIJ_GC_ZELLIJ") or "zellij"
    disabled = bool(os.environ.get("ZELLIJ_GC_DISABLE"))
    if dry_run:
        # A preview deletes nothing, so the switch that stops real runs doesn't stop it.
        if disabled:
            report_to_stderr("ZELLIJ_GC_DISABLE is set, so a real run would do nothing")
        return collect(zellij, dry_run=True, report=report_to_stderr)
    if disabled:
        return 0

    # One collector at a time: several terminals opening at once must not race on deletions, and
    # none of them waits for another's run. Failures here go to stderr, which zellij-welcome
    # keeps, since the log needs the lock.
    directory = xdg_dir("XDG_CACHE_HOME", ".cache")
    with contextlib.ExitStack() as stack:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            lock = stack.enter_context((directory / "lock").open("w", encoding="utf-8"))
        except OSError as error:
            report_to_stderr(f"cannot open the lock in {directory}: {error}")
            return 1
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0  # Another collector is running, and it will do the work.
        except OSError as error:
            report_to_stderr(f"cannot lock {lock.name}: {error}")
            return 1
        logger = stack.enter_context(run_log())
        try:
            return collect(zellij, dry_run=False, report=logger.info)
        except Exception:  # Recorded, not hidden: the screen is about to be cleared by zellij.
            logger.exception("run: crashed")
            return 1
