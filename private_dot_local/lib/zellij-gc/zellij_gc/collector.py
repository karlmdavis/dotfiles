"""zellij-gc core: session parsing, abandonment classification, and deletion.

Parsing and classification are pure functions, unit-tested directly. Everything that touches the
environment, the zellij CLI, or the filesystem sits in the I/O layer below them, which is tested
end to end against a fake `zellij`.

A session is abandoned when it never got past the welcome screen and nobody is looking at it: it is
running, older than the minimum age, and has no clients, no terminal panes, the welcome-screen
plugin, and a single default tab. Such a session holds no user state, so its name plays no part.
Every doubt (a failed, timed-out, or unparseable query) resolves to "keep the session".

A real run happens while a terminal waits for its chooser, so it is built to be quick. Every
zellij command probes every session on the machine before it does anything else, so commands are
what cost time, and the run avoids them: it first reads the metadata file that each zellij server
keeps about itself, and sessions which that shows to be in use are kept without a single query.
The file is only ever a reason to keep a session. One that looks abandoned, or has no readable
file, is put to zellij itself, and nothing is deleted on the file's word. That is the slow part, so
the run names each such session on the terminal as it comes to it, and Ctrl-C ends the run.

What a run did goes to a size-capped log, since zellij clears the screen straight afterwards.
Every run that gets the lock leaves at least one line there, which is what tells "nothing to do"
apart from "broken". Nothing is deleted that cannot be put on record there.

POSIX only: the lock is `fcntl.flock`, and the shim's shebang needs an `env` that has `-S`.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import functools
import glob
import json
import logging
import logging.handlers
import os
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

DEFAULT_MIN_AGE_HOURS = 1.0
# A healthy zellij answers in well under a second, and a session that doesn't answer is waited
# for again on every launch until someone deals with it, so the wait is kept short.
QUERY_TIMEOUT_SECONDS = 2
# How long a deletion is waited for. One that takes longer is left to finish, never killed.
DELETE_WAIT_SECONDS = 15
# The conventional exit status for "ended by Ctrl-C".
EXIT_INTERRUPTED = 130
# gc.log is rotated to a single gc.log.1 before it would pass this size.
LOG_MAX_BYTES = 256 * 1024

METADATA_FILE = "session-metadata.kdl"
# What zellij says, with a non-zero exit, when there are no sessions at all.
NO_SESSIONS = "No active zellij sessions"
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
    # Whether zellij ran and answered, whatever its answer: False for a timeout or a failure to
    # start it, neither of which says anything about the sessions.
    answered: bool = True


@dataclass(frozen=True, slots=True)
class Kept:
    """Why a session is kept. `undecided` when that is for want of an answer about it."""

    reason: str
    undecided: bool = False


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


class RunFailedError(Exception):
    """The run cannot go on, and has already reported why."""


def run_zellij(zellij: str, args: list[str]) -> Result:
    """Run `zellij <args>`; a non-zero exit, a timeout, and a failure to start are all failures."""
    timeout = QUERY_TIMEOUT_SECONDS
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
        return Result(None, f"timed out after {timeout}s", answered=False)
    except (OSError, subprocess.SubprocessError) as error:
        return Result(None, f"could not run: {error}", answered=False)
    if result.returncode != 0:
        # zellij reports some errors on stdout, so take the first line of whichever has one.
        detail = (result.stderr.strip() or result.stdout.strip()).partition("\n")[0][:200]
        return Result(None, f"exit {result.returncode}" + (f": {detail}" if detail else ""))
    return Result(result.stdout)


# A chain of early exits, each naming one reason, reads better than one expression.
def keep_reason(  # noqa: PLR0911
    zellij: str,
    session: Session,
    *,
    min_age_seconds: float,
    before_asking: Callable[[], None] = lambda: None,
) -> Kept | None:
    """Why a session is kept, or None if it is abandoned; any failed query means it is kept.

    `before_asking` is called if the session has to be put to zellij, which is the slow part.
    """
    # Cheap checks first, so sessions that can't qualify are never queried.
    if session.exited:
        return Kept("exited")
    if session.current:
        return Kept("current session")
    if session.age_seconds is None:
        return Kept("age unreadable", undecided=True)
    if session.age_seconds < min_age_seconds:
        return Kept("younger than the minimum age")
    # Then the session's own metadata file, which costs no zellij command at all.
    metadata = read_metadata(session.name)
    if metadata is not None and (reason := metadata_keep_reason(metadata)):
        return Kept(f"{reason}, by its metadata file")
    before_asking()
    outputs = []
    for action in (["list-clients"], ["list-panes", "--json", "--all"], ["list-tabs", "--json"]):
        query = ["--session", session.name, "action", *action]
        result = run_zellij(zellij, query)
        if result.stdout is None:
            return Kept(f"{action[0]} failed ({result.failure})", undecided=True)
        # A session in use is settled by the first query; skip the other two.
        if action == ["list-clients"] and count_clients(result.stdout):
            return Kept("client attached")
        outputs.append(result.stdout)
    if not is_abandoned(session, *outputs, min_age_seconds=min_age_seconds):
        return Kept("not a bare welcome screen")
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


class Reporter:
    """Where a run says what it did. This one is for a dry run: everything goes to stderr."""

    @property
    def broken(self) -> bool:
        """Whether what is reported can no longer be recorded."""
        return False

    def note(self, message: str) -> None:
        """Report something that happened."""
        print(f"zellij-gc: {message}", file=sys.stderr)

    def problem(self, message: str) -> None:
        """Report something that went wrong."""
        self.note(message)


class RecordingHandler(logging.handlers.RotatingFileHandler):
    """The GC log, which remembers a failure to write to it instead of printing a traceback."""

    failure: BaseException | None = None

    def handleError(self, record: logging.LogRecord) -> None:  # noqa: N802 (the base class's name)
        """Remember why the record could not be written."""
        del record
        self.failure = sys.exception()


class LogReporter(Reporter):
    """For a real run: everything goes to the GC log, and problems go to stderr as well.

    zellij-welcome keeps the stderr of a run that fails, so a problem reported here is what
    `last-failure.log` will say.
    """

    def __init__(self, logger: logging.Logger, handler: RecordingHandler) -> None:
        """Report through a logger whose one handler is the GC log."""
        self._logger = logger
        self._handler = handler

    @property
    def broken(self) -> bool:
        """Whether a line could not be written to the log."""
        return self._handler.failure is not None

    def note(self, message: str) -> None:
        """Log something that happened."""
        self._logger.info(message)

    def problem(self, message: str) -> None:
        """Log something that went wrong, and say so on stderr."""
        self._logger.error(message)
        print(f"zellij-gc: {message}", file=sys.stderr)


@contextlib.contextmanager
def run_log() -> Iterator[LogReporter]:
    """The size-capped GC log, open for one run. Raises OSError if it cannot be opened.

    Only ever used while holding the collector lock, so rotation cannot race another writer.
    """
    directory = xdg_dir("XDG_STATE_HOME", ".local/state")
    directory.mkdir(parents=True, exist_ok=True)
    handler = RecordingHandler(
        directory / "gc.log", maxBytes=LOG_MAX_BYTES, backupCount=1, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%Y-%m-%dT%H:%M:%S%z"))
    logger = logging.getLogger("zellij-gc")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.addHandler(handler)
    try:
        yield LogReporter(logger, handler)
    finally:
        logger.removeHandler(handler)
        handler.close()


class Progress:
    """What a real run shows whoever is waiting for their chooser: each session it asks about.

    A run with nobody to ask about shows nothing, and that is the usual run. zellij clears the
    screen when it starts, so this is for reading while it happens; the log is the record.
    """

    def __init__(self, *, shown: bool) -> None:
        """Show progress, or for a dry run (which has output of its own) do not."""
        self._shown = shown
        self._begun = False
        self._asking = False

    def asking(self, name: str) -> None:
        """Say that zellij is about to be asked about a session."""
        if self._shown:
            if not self._begun:
                print("zellij-gc: clearing out abandoned sessions (Ctrl-C to skip)")
            print(f"  {name}: ", end="", flush=True)
            self._begun = self._asking = True

    def outcome(self, text: str) -> None:
        """Say what became of the session, if it is one that zellij was asked about."""
        if self._asking:
            print(text, flush=True)
            self._asking = False


@dataclass(slots=True)
class Tally:
    """What a run has done so far, kept as it goes so that an interrupted run can still say."""

    listed: int = 0
    kept: int = 0
    undecided: int = 0
    deleted: int = 0
    failed: int = 0
    unparsed: int = 0
    first_undecided: str = ""
    first_unparsed: str = ""

    def summary(self, *, dry_run: bool) -> str:
        """The run's one-line report.

        Sessions kept for want of an answer are counted apart from those kept for a reason, with
        an example, since a collector that can never decide is a broken one.
        """
        counts = (
            f"{self.listed} listed, {self.kept} kept, {self.undecided} undecided, "
            f"{self.deleted} {'to delete' if dry_run else 'deleted'}, "
            f"{self.failed} failed to delete, {self.unparsed} unparsed lines"
        )
        examples = [
            f"first {what}: {example}"
            for what, example in (
                ("undecided", self.first_undecided),
                ("unparsed line", self.first_unparsed),
            )
            if example
        ]
        return "; ".join([counts, *examples])


@contextlib.contextmanager
def signals_held() -> Iterator[None]:
    """Hold back Ctrl-C, hangup, and termination until the block is done, then let them in.

    With handlers, not a signal mask: a mask covers only the thread that sets it, and a signal sent
    to the process is taken by any thread that lets it in. Python runs handlers in the main thread
    whichever thread the signal reached.
    """
    arrived: list[int] = []
    held = (signal.SIGINT, signal.SIGHUP, signal.SIGTERM)
    before = [
        signal.signal(held_signal, lambda number, _frame: arrived.append(number))
        for held_signal in held
    ]
    try:
        yield
    finally:
        for held_signal, handler in zip(held, before, strict=True):
            signal.signal(held_signal, handler)
        for number in arrived:
            signal.raise_signal(number)


def delete(zellij: str, session: Session) -> Result:
    """Delete one abandoned session, without any way of cutting the deletion short.

    `zellij delete-session --force` tells the server to quit and then removes the session's saved
    state, as two separate steps. Stopped between them, it leaves a session that has exited but
    can be resurrected, which nothing here would ever clear up. So, once started, it is never
    killed: not by a timeout, and not by a signal. Call this with
    signals held, so that this process stays to see it through; the command itself gets a session
    of its own, out of reach of whatever the terminal sends. If it outlasts the wait it is left
    running, and its output goes to a file, not a pipe, so that it can finish after this process
    has gone.
    """
    # Accepted race: a client could attach between the queries that found the session abandoned
    # and this delete. It follows them directly, so the window is a few subprocess calls long, and
    # what would be lost is a welcome screen holding no work.
    command = [zellij, "delete-session", "--force", session.name]
    with tempfile.TemporaryFile() as output:
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        except OSError as error:
            return Result(None, f"could not run: {error}")
        try:
            status = process.wait(timeout=DELETE_WAIT_SECONDS)
        except subprocess.TimeoutExpired:
            return Result(None, f"still running after {DELETE_WAIT_SECONDS}s, and left to finish")
        output.seek(0)
        text = output.read().decode("utf-8", errors="replace")
    if status != 0:
        detail = text.strip().partition("\n")[0][:200]
        return Result(None, f"exit {status}" + (f": {detail}" if detail else ""))
    return Result(text)


def delete_on_record(zellij: str, session: Session, tally: Tally, reporter: Reporter) -> str:
    """Delete one abandoned session, reporting it before and after. Returns what became of it."""
    name = session.name
    age = f"age {session.age_seconds}s"
    # Signals are held until the deletion is over and on record. It is announced first, which
    # leaves a trace of one that this process does not live to see the end of, and shows that the
    # log can be written before anything is deleted.
    with signals_held():
        reporter.note(f"deleting {name!r} ({age})")
        if reporter.broken:
            return "not deleted, as the log cannot be written"
        result = delete(zellij, session)
        if result.stdout is None:
            reporter.problem(f"FAILED to delete {name!r} ({age}): {result.failure}")
            tally.failed += 1
            return f"could not be deleted ({result.failure})"
        reporter.note(f"deleted {name!r} ({age})")
        tally.deleted += 1
        return "deleted"


def list_sessions(zellij: str, tally: Tally, reporter: Reporter) -> list[Session]:
    """The sessions zellij lists, counted into the tally. Raises RunFailedError if it cannot say."""
    listing = run_zellij(zellij, ["list-sessions", "--no-formatting"])
    if listing.stdout is None:
        # zellij exits non-zero when there are no sessions at all, which is no failure.
        if listing.answered and NO_SESSIONS in listing.failure:
            return []
        reporter.problem(f"run: could not list the sessions ({listing.failure})")
        raise RunFailedError
    sessions = parse_sessions(listing.stdout)
    lines = [line for line in listing.stdout.splitlines() if line.strip()]
    tally.listed = len(sessions)
    tally.unparsed = len(lines) - len(sessions)
    tally.first_unparsed = next(
        (repr(line[:200]) for line in lines if not SESSION_LINE.match(line.rstrip())), ""
    )
    return sessions


def collect(zellij: str, *, dry_run: bool, reporter: Reporter) -> int:
    """Delete (or, for a dry run, print) every abandoned session. Returns the process exit status.

    A dry run prints the deletions on stdout and reports its reasoning. A real run reports two
    lines per deletion plus one for the run, and shows its progress on stdout.
    """
    tally = Tally()
    try:
        return collect_into(tally, zellij, dry_run=dry_run, reporter=reporter)
    except KeyboardInterrupt:
        reporter.note(f"run: interrupted after {tally.summary(dry_run=dry_run)}")
        return EXIT_INTERRUPTED


def collect_into(tally: Tally, zellij: str, *, dry_run: bool, reporter: Reporter) -> int:
    """Do the work of `collect`, keeping the tally as it goes."""
    min_age_seconds = min_age_seconds_from_env()
    if min_age_seconds is None:
        reporter.problem(
            f"invalid ZELLIJ_GC_MIN_AGE_HOURS={os.environ.get('ZELLIJ_GC_MIN_AGE_HOURS')!r} "
            "(want a number of hours, 0 or more); nothing deleted"
        )
        return 1
    try:
        sessions = list_sessions(zellij, tally, reporter)
    except RunFailedError:
        return 1

    # One session at a time, oldest first, as zellij lists them. Every zellij command makes every
    # server on the machine answer a probe, so running several at once mostly makes them contend.
    progress = Progress(shown=not dry_run)
    for session in sessions:
        name = session.name
        kept = keep_reason(
            zellij,
            session,
            min_age_seconds=min_age_seconds,
            before_asking=functools.partial(progress.asking, name),
        )
        if kept is not None:
            if kept.undecided:
                tally.undecided += 1
                tally.first_undecided = tally.first_undecided or f"{name!r}, {kept.reason}"
            else:
                tally.kept += 1
            if dry_run:
                reporter.note(f"kept {name!r}: {kept.reason}")
            progress.outcome(f"kept ({kept.reason})")
        elif dry_run:
            # Shell-quoted, so a name with spaces or parens can be pasted back into a shell.
            print(shlex.join([zellij, "delete-session", "--force", name]))
            tally.deleted += 1
        else:
            progress.outcome(delete_on_record(zellij, session, tally, reporter))
            if reporter.broken:
                break
    reporter.note(f"run: {tally.summary(dry_run=dry_run)}")
    if reporter.broken:
        # Being unable to record a deletion is a doubt like any other, so it stops them.
        print("zellij-gc: the log cannot be written, so no more was deleted", file=sys.stderr)
        return 1
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


# Each way a run can end without collecting (disabled, lock unusable, lock busy, log unusable,
# crashed) is its own early return.
def main(argv: list[str] | None = None) -> int:  # noqa: PLR0911
    """Run the collector; returns the process exit status."""
    dry_run = parse_args(argv).dry_run
    zellij = os.environ.get("ZELLIJ_GC_ZELLIJ") or "zellij"
    disabled = bool(os.environ.get("ZELLIJ_GC_DISABLE"))
    if dry_run:
        # A preview deletes nothing, so the switch that stops real runs doesn't stop it.
        if disabled:
            Reporter().note("ZELLIJ_GC_DISABLE is set, so a real run would do nothing")
        return collect(zellij, dry_run=True, reporter=Reporter())
    if disabled:
        return 0

    # One collector at a time: several terminals opening at once must not race on deletions, and
    # none of them waits for another's run. A failure to take the lock, or to open the log, goes
    # to stderr alone: the log may only be written while holding the lock. zellij-welcome keeps
    # the stderr of a run that fails.
    directory = xdg_dir("XDG_CACHE_HOME", ".cache")
    with contextlib.ExitStack() as stack:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            lock = stack.enter_context((directory / "lock").open("w", encoding="utf-8"))
        except OSError as error:
            Reporter().problem(f"cannot open the lock in {directory}: {error}")
            return 1
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0  # Another collector is running, and it will do the work.
        except OSError as error:
            Reporter().problem(f"cannot lock {lock.name}: {error}")
            return 1
        try:
            reporter = stack.enter_context(run_log())
        except OSError as error:
            # Nothing is deleted that cannot be put on record.
            Reporter().problem(f"cannot open the log, so nothing was deleted: {error}")
            return 1
        try:
            return collect(zellij, dry_run=False, reporter=reporter)
        except Exception:  # Recorded, not hidden: the screen is about to be cleared by zellij.
            reporter.problem(f"run: crashed\n{traceback.format_exc().rstrip()}")
            return 1
