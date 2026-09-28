"""Unit tests for zellij-gc parsing, classification, and the dry-run/deletion flow.

Pure helpers are tested directly. The end-to-end tests drive main() against a fake `zellij`
executable (the ZELLIJ_GC_ZELLIJ seam) that replays canned output and records the calls it
receives; no mocking framework.
"""

from __future__ import annotations

import json
import shlex
import textwrap

import pytest

from zellij_gc import gc
from zellij_gc.gc import Session, count_clients, is_abandoned, parse_age, parse_sessions

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
DEFAULT_TABS = json.dumps([{"position": 0, "name": "Tab #1", "tab_id": 0}])

STALE = Session(name="brave-petunia", age_seconds=5 * HOUR)


def abandoned(session=STALE, clients=NO_CLIENTS, panes=WELCOME_PANES, tabs=DEFAULT_TABS):
    return is_abandoned(session, clients, panes, tabs, min_age_seconds=HOUR)


# --- parse_age ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("36s", 36),
        ("4h 23m 51s", 4 * HOUR + 23 * 60 + 51),
        ("1day 8h 32m 40s", 86400 + 8 * HOUR + 32 * 60 + 40),
        ("3months 25days 20h 9m 36s", 3 * 2630016 + 25 * 86400 + 20 * HOUR + 9 * 60 + 36),
        ("1month 2days", 2630016 + 2 * 86400),
        ("1year 19days 12h 18m 26s", 31557600 + 19 * 86400 + 12 * HOUR + 18 * 60 + 26),
    ],
)
def test_parse_age(text, expected):
    assert parse_age(text) == expected


@pytest.mark.parametrize("text", ["", "soon", "3 fortnights", "5m and change", "12"])
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


def test_parse_sessions_ignores_other_lines():
    assert parse_sessions("No active zellij sessions found.\n\n") == []


def test_parse_sessions_keeps_a_session_whose_age_is_unreadable():
    assert parse_sessions("x [Created a while ago]\n") == [Session("x", None)]


# --- count_clients --------------------------------------------------------------------------


def test_count_clients():
    assert count_clients(NO_CLIENTS) == 0
    assert count_clients(ONE_CLIENT) == 1


@pytest.mark.parametrize("text", ["", "\n", "Session 'x' not found\n"])
def test_count_clients_rejects_unknown_output(text):
    assert count_clients(text) is None


# --- is_abandoned ---------------------------------------------------------------------------


def test_unattended_welcome_screen_is_abandoned():
    assert abandoned()


def test_name_plays_no_part():
    assert abandoned(session=Session("my-project", 5 * HOUR))


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
        "[]",
        "not json",
        "{}",
        '["welcome-screen"]',
        json.dumps([{"is_plugin": True, "plugin_url": "zellij:link"}]),
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
    [(None, HOUR), ("", HOUR), ("junk", HOUR), ("-2", HOUR), ("nan", HOUR), ("inf", HOUR),
     ("0", 0), ("0.5", HOUR / 2), ("24", 24 * HOUR)],
)
def test_min_age_from_env(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv("ZELLIJ_GC_MIN_AGE_HOURS", raising=False)
    else:
        monkeypatch.setenv("ZELLIJ_GC_MIN_AGE_HOURS", value)
    assert gc.min_age_seconds_from_env() == expected


# --- End to end, against a fake zellij ------------------------------------------------------

LISTING = textwrap.dedent(
    """\
    dotfiles [Created 3months 25days 20h 37m 19s ago]
    brave-petunia [Created 3months 25days 20h 9m 36s ago]
    outstanding-cowbell [Created 2days 20h 7m 13s ago]
    stale one [Created 5h 1m ago]
    didactic-river [Created 23m 51s ago]
    verdant-yak [Created 4months 3days 2h 20m 16s ago] (EXITED - attach to resurrect)
    """
)

# Per-session replies; a session missing a reply makes the fake exit non-zero for that query.
REPLIES = {
    "dotfiles": {"list-clients": ONE_CLIENT, "list-panes": WORKING_PANES,
                 "list-tabs": json.dumps([{"name": "claude-settings"}, {"name": "shortcuts"}])},
    "brave-petunia": {"list-clients": NO_CLIENTS, "list-panes": WELCOME_PANES,
                      "list-tabs": DEFAULT_TABS},
    "outstanding-cowbell": {"list-clients": ONE_CLIENT, "list-panes": WELCOME_PANES,
                            "list-tabs": DEFAULT_TABS},
    "stale one": {"list-clients": NO_CLIENTS, "list-panes": WELCOME_PANES,
                  "list-tabs": DEFAULT_TABS},
    "didactic-river": {"list-clients": NO_CLIENTS, "list-panes": WELCOME_PANES,
                       "list-tabs": DEFAULT_TABS},
}

FAKE_ZELLIJ = """\
#!/usr/bin/env python3
import json, pathlib, sys

here = pathlib.Path(__file__).parent
args = sys.argv[1:]
with open(here / "calls.jsonl", "a") as calls:
    calls.write(json.dumps(args) + "\\n")
spec = json.loads((here / "spec.json").read_text())

if args[:1] == ["list-sessions"]:
    if spec["listing"] is None:
        sys.exit(1)
    sys.stdout.write(spec["listing"])
elif args[:1] == ["delete-session"]:
    sys.exit(spec["delete_status"])
elif args[:1] == ["--session"] and args[2:3] == ["action"]:
    reply = spec["replies"].get(args[1], {}).get(args[3])
    if reply is None:
        sys.exit(2)
    sys.stdout.write(reply)
else:
    sys.exit(64)
"""


class FakeZellij:
    def __init__(self, directory):
        self.directory = directory
        self.path = directory / "zellij"
        self.path.write_text(FAKE_ZELLIJ, encoding="utf-8")
        self.path.chmod(0o755)
        self.configure()

    def configure(self, listing=LISTING, replies=None, delete_status=0):
        spec = {"listing": listing, "replies": REPLIES if replies is None else replies,
                "delete_status": delete_status}
        (self.directory / "spec.json").write_text(json.dumps(spec), encoding="utf-8")

    @property
    def quoted(self):
        """The fake's path as dry-run output prints it."""
        return shlex.quote(str(self.path))

    @property
    def calls(self):
        log = self.directory / "calls.jsonl"
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]

    @property
    def deletions(self):
        return [call for call in self.calls if call[0] == "delete-session"]

    def queried(self):
        return {call[1] for call in self.calls if call[0] == "--session"}


@pytest.fixture
def zellij(tmp_path, monkeypatch):
    """A fake zellij on the ZELLIJ_GC_ZELLIJ seam, with HOME and the XDG dirs isolated."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    for var in ("ZELLIJ_GC_DISABLE", "ZELLIJ_GC_MIN_AGE_HOURS"):
        monkeypatch.delenv(var, raising=False)
    directory = tmp_path / "fake"
    directory.mkdir()
    fake = FakeZellij(directory)
    monkeypatch.setenv("ZELLIJ_GC_ZELLIJ", str(fake.path))
    return fake


def gc_log(tmp_path):
    path = tmp_path / "state" / "zellij-gc" / "gc.log"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def test_dry_run_prints_the_deletions_without_running_them(zellij, capsys, tmp_path):
    assert gc.main(["--dry-run"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        f"{zellij.quoted} delete-session --force brave-petunia",
        f"{zellij.quoted} delete-session --force 'stale one'",
    ]
    assert zellij.deletions == []
    assert gc_log(tmp_path) == ""


def test_dry_run_names_plain_zellij_when_no_binary_is_configured(zellij, capsys, monkeypatch):
    monkeypatch.delenv("ZELLIJ_GC_ZELLIJ")
    monkeypatch.setenv("PATH", str(zellij.directory), prepend=":")
    gc.main(["--dry-run"])
    assert capsys.readouterr().out.splitlines()[0] == "zellij delete-session --force brave-petunia"


@pytest.mark.parametrize(
    "argv", [["--dryrun"], ["--dry"], ["--dry-run=1"], ["-n"], ["--help"], ["--dry-run", "extra"]]
)
def test_unrecognised_arguments_never_touch_zellij(zellij, argv):
    with pytest.raises(SystemExit):
        gc.main(argv)
    assert zellij.calls == []


def test_deletes_only_abandoned_sessions_and_logs_them(zellij, capsys, tmp_path):
    assert gc.main([]) == 0
    assert zellij.deletions == [
        ["delete-session", "--force", "brave-petunia"],
        ["delete-session", "--force", "stale one"],
    ]
    assert capsys.readouterr().out == ""
    log = gc_log(tmp_path)
    assert "deleted 'brave-petunia'" in log
    assert "deleted 'stale one'" in log
    assert len(log.splitlines()) == 2


def test_young_and_exited_sessions_are_never_queried(zellij):
    gc.main([])
    assert zellij.queried() == {"dotfiles", "brave-petunia", "outstanding-cowbell", "stale one"}


def test_session_with_a_client_gets_only_the_clients_query(zellij):
    gc.main([])
    actions = {name: [call[3] for call in zellij.calls if call[:2] == ["--session", name]]
               for name in ("dotfiles", "outstanding-cowbell", "brave-petunia")}
    assert actions == {
        "dotfiles": ["list-clients"],
        "outstanding-cowbell": ["list-clients"],
        "brave-petunia": ["list-clients", "list-panes", "list-tabs"],
    }


def test_min_age_override_widens_the_net(zellij, capsys, monkeypatch):
    monkeypatch.setenv("ZELLIJ_GC_MIN_AGE_HOURS", "0")
    gc.main(["--dry-run"])
    expected = f"{zellij.quoted} delete-session --force didactic-river"
    assert expected in capsys.readouterr().out.splitlines()


def test_disable_switch_does_nothing(zellij, monkeypatch):
    monkeypatch.setenv("ZELLIJ_GC_DISABLE", "1")
    assert gc.main([]) == 0
    assert zellij.calls == []


def test_older_zellij_without_the_query_actions_deletes_nothing(zellij, capsys):
    """zellij 0.43 has list-clients but may lack list-panes/list-tabs: every session is kept."""
    replies = {name: {"list-clients": reply["list-clients"]} for name, reply in REPLIES.items()}
    zellij.configure(replies=replies)
    assert gc.main([]) == 0
    assert gc.main(["--dry-run"]) == 0
    assert zellij.deletions == []
    assert capsys.readouterr().out == ""


def test_failed_listing_is_a_quiet_no_op(zellij):
    zellij.configure(listing=None)
    assert gc.main([]) == 0
    assert zellij.calls == [["list-sessions", "--no-formatting"]]


def test_missing_zellij_binary_is_a_quiet_no_op(zellij, monkeypatch, tmp_path):
    monkeypatch.setenv("ZELLIJ_GC_ZELLIJ", str(tmp_path / "no-such-zellij"))
    assert gc.main([]) == 0


def test_failed_deletion_is_logged_and_reported(zellij, tmp_path):
    zellij.configure(delete_status=1)
    assert gc.main([]) == 1
    assert "FAILED to delete 'brave-petunia'" in gc_log(tmp_path)


def test_second_collector_backs_off_while_the_lock_is_held(zellij, tmp_path):
    import fcntl

    lock_dir = tmp_path / "cache" / "zellij-gc"
    lock_dir.mkdir(parents=True)
    with open(lock_dir / "lock", "w", encoding="utf-8") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert gc.main([]) == 0
    assert zellij.calls == []
