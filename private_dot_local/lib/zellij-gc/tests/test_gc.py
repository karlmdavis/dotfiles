"""Unit tests for zellij-gc parsing, classification, and the dry-run/deletion flow.

Pure helpers are tested directly. The end-to-end tests drive main() against a fake `zellij`
executable (the ZELLIJ_GC_ZELLIJ seam) that replays canned output and records the calls it
receives; no mocking framework.
"""

from __future__ import annotations

import fcntl
import json
import shlex
import subprocess
import textwrap
from pathlib import Path

import pytest

from zellij_gc import gc
from zellij_gc.gc import Session, is_abandoned, parse_age, parse_sessions

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


@pytest.mark.parametrize("text", ["", "3 fortnights", "5m and change"])
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
    [(None, HOUR), ("  ", HOUR), ("0", 0), ("0.5", HOUR / 2),
     ("24h", None), ("-2", None), ("nan", None), ("inf", None)],
)
def test_min_age_from_env(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv("ZELLIJ_GC_MIN_AGE_HOURS", raising=False)
    else:
        monkeypatch.setenv("ZELLIJ_GC_MIN_AGE_HOURS", value)
    assert gc.min_age_seconds_from_env() == expected


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
    "dotfiles": {"list-clients": ONE_CLIENT, "list-panes": WORKING_PANES,
                 "list-tabs": json.dumps([{"name": "claude-settings"}, {"name": "shortcuts"}])},
    "brave-petunia": {"list-clients": NO_CLIENTS, "list-panes": WELCOME_PANES,
                      "list-tabs": DEFAULT_TABS},
    "outstanding-cowbell": {"list-clients": ONE_CLIENT, "list-panes": WELCOME_PANES,
                            "list-tabs": DEFAULT_TABS},
    "stale one": {"list-clients": NO_CLIENTS, "list-panes": WELCOME_PANES,
                  "list-tabs": DEFAULT_TABS},
    "shell-beside-chooser": {"list-clients": NO_CLIENTS, "list-panes": WELCOME_PLUS_TERMINAL_PANES,
                             "list-tabs": DEFAULT_TABS},
    "didactic-river": {"list-clients": NO_CLIENTS, "list-panes": WELCOME_PANES,
                       "list-tabs": DEFAULT_TABS},
}

FAKE_ZELLIJ = """\
#!/usr/bin/env python3
import json, pathlib, sys, time

here = pathlib.Path(__file__).parent
args = sys.argv[1:]
with open(here / "calls.jsonl", "a") as calls:
    calls.write(json.dumps(args) + "\\n")
spec = json.loads((here / "spec.json").read_text())
time.sleep(spec["sleep"])

if args[:1] == ["list-sessions"]:
    if spec["listing"] is None:
        sys.exit("No active zellij sessions found.")
    sys.stdout.write(spec["listing"])
elif args[:1] == ["delete-session"]:
    if spec["delete_status"]:
        print(f'Session: "{args[-1]}" not found.', file=sys.stderr)
    sys.exit(spec["delete_status"])
elif args[:1] == ["--session"] and args[2:3] == ["action"]:
    reply = spec["replies"].get(args[1], {}).get(args[3])
    # As the real CLI: the JSON queries print a table, not JSON, unless asked for JSON.
    wants_json = args[3] in ("list-panes", "list-tabs")
    if reply is None or (wants_json and "--json" not in args):
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

    def configure(self, listing=LISTING, replies=None, delete_status=0, sleep=0):
        spec = {"listing": listing, "replies": REPLIES if replies is None else replies,
                "delete_status": delete_status, "sleep": sleep}
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
    """The GC log's lines, without their timestamps."""
    path = tmp_path / "state" / "zellij-gc" / "gc.log"
    if not path.exists():
        return []
    return [line.partition(" ")[2] for line in path.read_text(encoding="utf-8").splitlines()]


def test_dry_run_prints_the_deletions_and_its_reasons_and_deletes_nothing(zellij, capsys, tmp_path):
    assert gc.main(["--dry-run"]) == 0
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
        "zellij-gc: run: 7 listed, 5 kept, 2 to delete, 0 failed to delete, 0 unparsed lines",
    ]


def test_dry_run_names_plain_zellij_when_no_binary_is_configured(zellij, capsys, monkeypatch):
    monkeypatch.delenv("ZELLIJ_GC_ZELLIJ")
    monkeypatch.setenv("PATH", str(zellij.directory), prepend=":")
    assert gc.main(["--dry-run"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "zellij delete-session --force brave-petunia",
        "zellij delete-session --force 'stale one'",
    ]


@pytest.mark.parametrize("argv", [["--dry"], ["--dry-run=1"], ["-n"], ["--dry-run", "extra"]])
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
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")
    assert gc_log(tmp_path) == [
        f"deleted 'brave-petunia' (age {parse_age('3months 25days 20h 9m 36s')}s)",
        f"deleted 'stale one' (age {parse_age('5h 1m')}s)",
        "run: 7 listed, 5 kept, 2 deleted, 0 failed to delete, 0 unparsed lines",
    ]


def test_a_run_with_nothing_to_delete_still_leaves_a_line(zellij, tmp_path):
    """Without it, a collector that never finds anything looks the same as one that never runs."""
    zellij.configure(listing="dotfiles [Created 5h ago]\nnot a session line\n")
    assert gc.main([]) == 0
    assert gc_log(tmp_path) == [
        "run: 1 listed, 1 kept, 0 deleted, 0 failed to delete, 1 unparsed lines",
    ]


def test_log_is_rotated_once_past_its_size_cap(zellij, tmp_path, monkeypatch):
    monkeypatch.setattr(gc, "LOG_MAX_BYTES", 200)
    zellij.configure(listing=None)  # The cheapest run: one zellij call and one log line (~90 bytes).
    directory = tmp_path / "state" / "zellij-gc"
    for _ in range(8):  # Enough to rotate twice, so the second rotation replaces gc.log.1.
        assert gc.main([]) == 0
    assert sorted(path.name for path in directory.iterdir()) == ["gc.log", "gc.log.1"]
    # Each file stops growing within one line of the cap.
    assert all(path.stat().st_size < 200 + 100 for path in directory.iterdir())


def test_a_crash_is_logged_with_its_traceback(zellij, tmp_path, monkeypatch):
    def explode(text):
        raise RuntimeError("boom")

    monkeypatch.setattr(gc, "parse_sessions", explode)
    assert gc.main([]) == 1
    log = gc_log(tmp_path)
    assert log[0] == "run: crashed"
    assert log[-1] == "boom"


def test_queries_and_their_flags(zellij):
    """Young and exited sessions get no queries, and a session with a client only the first."""
    gc.main([])
    assert zellij.queried() == {"dotfiles", "brave-petunia", "outstanding-cowbell", "stale one",
                                "shell-beside-chooser"}
    actions = {name: [call[3:] for call in zellij.calls if call[:2] == ["--session", name]]
               for name in ("dotfiles", "outstanding-cowbell", "brave-petunia")}
    assert actions == {
        "dotfiles": [["list-clients"]],
        "outstanding-cowbell": [["list-clients"]],
        "brave-petunia": [["list-clients"], ["list-panes", "--json", "--all"],
                          ["list-tabs", "--json"]],
    }


def test_min_age_override_widens_the_net(zellij, capsys, monkeypatch):
    monkeypatch.setenv("ZELLIJ_GC_MIN_AGE_HOURS", "0")
    gc.main(["--dry-run"])
    expected = f"{zellij.quoted} delete-session --force didactic-river"
    assert expected in capsys.readouterr().out.splitlines()


def test_invalid_min_age_deletes_nothing_and_says_so(zellij, capsys, monkeypatch, tmp_path):
    """`24h` asks for longer retention; falling back to the 1h default would shorten it."""
    monkeypatch.setenv("ZELLIJ_GC_MIN_AGE_HOURS", "24h")
    assert gc.main([]) == 1
    assert zellij.calls == []
    [line] = gc_log(tmp_path)
    assert line.startswith("invalid ZELLIJ_GC_MIN_AGE_HOURS='24h'")

    assert gc.main(["--dry-run"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "invalid ZELLIJ_GC_MIN_AGE_HOURS='24h'" in captured.err
    assert zellij.calls == []


def test_disable_switch_stops_a_real_run_even_when_set_to_0(zellij, monkeypatch, tmp_path):
    monkeypatch.setenv("ZELLIJ_GC_DISABLE", "0")
    assert gc.main([]) == 0
    assert zellij.calls == []
    assert gc_log(tmp_path) == []


def test_disable_switch_does_not_stop_a_preview(zellij, capsys, monkeypatch):
    monkeypatch.setenv("ZELLIJ_GC_DISABLE", "1")
    assert gc.main(["--dry-run"]) == 0
    captured = capsys.readouterr()
    assert len(captured.out.splitlines()) == 2
    assert captured.err.startswith("zellij-gc: ZELLIJ_GC_DISABLE is set")


@pytest.mark.parametrize("missing", ["list-clients", "list-panes", "list-tabs"])
def test_a_query_that_zellij_cannot_answer_keeps_every_session(zellij, capsys, missing):
    """As on a zellij too old to have the action: whichever query fails, nothing is deleted."""
    replies = {name: {action: text for action, text in reply.items() if action != missing}
               for name, reply in REPLIES.items()}
    zellij.configure(replies=replies)
    assert gc.main([]) == 0
    assert gc.main(["--dry-run"]) == 0
    assert zellij.deletions == []
    captured = capsys.readouterr()
    assert captured.out == ""
    assert f"zellij-gc: kept 'brave-petunia': {missing} failed (exit 2)" in captured.err


def test_query_that_hangs_is_a_failure(zellij):
    zellij.configure(sleep=1)
    result = gc.run_zellij(str(zellij.path), ["list-sessions"], timeout=0.3)
    assert result == gc.Result(None, "timed out after 0.3s")


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
    assert gc.main(["--dry-run"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        f"{shlex.quote(str(script))} delete-session --force brave-petunia",
        f"{shlex.quote(str(script))} delete-session --force 'stale one'",
    ]


def test_failed_listing_deletes_nothing_and_is_logged(zellij, tmp_path):
    zellij.configure(listing=None)
    assert gc.main([]) == 0
    assert zellij.calls == [["list-sessions", "--no-formatting"]]
    assert gc_log(tmp_path) == [
        "run: no sessions listed (exit 1: No active zellij sessions found.)",
    ]


def test_missing_zellij_binary_deletes_nothing_and_is_logged(zellij, monkeypatch, tmp_path):
    monkeypatch.setenv("ZELLIJ_GC_ZELLIJ", str(tmp_path / "no-such-zellij"))
    assert gc.main([]) == 0
    [line] = gc_log(tmp_path)
    assert line.startswith("run: no sessions listed (could not run: ")


def test_failed_deletion_is_logged_with_its_cause_and_the_run_goes_on(zellij, tmp_path):
    zellij.configure(delete_status=2)
    assert gc.main([]) == 1
    assert len(zellij.deletions) == 2
    assert gc_log(tmp_path) == [
        f"FAILED to delete 'brave-petunia' (age {parse_age('3months 25days 20h 9m 36s')}s): "
        'exit 2: Session: "brave-petunia" not found.',
        f"FAILED to delete 'stale one' (age {parse_age('5h 1m')}s): "
        'exit 2: Session: "stale one" not found.',
        "run: 7 listed, 5 kept, 0 deleted, 2 failed to delete, 0 unparsed lines",
    ]


def test_second_collector_backs_off_while_the_lock_is_held(zellij, tmp_path, capsys):
    lock_dir = tmp_path / "cache" / "zellij-gc"
    lock_dir.mkdir(parents=True)
    with open(lock_dir / "lock", "w", encoding="utf-8") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert gc.main([]) == 0
    assert zellij.calls == []
    assert gc_log(tmp_path) == []
    assert capsys.readouterr().err == ""


def test_unusable_cache_dir_is_reported_and_deletes_nothing(zellij, tmp_path, monkeypatch, capsys):
    blocker = tmp_path / "a-file"
    blocker.write_text("", encoding="utf-8")
    monkeypatch.setenv("XDG_CACHE_HOME", str(blocker))
    assert gc.main([]) == 1
    assert zellij.calls == []
    assert capsys.readouterr().err.startswith("zellij-gc: cannot open the lock in ")


def test_unusable_state_dir_does_not_stop_the_run(zellij, tmp_path, monkeypatch):
    blocker = tmp_path / "a-file"
    blocker.write_text("", encoding="utf-8")
    monkeypatch.setenv("XDG_STATE_HOME", str(blocker))
    assert gc.main([]) == 0
    assert len(zellij.deletions) == 2


def test_log_falls_back_to_home_when_xdg_is_unset(zellij, tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_STATE_HOME")
    monkeypatch.delenv("XDG_CACHE_HOME")
    assert gc.main([]) == 0
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
