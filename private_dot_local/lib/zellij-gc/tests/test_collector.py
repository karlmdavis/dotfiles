"""Unit tests for zellij-gc parsing, classification, and the dry-run/deletion flow.

Pure helpers are tested directly. The end-to-end tests drive main() against a fake `zellij`
executable (the ZELLIJ_GC_ZELLIJ seam) that replays canned output and records the calls it
receives; no mocking framework.
"""

from __future__ import annotations

import fcntl
import json
import os
import shlex
import shutil
import signal
import subprocess
import textwrap
import threading
import time
from pathlib import Path

import pytest

from zellij_gc import collector
from zellij_gc.collector import Session, is_abandoned, parse_age, parse_sessions

HOUR = 3600

NO_CLIENTS = "CLIENT_ID ZELLIJ_PANE_ID RUNNING_COMMAND\n"
ONE_CLIENT = NO_CLIENTS + "1         plugin_1       zellij:session-manager\n"

WELCOME_PANES = json.dumps(
    [
        {"id": 0, "is_plugin": True, "plugin_url": "zellij:link", "terminal_command": None},
        {"id": 1, "is_plugin": True, "plugin_url": "welcome-screen", "terminal_command": None},
    ]
)
WORKING_PANES = json.dumps(
    [
        {"id": 0, "is_plugin": True, "plugin_url": "zellij:link"},
        {"id": 18, "is_plugin": False, "plugin_url": None, "title": "~/.local/share/chezmoi"},
    ]
)
# A shell opened beside the chooser: the welcome plugin is still there, but so is a terminal.
WELCOME_PLUS_TERMINAL_PANES = json.dumps(
    [
        {"id": 0, "is_plugin": True, "plugin_url": "zellij:link", "terminal_command": None},
        {"id": 1, "is_plugin": True, "plugin_url": "welcome-screen", "terminal_command": None},
        {"id": 0, "is_plugin": False, "plugin_url": None, "title": "~/work"},
    ]
)
DEFAULT_TABS = json.dumps([{"position": 0, "name": "Tab #1", "tab_id": 0}])

STALE = Session(name="brave-petunia", age_seconds=5 * HOUR)


def abandoned(session=STALE, clients=NO_CLIENTS, panes=WELCOME_PANES, tabs=DEFAULT_TABS):
    return is_abandoned(session, clients, panes, tabs, min_age_seconds=HOUR)


# --- parse_age ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Between them, every unit spelling that zellij prints.
        ("1year 1month 1day 20h 9m 36s", 31557600 + 2630016 + 86400 + 20 * HOUR + 9 * 60 + 36),
        ("2years 3months 25days", 2 * 31557600 + 3 * 2630016 + 25 * 86400),
    ],
)
def test_parse_age(text, expected):
    assert parse_age(text) == expected


@pytest.mark.parametrize("text", ["", "3 fortnights", "5m and change", "1w", "2hrs 5m"])
def test_parse_age_rejects_unknown_shapes(text):
    assert parse_age(text) is None


# --- parse_sessions -------------------------------------------------------------------------


def test_parse_sessions_reads_names_ages_and_flags():
    listing = textwrap.dedent(
        """\
        justdavis (monorepo) [Created 4months 3h 13m 45s ago]
        dotfiles [Created 3months 25days 20h 37m 19s ago] (current)
        brave-petunia [Created 3months 25days 20h 9m 36s ago]
        verdant-yak [Created 4months 3days 2h 20m 16s ago] (EXITED - attach to resurrect)
        """
    )
    assert parse_sessions(listing) == [
        Session("justdavis (monorepo)", 4 * 2630016 + 3 * HOUR + 13 * 60 + 45),
        Session("dotfiles", parse_age("3months 25days 20h 37m 19s"), current=True),
        Session("brave-petunia", parse_age("3months 25days 20h 9m 36s")),
        Session("verdant-yak", parse_age("4months 3days 2h 20m 16s"), exited=True),
    ]


def test_parse_sessions_anchors_on_the_last_created_marker():
    [session] = parse_sessions("odd [Created 1h ago] name [Created 2h ago] \n")
    assert session == Session("odd [Created 1h ago] name", 2 * HOUR)


def test_parse_sessions_keeps_a_session_whose_age_is_unreadable():
    assert parse_sessions("x [Created a while ago]\n") == [Session("x", None)]


# --- is_abandoned ---------------------------------------------------------------------------


def test_unattended_welcome_screen_is_abandoned():
    assert abandoned()


@pytest.mark.parametrize(
    "session",
    [
        Session("young", 10 * 60),
        Session("unknown-age", None),
        Session("dead", 5 * HOUR, exited=True),
        Session("mine", 5 * HOUR, current=True),
    ],
)
def test_sessions_kept_on_their_listing_alone(session):
    assert not abandoned(session=session)


def test_age_threshold_is_inclusive():
    assert abandoned(session=Session("edge", HOUR))


@pytest.mark.parametrize("clients", [ONE_CLIENT, "", "unexpected output\n"])
def test_kept_when_a_client_is_attached_or_clients_are_unreadable(clients):
    assert not abandoned(clients=clients)


@pytest.mark.parametrize(
    "panes",
    [
        WORKING_PANES,
        WELCOME_PLUS_TERMINAL_PANES,
        json.dumps([{"is_plugin": True, "plugin_url": "file:/x/not-welcome-screen.wasm"}]),
        "[]",
        "not json",
        "null",
        '["welcome-screen"]',
        json.dumps([{"plugin_url": "welcome-screen"}]),
        json.dumps([{"is_plugin": "true", "plugin_url": "welcome-screen"}]),
    ],
)
def test_kept_unless_panes_are_exactly_a_welcome_screen(panes):
    assert not abandoned(panes=panes)


@pytest.mark.parametrize(
    "tabs",
    [
        "[]",
        "not json",
        json.dumps([{"name": "scratch"}]),
        json.dumps([{"name": "Tab #1"}, {"name": "Tab #2"}]),
        json.dumps([{"position": 0}]),
    ],
)
def test_kept_unless_there_is_a_single_default_tab(tabs):
    assert not abandoned(tabs=tabs)


# --- min_age_seconds_from_env ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, HOUR),
        ("  ", HOUR),
        ("0", 0),
        ("0.5", HOUR / 2),
        ("24h", None),
        ("-2", None),
        ("nan", None),
        ("inf", None),
    ],
)
def test_min_age_from_env(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv("ZELLIJ_GC_MIN_AGE_HOURS", raising=False)
    else:
        monkeypatch.setenv("ZELLIJ_GC_MIN_AGE_HOURS", value)
    assert collector.min_age_seconds_from_env() == expected


# --- End to end, against a fake zellij ------------------------------------------------------

# Two sessions are abandoned: `brave-petunia`, named as zellij generates names, and `stale one`,
# which no generator would produce. Both must go: the signature decides, not the name.
LISTING = textwrap.dedent(
    """\
    dotfiles [Created 3months 25days 20h 37m 19s ago]
    brave-petunia [Created 3months 25days 20h 9m 36s ago]
    outstanding-cowbell [Created 2days 20h 7m 13s ago]
    stale one [Created 5h 1m ago]
    shell-beside-chooser [Created 6h ago]
    didactic-river [Created 23m 51s ago]
    verdant-yak [Created 4months 3days 2h 20m 16s ago] (EXITED - attach to resurrect)
    """
)

# Per-session replies; a session missing a reply makes the fake exit non-zero for that query.
REPLIES = {
    "dotfiles": {
        "list-clients": ONE_CLIENT,
        "list-panes": WORKING_PANES,
        "list-tabs": json.dumps([{"name": "claude-settings"}, {"name": "shortcuts"}]),
    },
    "brave-petunia": {
        "list-clients": NO_CLIENTS,
        "list-panes": WELCOME_PANES,
        "list-tabs": DEFAULT_TABS,
    },
    "outstanding-cowbell": {
        "list-clients": ONE_CLIENT,
        "list-panes": WELCOME_PANES,
        "list-tabs": DEFAULT_TABS,
    },
    "stale one": {
        "list-clients": NO_CLIENTS,
        "list-panes": WELCOME_PANES,
        "list-tabs": DEFAULT_TABS,
    },
    "shell-beside-chooser": {
        "list-clients": NO_CLIENTS,
        "list-panes": WELCOME_PLUS_TERMINAL_PANES,
        "list-tabs": DEFAULT_TABS,
    },
    "didactic-river": {
        "list-clients": NO_CLIENTS,
        "list-panes": WELCOME_PANES,
        "list-tabs": DEFAULT_TABS,
    },
}

# A shell script, since a run makes a dozen calls and a shell starts ten times faster than Python.
# What it is to answer is laid out as files beside it by FakeZellij.configure().
FAKE_ZELLIJ = r"""#!/bin/sh
here=${0%/*}
# Builtins only on the paths every call takes: on a busy machine each spawn costs milliseconds.
show() { while IFS= read -r line || [ -n "$line" ]; do printf '%s\n' "$line"; done < "$1"; }
IFS='	'
printf '%s\n' "$*" >> "$here/calls"
IFS=' '

case $1 in
  --session) command="$2/$4" ;;
  *) command=$1 ;;
esac
# A delay for every command, or for one: "list-sessions", "delete-session", "<session>/<action>".
for delay in "$here/delays/all" "$here/delays/$command"; do
  [ -f "$delay" ] && read -r seconds < "$delay" && sleep "$seconds"
done

case $1 in
  list-sessions)
    [ -f "$here/listing" ] || { echo "No active zellij sessions found." >&2; exit 1; }
    show "$here/listing"
    ;;
  delete-session)
    read -r status < "$here/delete-status"
    if [ "$status" -ne 0 ]; then
      echo "Session: \"$3\" not found." >&2
      exit "$status"
    fi
    # A deletion that ran to its end says so, and whether it was out of the terminal's reach:
    # started in a session of its own, it leads its own process group.
    leads=no
    [ "$(ps -o pgid= -p $$ | tr -d ' ')" = "$$" ] && leads=yes
    printf '%s\t%s\n' "$3" "$leads" >> "$here/finished"
    echo "Session: \"$3\" successfully deleted."
    ;;
  --session)
    # As the real CLI: the JSON queries print a table, not JSON, unless asked for JSON.
    case $4 in
      list-panes | list-tabs) case " $* " in *" --json "*) ;; *) exit 2 ;; esac ;;
    esac
    [ -f "$here/replies/$2/$4" ] || exit 2
    show "$here/replies/$2/$4"
    ;;
  *) exit 64 ;;
esac
"""


class FakeZellij:
    def __init__(self, directory):
        self.directory = directory
        self.path = directory / "zellij"
        self.path.write_text(FAKE_ZELLIJ, encoding="utf-8")
        self.path.chmod(0o755)
        self.configure()

    def configure(self, listing=LISTING, replies=None, delete_status=0, sleep=0):
        """Lay out what the fake is to answer. `sleep` is seconds, or seconds by command."""
        for folder in ("replies", "delays"):
            shutil.rmtree(self.directory / folder, ignore_errors=True)
        (self.directory / "listing").unlink(missing_ok=True)
        if listing is not None:
            (self.directory / "listing").write_text(listing, encoding="utf-8")
        (self.directory / "delete-status").write_text(f"{delete_status}\n", encoding="utf-8")
        files = {
            f"replies/{name}/{action}": text
            for name, reply in (REPLIES if replies is None else replies).items()
            for action, text in reply.items()
        }
        delays = sleep if isinstance(sleep, dict) else {"all": sleep}
        files.update({f"delays/{command}": f"{seconds}\n" for command, seconds in delays.items()})
        for name, text in files.items():
            (self.directory / name).parent.mkdir(parents=True, exist_ok=True)
            (self.directory / name).write_text(text, encoding="utf-8")

    @property
    def quoted(self):
        """The fake's path as dry-run output prints it."""
        return shlex.quote(str(self.path))

    def _records(self, name):
        log = self.directory / name
        if not log.exists():
            return []
        return [line.split("\t") for line in log.read_text(encoding="utf-8").splitlines()]

    @property
    def calls(self):
        return self._records("calls")

    @property
    def deletions(self):
        return [call for call in self.calls if call[0] == "delete-session"]

    @property
    def finished_deletions(self):
        """What each deletion that ran to its end recorded about itself."""
        return [
            {"name": name, "leads_its_own_group": leads == "yes"}
            for name, leads in self._records("finished")
        ]

    def queried(self):
        return {call[1] for call in self.calls if call[0] == "--session"}

    def interrupt_at(self, command):
        """Send this process a real Ctrl-C once the fake has been asked to run `command`."""
        # A process started in the background by a shell without job control, as a test runner
        # may well be, starts out ignoring Ctrl-C. The `zellij` fixture puts back what it found.
        signal.signal(signal.SIGINT, signal.default_int_handler)

        def watch():
            while command not in self.calls:
                time.sleep(0.01)
            os.kill(os.getpid(), signal.SIGINT)

        threading.Thread(target=watch, daemon=True).start()


def write_metadata(name, *, clients=0, panes=((True, "welcome-screen"),), tabs=("Tab #1",)):
    """Write a session's metadata file as its zellij server would, in zellij's own layout."""
    lines = [f'name "{name}"', "tabs {"]
    for position, tab in enumerate(tabs):
        lines += ["    tab {", f"        position {position}", f'        name "{tab}"', "    }"]
    lines += ["}", "panes {"]
    for number, (is_plugin, plugin_url) in enumerate(panes):
        lines += [
            "    pane {",
            f"        id {number}",
            f"        is_plugin {str(is_plugin).lower()}",
        ]
        lines += [f'        plugin_url "{plugin_url}"'] if plugin_url else []
        lines += ["        tab_position 0", "    }"]
    lines += ["}", f"connected_clients {clients}", "creation_time 18000", ""]
    folder = collector.zellij_cache_dir() / "contract_version_1" / "session_info" / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / collector.METADATA_FILE).write_text("\n".join(lines), encoding="utf-8")
    return "\n".join(lines)


@pytest.fixture
def zellij(tmp_path, monkeypatch):
    """A fake zellij on the ZELLIJ_GC_ZELLIJ seam, with HOME and the XDG dirs isolated."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    for var in ("ZELLIJ_GC_DISABLE", "ZELLIJ_GC_MIN_AGE_HOURS"):
        monkeypatch.delenv(var, raising=False)
    # However loaded the machine is, only the test of a query that hangs should ever see a
    # command give up waiting.
    monkeypatch.setattr(collector, "QUERY_TIMEOUT_SECONDS", 60)
    directory = tmp_path / "fake"
    directory.mkdir()
    fake = FakeZellij(directory)
    monkeypatch.setenv("ZELLIJ_GC_ZELLIJ", str(fake.path))
    on_interrupt = signal.getsignal(signal.SIGINT)
    yield fake
    signal.signal(signal.SIGINT, on_interrupt)


def summary(listed, kept, deleted=0, *, dry_run=False, **others):
    """A run's one-line report, as far as its counts; `others` default to none."""
    counts = {"undecided": 0, "failed": 0, "unparsed": 0} | others
    return (
        f"{listed} listed, {kept} kept, {counts['undecided']} undecided, "
        f"{deleted} {'to delete' if dry_run else 'deleted'}, "
        f"{counts['failed']} failed to delete, {counts['unparsed']} unparsed lines"
    )


def gc_log(tmp_path):
    """The GC log's lines, without their timestamps."""
    path = tmp_path / "state" / "zellij-gc" / "gc.log"
    if not path.exists():
        return []
    return [line.partition(" ")[2] for line in path.read_text(encoding="utf-8").splitlines()]


def test_dry_run_prints_the_deletions_and_its_reasons_and_deletes_nothing(zellij, capsys, tmp_path):
    assert collector.main(["--dry-run"]) == 0
    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        f"{zellij.quoted} delete-session --force brave-petunia",
        f"{zellij.quoted} delete-session --force 'stale one'",
    ]
    assert zellij.deletions == []
    assert gc_log(tmp_path) == []
    assert captured.err.splitlines() == [
        "zellij-gc: kept 'dotfiles': client attached",
        "zellij-gc: kept 'outstanding-cowbell': client attached",
        "zellij-gc: kept 'shell-beside-chooser': not a bare welcome screen",
        "zellij-gc: kept 'didactic-river': younger than the minimum age",
        "zellij-gc: kept 'verdant-yak': exited",
        f"zellij-gc: run: {summary(7, 5, 2, dry_run=True)}",
    ]


def test_dry_run_names_plain_zellij_when_no_binary_is_configured(zellij, capsys, monkeypatch):
    monkeypatch.delenv("ZELLIJ_GC_ZELLIJ")
    monkeypatch.setenv("PATH", str(zellij.directory), prepend=":")
    assert collector.main(["--dry-run"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "zellij delete-session --force brave-petunia",
        "zellij delete-session --force 'stale one'",
    ]


@pytest.mark.parametrize("argv", [["--dry"], ["--dry-run=1"], ["-n"], ["--dry-run", "extra"]])
def test_unrecognised_arguments_never_touch_zellij(zellij, argv):
    with pytest.raises(SystemExit):
        collector.main(argv)
    assert zellij.calls == []


def test_deletes_only_abandoned_sessions_and_logs_them(zellij, capsys, tmp_path):
    assert collector.main([]) == 0
    assert zellij.deletions == [
        ["delete-session", "--force", "brave-petunia"],
        ["delete-session", "--force", "stale one"],
    ]
    # On the terminal: each session that zellij had to be asked about, and what became of it.
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.splitlines() == [
        "zellij-gc: clearing out abandoned sessions (Ctrl-C to skip)",
        "  dotfiles: kept (client attached)",
        "  brave-petunia: deleted",
        "  outstanding-cowbell: kept (client attached)",
        "  stale one: deleted",
        "  shell-beside-chooser: kept (not a bare welcome screen)",
    ]
    assert gc_log(tmp_path) == [
        f"deleting 'brave-petunia' (age {parse_age('3months 25days 20h 9m 36s')}s)",
        f"deleted 'brave-petunia' (age {parse_age('3months 25days 20h 9m 36s')}s)",
        f"deleting 'stale one' (age {parse_age('5h 1m')}s)",
        f"deleted 'stale one' (age {parse_age('5h 1m')}s)",
        f"run: {summary(7, 5, 2)}",
    ]


def test_ctrl_c_ends_the_run_and_what_was_already_deleted_is_on_record(zellij, tmp_path):
    """A real Ctrl-C, arriving part-way through the inspection of the second abandoned session."""
    zellij.configure(sleep={"stale one/list-tabs": 5})
    zellij.interrupt_at(["--session", "stale one", "action", "list-tabs", "--json"])
    assert collector.main([]) == 130
    assert zellij.deletions == [["delete-session", "--force", "brave-petunia"]]
    assert gc_log(tmp_path) == [
        f"deleting 'brave-petunia' (age {parse_age('3months 25days 20h 9m 36s')}s)",
        f"deleted 'brave-petunia' (age {parse_age('3months 25days 20h 9m 36s')}s)",
        f"run: interrupted after {summary(7, 2, 1)}",
    ]


def test_a_deletion_under_way_is_not_cut_short_by_ctrl_c(zellij, tmp_path):
    """The Ctrl-C arrives while the first deletion runs: that one finishes, and no other starts."""
    zellij.configure(sleep={"delete-session": 0.3})
    zellij.interrupt_at(["delete-session", "--force", "brave-petunia"])
    assert collector.main([]) == 130
    assert zellij.finished_deletions == [
        {
            "name": "brave-petunia",
            "leads_its_own_group": True,
        }
    ]
    assert zellij.deletions == [["delete-session", "--force", "brave-petunia"]]
    assert gc_log(tmp_path) == [
        f"deleting 'brave-petunia' (age {parse_age('3months 25days 20h 9m 36s')}s)",
        f"deleted 'brave-petunia' (age {parse_age('3months 25days 20h 9m 36s')}s)",
        f"run: interrupted after {summary(7, 1, 1)}",
    ]


def test_a_deletion_that_outlasts_the_wait_is_left_to_finish(zellij, tmp_path, monkeypatch):
    monkeypatch.setattr(collector, "DELETE_WAIT_SECONDS", 0.2)
    zellij.configure(listing="brave-petunia [Created 5h ago]\n", sleep={"delete-session": 0.5})
    assert collector.main([]) == 1
    assert gc_log(tmp_path)[:2] == [
        "deleting 'brave-petunia' (age 18000s)",
        "FAILED to delete 'brave-petunia' (age 18000s): still running after 0.2s, "
        "and left to finish",
    ]
    assert zellij.finished_deletions == []
    deadline = time.monotonic() + 5
    while not zellij.finished_deletions and time.monotonic() < deadline:
        time.sleep(0.02)
    assert [deletion["name"] for deletion in zellij.finished_deletions] == ["brave-petunia"]


# --- The metadata files ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("described", "expected"),
    [
        ({}, None),
        ({"clients": 2}, "client attached"),
        ({"panes": ((True, "welcome-screen"), (False, None))}, "has a terminal pane"),
        ({"tabs": ("Tab #1", "Tab #2")}, "has more than one tab"),
        ({"tabs": ("scratch",)}, "has a renamed tab"),
    ],
)
def test_metadata_is_only_ever_a_reason_to_keep(zellij, described, expected):
    assert collector.metadata_keep_reason(write_metadata("x", **described)) == expected


@pytest.mark.parametrize("text", ["", "not kdl at all", "connected_clients many\n", "{}"])
def test_metadata_that_makes_no_sense_is_no_reason_at_all(text):
    assert collector.metadata_keep_reason(text) is None


def test_sessions_in_use_by_their_metadata_cost_no_queries(zellij, tmp_path, capsys):
    write_metadata("dotfiles", clients=1, panes=((False, None),), tabs=("claude-settings",))
    write_metadata("outstanding-cowbell", clients=1)
    write_metadata("shell-beside-chooser", panes=((True, "welcome-screen"), (False, None)))
    assert collector.main([]) == 0
    assert zellij.queried() == {"brave-petunia", "stale one"}
    assert len(zellij.deletions) == 2
    # Nor are they named on the terminal, which is for what takes time.
    assert capsys.readouterr().out.splitlines() == [
        "zellij-gc: clearing out abandoned sessions (Ctrl-C to skip)",
        "  brave-petunia: deleted",
        "  stale one: deleted",
    ]
    assert gc_log(tmp_path)[-1] == f"run: {summary(7, 5, 2)}"


def test_a_run_with_nobody_to_ask_about_shows_nothing(zellij, capsys):
    """The usual run: every session is settled by its listing or by its metadata file."""
    for name in ("dotfiles", "brave-petunia", "outstanding-cowbell", "stale one"):
        write_metadata(name, clients=1)
    write_metadata("shell-beside-chooser", panes=((False, None),))
    assert collector.main([]) == 0
    assert zellij.queried() == set()
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")


def test_dry_run_says_when_the_metadata_decided(zellij, capsys):
    write_metadata("dotfiles", clients=1)
    collector.main(["--dry-run"])
    assert "zellij-gc: kept 'dotfiles': client attached, by its metadata file" in (
        capsys.readouterr().err.splitlines()
    )


def test_nothing_is_deleted_on_the_word_of_the_metadata(zellij):
    """Every file says abandoned, but zellij itself says two of these sessions are in use."""
    for name in REPLIES:
        write_metadata(name)
    assert collector.main([]) == 0
    assert zellij.queried() == set(REPLIES) - {"didactic-river"}
    assert zellij.deletions == [
        ["delete-session", "--force", "brave-petunia"],
        ["delete-session", "--force", "stale one"],
    ]


def test_metadata_is_read_from_the_newest_of_zellij_s_folders(zellij):
    """Folders for earlier versions of the file format are left behind, holding stale files."""
    current = write_metadata("dotfiles", clients=1)
    stale = collector.zellij_cache_dir() / "0.43.1" / "session_info" / "dotfiles"
    stale.mkdir(parents=True)
    (stale / collector.METADATA_FILE).write_text("connected_clients 0\n", encoding="utf-8")
    os.utime(stale / collector.METADATA_FILE, (0, 0))
    assert collector.read_metadata("dotfiles") == current
    assert collector.read_metadata("no-such-session") is None
    assert collector.read_metadata("*") is None


def test_a_run_with_nothing_to_delete_still_leaves_a_line(zellij, tmp_path):
    """Without it, a collector that never finds anything looks the same as one that never runs."""
    zellij.configure(listing="dotfiles [Created 5h ago]\nnot a session line\n")
    assert collector.main([]) == 0
    assert gc_log(tmp_path) == [
        f"run: {summary(1, 1, unparsed=1)}; first unparsed line: 'not a session line'",
    ]


def test_log_is_rotated_before_it_passes_its_size_cap(zellij, tmp_path, monkeypatch):
    monkeypatch.setattr(collector, "LOG_MAX_BYTES", 300)
    # The cheapest run: one zellij call and one log line (a little over 100 bytes).
    zellij.configure(listing=None)
    directory = tmp_path / "state" / "zellij-gc"
    for _ in range(6):  # Enough to rotate at least twice, so that gc.log.1 gets replaced.
        assert collector.main([]) == 0
    assert sorted(path.name for path in directory.iterdir()) == ["gc.log", "gc.log.1"]
    # Neither file ever exceeds the cap.
    assert all(0 < path.stat().st_size <= 300 for path in directory.iterdir())


def test_a_log_that_stops_taking_lines_stops_the_deletions(zellij, tmp_path, monkeypatch, capsys):
    """Here the log cannot be rotated. What cannot be put on record is not deleted."""
    monkeypatch.setattr(collector, "LOG_MAX_BYTES", 10)
    directory = tmp_path / "state" / "zellij-gc"
    (directory / "gc.log.1" / "in-the-way").mkdir(parents=True)
    (directory / "gc.log").write_text("a line from an earlier run\n", encoding="utf-8")
    assert collector.main([]) == 1
    assert zellij.deletions == []
    assert capsys.readouterr().err == (
        "zellij-gc: the log cannot be written, so no more was deleted\n"
    )


def test_a_crash_is_reported_with_its_traceback(zellij, tmp_path, monkeypatch, capsys):
    def explode(text):
        raise RuntimeError("boom")

    monkeypatch.setattr(collector, "parse_sessions", explode)
    assert collector.main([]) == 1
    log = gc_log(tmp_path)
    assert log[0] == "run: crashed"
    assert log[-1] == "boom"
    # On stderr as well, which is what zellij-welcome keeps of a run that failed.
    reported = capsys.readouterr().err.splitlines()
    assert reported[0] == "zellij-gc: run: crashed"
    assert reported[-1] == "RuntimeError: boom"


def test_queries_and_their_flags(zellij):
    """Young and exited sessions get no queries, and a session with a client only the first."""
    collector.main([])
    assert zellij.queried() == {
        "dotfiles",
        "brave-petunia",
        "outstanding-cowbell",
        "stale one",
        "shell-beside-chooser",
    }
    actions = {
        name: [call[3:] for call in zellij.calls if call[:2] == ["--session", name]]
        for name in ("dotfiles", "outstanding-cowbell", "brave-petunia")
    }
    assert actions == {
        "dotfiles": [["list-clients"]],
        "outstanding-cowbell": [["list-clients"]],
        "brave-petunia": [
            ["list-clients"],
            ["list-panes", "--json", "--all"],
            ["list-tabs", "--json"],
        ],
    }


def test_min_age_override_widens_the_net(zellij, capsys, monkeypatch):
    monkeypatch.setenv("ZELLIJ_GC_MIN_AGE_HOURS", "0")
    collector.main(["--dry-run"])
    expected = f"{zellij.quoted} delete-session --force didactic-river"
    assert expected in capsys.readouterr().out.splitlines()


def test_invalid_min_age_deletes_nothing_and_says_so(zellij, capsys, monkeypatch, tmp_path):
    """`24h` asks for longer retention; falling back to the 1h default would shorten it."""
    monkeypatch.setenv("ZELLIJ_GC_MIN_AGE_HOURS", "24h")
    assert collector.main([]) == 1
    assert zellij.calls == []
    [line] = gc_log(tmp_path)
    assert line.startswith("invalid ZELLIJ_GC_MIN_AGE_HOURS='24h'")
    assert capsys.readouterr().err == f"zellij-gc: {line}\n"

    assert collector.main(["--dry-run"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "invalid ZELLIJ_GC_MIN_AGE_HOURS='24h'" in captured.err
    assert zellij.calls == []


def test_disable_switch_stops_a_real_run_even_when_set_to_0(zellij, monkeypatch, tmp_path):
    monkeypatch.setenv("ZELLIJ_GC_DISABLE", "0")
    assert collector.main([]) == 0
    assert zellij.calls == []
    assert gc_log(tmp_path) == []


def test_disable_switch_does_not_stop_a_preview(zellij, capsys, monkeypatch):
    monkeypatch.setenv("ZELLIJ_GC_DISABLE", "1")
    assert collector.main(["--dry-run"]) == 0
    captured = capsys.readouterr()
    assert len(captured.out.splitlines()) == 2
    assert captured.err.startswith("zellij-gc: ZELLIJ_GC_DISABLE is set")


@pytest.mark.parametrize("missing", ["list-clients", "list-panes", "list-tabs"])
def test_a_query_that_zellij_cannot_answer_keeps_every_session(zellij, capsys, tmp_path, missing):
    """As on a zellij too old to have the action: whichever query fails, nothing is deleted."""
    replies = {
        name: {action: text for action, text in reply.items() if action != missing}
        for name, reply in REPLIES.items()
    }
    zellij.configure(replies=replies)
    assert collector.main([]) == 0
    shown = capsys.readouterr().out.splitlines()
    assert f"  brave-petunia: kept ({missing} failed (exit 2))" in shown
    assert collector.main(["--dry-run"]) == 0
    assert zellij.deletions == []
    captured = capsys.readouterr()
    assert captured.out == ""
    assert f"zellij-gc: kept 'brave-petunia': {missing} failed (exit 2)" in captured.err
    # The real run's log shows that it could not decide, and gives an example of why.
    [line] = gc_log(tmp_path)
    assert " 0 undecided" not in line
    assert line.endswith(f"{missing} failed (exit 2)")


def test_a_query_that_hangs_leaves_its_session_undecided(zellij, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(collector, "QUERY_TIMEOUT_SECONDS", 0.3)
    zellij.configure(sleep={"brave-petunia/list-panes": 2})
    assert collector.main([]) == 0
    assert zellij.deletions == [["delete-session", "--force", "stale one"]]
    assert gc_log(tmp_path)[-1] == (
        f"run: {summary(7, 5, 1, undecided=1)}; "
        "first undecided: 'brave-petunia', list-panes failed (timed out after 0.3s)"
    )
    shown = capsys.readouterr().out.splitlines()
    assert "  brave-petunia: kept (list-panes failed (timed out after 0.3s))" in shown


def test_a_listing_that_hangs_is_a_failure(zellij, monkeypatch, tmp_path):
    monkeypatch.setattr(collector, "QUERY_TIMEOUT_SECONDS", 0.3)
    zellij.configure(sleep={"list-sessions": 2})
    assert collector.main([]) == 1
    assert zellij.queried() == set()
    assert gc_log(tmp_path) == ["run: could not list the sessions (timed out after 0.3s)"]


def test_undecodable_output_does_not_stop_the_run(zellij, capsys, monkeypatch, tmp_path):
    """One session name that isn't UTF-8 must not abort collection for the others."""
    script = tmp_path / "latin1-zellij"
    script.write_text(
        textwrap.dedent(
            f"""\
            #!/bin/sh
            if [ "$1" = list-sessions ]; then
              printf 'caf\\351 [Created 5h ago]\\n'
            fi
            exec {shlex.quote(str(zellij.path))} "$@"
            """
        ),
        encoding="utf-8",
    )
    script.chmod(0o755)
    monkeypatch.setenv("ZELLIJ_GC_ZELLIJ", str(script))
    assert collector.main(["--dry-run"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        f"{shlex.quote(str(script))} delete-session --force brave-petunia",
        f"{shlex.quote(str(script))} delete-session --force 'stale one'",
    ]


def test_no_sessions_at_all_is_no_failure(zellij, tmp_path, capsys):
    """zellij reports it with a non-zero exit, which must not be taken for one."""
    zellij.configure(listing=None)
    assert collector.main([]) == 0
    assert zellij.calls == [["list-sessions", "--no-formatting"]]
    assert gc_log(tmp_path) == [f"run: {summary(0, 0)}"]
    assert capsys.readouterr().err == ""


def test_a_listing_that_fails_is_a_failure(zellij, tmp_path, capsys):
    """Any other non-zero exit is zellij failing, not zellij finding nothing."""
    (zellij.directory / "zellij").write_text(
        "#!/bin/sh\necho 'thread main panicked' >&2\nexit 101\n", encoding="utf-8"
    )
    assert collector.main([]) == 1
    line = "run: could not list the sessions (exit 101: thread main panicked)"
    assert gc_log(tmp_path) == [line]
    assert capsys.readouterr().err == f"zellij-gc: {line}\n"


def test_missing_zellij_binary_is_a_failure(zellij, monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("ZELLIJ_GC_ZELLIJ", str(tmp_path / "no-such-zellij"))
    assert collector.main([]) == 1
    [line] = gc_log(tmp_path)
    assert line.startswith("run: could not list the sessions (could not run: ")
    assert capsys.readouterr().err == f"zellij-gc: {line}\n"


def test_failed_deletion_is_reported_with_its_cause_and_the_run_goes_on(zellij, tmp_path, capsys):
    zellij.configure(delete_status=2)
    assert collector.main([]) == 1
    assert len(zellij.deletions) == 2
    failures = [
        f"FAILED to delete 'brave-petunia' (age {parse_age('3months 25days 20h 9m 36s')}s): "
        'exit 2: Session: "brave-petunia" not found.',
        f"FAILED to delete 'stale one' (age {parse_age('5h 1m')}s): "
        'exit 2: Session: "stale one" not found.',
    ]
    captured = capsys.readouterr()
    assert captured.out.splitlines()[2] == (
        '  brave-petunia: could not be deleted (exit 2: Session: "brave-petunia" not found.)'
    )
    assert captured.err.splitlines() == [f"zellij-gc: {line}" for line in failures]
    assert gc_log(tmp_path) == [
        f"deleting 'brave-petunia' (age {parse_age('3months 25days 20h 9m 36s')}s)",
        failures[0],
        f"deleting 'stale one' (age {parse_age('5h 1m')}s)",
        failures[1],
        f"run: {summary(7, 5, failed=2)}",
    ]


def test_second_collector_backs_off_while_the_lock_is_held(zellij, tmp_path, capsys):
    lock_dir = tmp_path / "cache" / "zellij-gc"
    lock_dir.mkdir(parents=True)
    with (lock_dir / "lock").open("w", encoding="utf-8") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert collector.main([]) == 0
    assert zellij.calls == []
    assert gc_log(tmp_path) == []
    assert capsys.readouterr().err == ""


def test_unusable_cache_dir_is_reported_and_deletes_nothing(zellij, tmp_path, monkeypatch, capsys):
    blocker = tmp_path / "a-file"
    blocker.write_text("", encoding="utf-8")
    monkeypatch.setenv("XDG_CACHE_HOME", str(blocker))
    assert collector.main([]) == 1
    assert zellij.calls == []
    assert capsys.readouterr().err.startswith("zellij-gc: cannot open the lock in ")


def test_a_log_that_cannot_be_opened_stops_the_run(zellij, tmp_path, monkeypatch, capsys):
    """What cannot be put on record is not deleted."""
    blocker = tmp_path / "a-file"
    blocker.write_text("", encoding="utf-8")
    monkeypatch.setenv("XDG_STATE_HOME", str(blocker))
    assert collector.main([]) == 1
    assert zellij.calls == []
    assert capsys.readouterr().err.startswith(
        "zellij-gc: cannot open the log, so nothing was deleted: "
    )


def test_log_falls_back_to_home_when_xdg_is_unset(zellij, tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_STATE_HOME")
    monkeypatch.delenv("XDG_CACHE_HOME")
    assert collector.main([]) == 0
    assert (tmp_path / "home" / ".local" / "state" / "zellij-gc" / "gc.log").exists()
    assert (tmp_path / "home" / ".cache" / "zellij-gc" / "lock").exists()


# --- The shim -------------------------------------------------------------------------------


def test_shim_runs_the_package_and_passes_its_arguments_and_status(zellij, monkeypatch):
    """Through its own shebang, as zellij-welcome runs it; so this needs `uv` on PATH."""
    project = Path(__file__).resolve().parents[1]
    shim = project.parents[1] / "bin" / "executable_zellij-gc"
    monkeypatch.setenv("ZELLIJ_GC_LIB_DIR", str(project))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")

    preview = subprocess.run([str(shim), "--dry-run"], capture_output=True, text=True, check=False)
    assert preview.returncode == 0, preview.stderr
    assert preview.stdout.splitlines() == [
        f"{zellij.quoted} delete-session --force brave-petunia",
        f"{zellij.quoted} delete-session --force 'stale one'",
    ]
    assert zellij.deletions == []

    rejected = subprocess.run([str(shim), "--dryrun"], capture_output=True, check=False)
    assert rejected.returncode == 2
    assert zellij.deletions == []

    # argparse exits by itself, so only a status that main() returns shows the shim passing it on.
    monkeypatch.setenv("ZELLIJ_GC_MIN_AGE_HOURS", "24h")
    refused = subprocess.run([str(shim), "--dry-run"], capture_output=True, check=False)
    assert refused.returncode == 1
