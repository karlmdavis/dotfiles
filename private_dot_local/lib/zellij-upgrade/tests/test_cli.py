"""End-to-end tests: the real command, run against stand-ins for every program it calls.

`fake_tools` simulates one machine (zellij sessions and panes, Homebrew, iTerm2, AeroSpace, the
Claude Code processes `ps` shows). Each test sets a machine up, runs `main`, and then checks the
commands that were run and the state the machine was left in. No mocking framework.
"""

from __future__ import annotations

import json
from pathlib import Path

import fake_tools
import pytest

from zellij_upgrade import cli

ALPHA_ID = "aaaa1111-0000-0000-0000-000000000000"
BETA_ID = "bbbb2222-0000-0000-0000-000000000000"
ALPHA_ARGS = "/home/bin/claude --chrome --permission-mode plan --resume old-id"
BETA_ARGS = "/home/bin/claude --chrome -n beta: job"
SHELL = "/opt/homebrew/bin/nu"
# What a report or a dry run says to type by hand for the first session.
BY_HAND = f"`cd /repo/alpha` then `claude --chrome --permission-mode plan --resume {ALPHA_ID}`"


class Machine:
    """The simulated machine, and what the command did to it."""

    def __init__(self, home: Path, world_file: Path) -> None:
        self.home = home
        self.world_file = world_file

    @property
    def world(self) -> dict:
        return json.loads(self.world_file.read_text())

    def change(self, **values: object) -> None:
        self.world_file.write_text(json.dumps({**self.world, **values}))

    def calls(self, name: str | None = None) -> list[list[str]]:
        return [c for c in fake_tools.calls(self.world_file) if name is None or c[0] == name]

    def ran(self, name: str, *words: str) -> bool:
        """Whether `name` was run with all of `words` among its arguments."""
        return any(all(w in call for w in words) for call in self.calls(name))

    def typed(self) -> list[tuple[str, str]]:
        """Each line typed into a pane, as (session, text), in order."""
        return [(c[2], c[-1]) for c in self.calls("zellij") if "write-chars" in c]

    def scripts(self) -> list[str]:
        """Each AppleScript that opened a window or tab."""
        return [c[-1] for c in self.calls("osascript") if "create " in c[-1]]

    def add_claude(
        self, pid: int, session_id: str, name: str, args: str, *, turn: bool = True
    ) -> None:
        claude = self.home / ".claude"
        (claude / "sessions").mkdir(parents=True, exist_ok=True)
        record = {
            "pid": pid,
            "sessionId": session_id,
            "entrypoint": "cli",
            "name": name,
            "cwd": f"/repo/{name[:5]}",
        }
        (claude / "sessions" / f"{pid}.json").write_text(json.dumps(record))
        if turn:
            (claude / "projects/some-project").mkdir(parents=True, exist_ok=True)
            (claude / "projects/some-project" / f"{session_id}.jsonl").write_text("{}\n")
        self.change(claude={**self.world["claude"], str(pid): args})

    def state_dirs(self) -> list[Path]:
        return sorted((self.home / "state/zellij-upgrade").glob("*"))

    def report(self) -> str:
        return (self.state_dirs()[-1] / "report.md").read_text()


@pytest.fixture
def machine(tmp_path, monkeypatch):
    """A Mac with iTerm2: one window on workspace I with two tabs, a Claude session in each."""
    home = tmp_path / "home"
    home.mkdir()
    fake_tools.install(tmp_path / "bin")
    world_file = tmp_path / "world.json"
    world = {
        "version": "0.46.0",
        "newer": "0.46.1",
        "iterm": True,
        "claude": {},
        "sessions": {
            "alpha": {
                "state": "running",
                "panes": [
                    {
                        "id": 0,
                        "tab_name": "alpha: one",
                        "tab_position": 0,
                        "title": "alpha: one",
                        "pane_command": ALPHA_ARGS,
                    },
                    {
                        "id": 1,
                        "tab_name": "alpha: one",
                        "tab_position": 0,
                        "title": "~",
                        "pane_command": SHELL,
                    },
                ],
            },
            "beta (two)": {
                "state": "running",
                "panes": [
                    {
                        "id": 0,
                        "tab_name": "beta: job",
                        "tab_position": 0,
                        "title": "✳ beta: job",
                        "pane_command": BETA_ARGS,
                    },
                ],
            },
        },
        "windows": [["900", ["alpha | alpha: one (zellij)", "beta (two) | beta: job (zellij)"]]],
        "workspaces": {"900": "I"},
    }
    world_file.write_text(json.dumps(world))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_STATE_HOME", str(home / "state"))
    monkeypatch.setenv("FAKE_WORLD", str(world_file))
    monkeypatch.setenv("ZELLIJ_UPGRADE_PATH", f"{tmp_path / 'bin'}:/usr/bin:/bin")
    monkeypatch.setenv("ZELLIJ_UPGRADE_PAUSE_SCALE", "0")
    for name in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID", "XDG_CACHE_HOME"):
        monkeypatch.delenv(name, raising=False)
    machine = Machine(home, world_file)
    machine.add_claude(101, ALPHA_ID, "alpha: one", ALPHA_ARGS)
    machine.add_claude(102, BETA_ID, "beta: job", BETA_ARGS)
    return machine


def index_of(calls: list[list[str]], *words: str) -> int:
    return next(i for i, call in enumerate(calls) if all(w in call for w in words))


# ------------------------------------------------------------------------------------- a full run


def test_a_full_run_with_iterm_upgrades_restarts_and_resumes_everything(machine, capsys):
    assert cli.main(["--yes"]) == 0

    world = machine.world
    assert world["version"] == "0.46.1"
    assert all(s["state"] == "running" for s in world["sessions"].values())
    # The window comes back with both tabs, attached straight to each session, on its workspace.
    window, tab = machine.scripts()
    assert 'create window with profile "zellij"' in window
    assert 'attach \\"alpha\\"' in window
    assert "create tab" in tab
    assert 'attach \\"beta (two)\\"' in tab
    assert machine.ran("aerospace", "move-node-to-workspace", "--window-id", "501", "I")
    # Each Claude session is resumed from a shell: cd first, then its own flags and its id.
    assert machine.typed() == [
        ("alpha", "cd /repo/alpha"),
        ("alpha", f"claude --chrome --permission-mode plan --resume {ALPHA_ID}"),
        ("beta (two)", "cd /repo/beta:"),
        ("beta (two)", f"claude --chrome --resume {BETA_ID}"),
    ]
    assert machine.ran("zellij", "send-keys", "terminal_0", "Esc")
    assert not machine.ran("zellij", "send-keys", "terminal_1", "Esc")
    assert "Everything came back." in machine.report()
    assert machine.ran("brew", "cleanup", "zellij")
    out = capsys.readouterr().out
    assert "Window on workspace I: alpha, beta (two)" in out
    assert "No problems found." in out


def test_nothing_is_ended_before_the_upgrade_and_nothing_reopened_before_the_end(machine):
    cli.main(["--yes"])
    calls = machine.calls()
    upgrade = index_of(calls, "brew", "upgrade")
    kill = index_of(calls, "zellij", "kill-all-sessions")
    reopen = next(
        i for i, c in enumerate(calls) if c[0] == "osascript" and "create window" in c[-1]
    )
    assert upgrade < kill < reopen


def test_the_saved_sessions_and_the_inventory_are_kept_in_the_state_folder(machine):
    saved = cli.cache_dir() / "contract_version_1/session_info/alpha"
    saved.mkdir(parents=True)
    (saved / "session-layout.kdl").write_text("layout {}\n")
    cli.main(["--yes"])
    state = machine.state_dirs()[-1]
    assert (state / "session-cache/session_info/alpha/session-layout.kdl").is_file()
    assert json.loads((state / "inventory.json").read_text())["zellij_version"] == "zellij 0.46.0"
    assert "upgrade zellij with Homebrew" in (state / "run.log").read_text()


def test_without_iterm_sessions_come_back_in_the_background(machine, capsys):
    machine.change(iterm=False)
    assert cli.main(["--yes"]) == 0
    out = capsys.readouterr().out
    assert "Sessions come back as background sessions." in out
    assert "Window on" not in out
    assert machine.scripts() == []
    assert machine.ran("zellij", "attach", "--create-background", "alpha")
    assert machine.ran("zellij", "attach", "--create-background", "beta (two)")
    assert not machine.ran("aerospace", "move-node-to-workspace")
    assert len(machine.typed()) == 4
    assert "Everything came back." in machine.report()


def test_a_session_with_no_window_gets_one_so_its_server_starts_in_the_gui_session(machine):
    machine.change(windows=[["900", ["alpha | alpha: one (zellij)"]]])
    assert cli.main(["--yes"]) == 0
    first, second = machine.scripts()
    assert "create window" in first
    assert "create window" in second
    assert 'attach \\"beta (two)\\"' in second
    assert len([c for c in machine.calls("aerospace") if "move-node-to-workspace" in c]) == 1


# --------------------------------------------------------------------------- when nothing is ended


def test_a_dry_run_changes_nothing(machine, capsys):
    assert cli.main(["--dry-run"]) == 0
    world = machine.world
    assert world["version"] == "0.46.0"
    assert all(s["state"] == "running" for s in world["sessions"].values())
    assert not machine.ran("brew", "upgrade")
    assert not machine.ran("zellij", "kill-all-sessions")
    assert machine.typed() == []
    assert machine.scripts() == []
    out = capsys.readouterr().out
    assert "would end all zellij sessions" in out
    assert f"would resume alpha / alpha: one: {BY_HAND}" in out


def test_with_no_newer_zellij_there_is_nothing_to_do(machine, capsys):
    machine.change(newer=None)
    assert cli.main(["--yes"]) == 0
    assert "nothing to do" in capsys.readouterr().out
    assert not machine.ran("zellij", "kill-all-sessions")
    assert machine.state_dirs() == []


def test_force_restarts_everything_without_an_upgrade(machine):
    machine.change(newer=None)
    assert cli.main(["--yes", "--force"]) == 0
    assert not machine.ran("brew", "upgrade")
    assert machine.ran("zellij", "kill-all-sessions", "--yes")
    assert len(machine.typed()) == 4


def test_it_does_not_go_ahead_unasked_when_nobody_can_answer(machine, capsys):
    assert cli.main([]) == cli.EXIT_REFUSED
    assert "pass --yes" in capsys.readouterr().out
    assert not machine.ran("brew", "upgrade")
    assert not machine.ran("zellij", "kill-all-sessions")


def test_an_upgrade_that_did_not_change_the_version_ends_nothing(machine):
    machine.change(newer="0.46.0")  # Homebrew "upgrades" to the version already installed.
    assert cli.main(["--yes"]) == 0
    assert machine.ran("brew", "upgrade", "zellij")
    assert not machine.ran("zellij", "kill-all-sessions")


# ------------------------------------------------------------------------------- started in zellij


def test_started_inside_zellij_it_carries_on_in_a_window_outside_it(machine, monkeypatch, capsys):
    monkeypatch.setenv("ZELLIJ", "0")
    monkeypatch.setenv("ZELLIJ_SESSION_NAME", "alpha")
    monkeypatch.setenv("ZELLIJ_PANE_ID", "0")
    assert cli.main(["--yes"]) == 0

    (script,) = machine.scripts()
    state = machine.state_dirs()[-1]
    assert 'create window with profile "zsh"' in script
    assert "NO_ZELLIJ=1" in script
    assert f"--run {state} --hold" in script
    assert not machine.ran("zellij", "kill-all-sessions")
    assert "Carrying on outside zellij" in capsys.readouterr().out
    inventory = json.loads((state / "inventory.json").read_text())
    assert inventory["origin"] == {"session": "alpha", "tab": "alpha: one"}


def test_the_pane_it_was_started_from_is_resumed_last_and_told_where_the_report_is(
    machine, monkeypatch
):
    monkeypatch.setenv("ZELLIJ", "0")
    monkeypatch.setenv("ZELLIJ_SESSION_NAME", "alpha")
    monkeypatch.setenv("ZELLIJ_PANE_ID", "0")
    cli.main(["--yes"])
    state = machine.state_dirs()[-1]
    for name in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID"):
        monkeypatch.delenv(name)

    assert cli.main(["--run", str(state)]) == 0
    typed = machine.typed()
    assert [session for session, _ in typed] == [
        "beta (two)",
        "beta (two)",
        "alpha",
        "alpha",
        "alpha",
    ]
    assert typed[-1][1].startswith("The zellij upgrade has finished. Everything came back. Read")
    assert str(state / "report.md") in typed[-1][1]


def test_the_second_half_refuses_to_run_inside_zellij(machine, monkeypatch, capsys):
    monkeypatch.setenv("ZELLIJ", "0")
    assert cli.main(["--run", "/nowhere"]) == cli.EXIT_REFUSED
    assert "outside zellij" in capsys.readouterr().err


# -------------------------------------------------------------------------- what does not come back


def test_a_session_that_does_not_resurrect_is_recreated_from_its_backed_up_layout(machine):
    saved = cli.cache_dir() / "contract_version_1/session_info/alpha"
    saved.mkdir(parents=True)
    (saved / "session-layout.kdl").write_text("layout {}\n")
    machine.change(resurrect_fails=["alpha"])

    assert cli.main(["--yes"]) == cli.EXIT_INCOMPLETE
    recreate = next(s for s in machine.scripts() if "--layout" in s)
    assert "session-cache/session_info/alpha/session-layout.kdl" in recreate
    assert 'attach --create \\"alpha\\"' in recreate
    report = machine.report()
    assert "`alpha` did not resurrect; recreated from its backup." in report
    # The recreated session has only a shell, so its Claude pane cannot be found: say how to do it.
    assert f"alpha / alpha: one: could not tell which pane to use. By hand: {BY_HAND}" in report
    assert "Something did not come back." in report
    assert not machine.ran("brew", "cleanup")
    # The other session is unaffected.
    assert ("beta (two)", f"claude --chrome --resume {BETA_ID}") in machine.typed()


def test_a_session_that_does_not_come_back_and_has_no_backup_is_reported(machine):
    machine.change(resurrect_fails=["alpha"])
    assert cli.main(["--yes"]) == cli.EXIT_INCOMPLETE
    assert "`alpha` did not come back and has no backed-up layout" in machine.report()


def test_a_claude_session_that_never_took_a_turn_is_flagged_beforehand_and_left_alone(
    machine, capsys
):
    machine.add_claude(103, "cccc3333", "gamma: new", "/home/bin/claude --chrome", turn=False)
    world = machine.world
    world["sessions"]["beta (two)"]["panes"].append(
        {
            "id": 5,
            "tab_name": "gamma: new",
            "tab_position": 1,
            "title": "gamma: new",
            "pane_command": "/home/bin/claude --chrome",
        }
    )
    machine.change(sessions=world["sessions"])

    assert cli.main(["--yes"]) == cli.EXIT_INCOMPLETE
    out = capsys.readouterr().out
    assert "beta (two) / gamma: new: Claude session cccc3333 has no saved conversation yet" in out
    assert "gamma: new: NOT RESUMED" in out
    assert not any("cccc3333" in text for _, text in machine.typed())
    assert "beta (two) / gamma: new was not resumed" in machine.report()
    assert len(machine.typed()) == 4


def test_a_claude_session_that_is_not_running_afterwards_is_reported(machine, monkeypatch):
    # Claude shows a question instead of starting (whether to trust the folder, say), so typing the
    # resume command leaves no running session behind.
    monkeypatch.setenv("FAKE_CLAUDE_NEVER_STARTS", ALPHA_ID)
    assert cli.main(["--yes"]) == cli.EXIT_INCOMPLETE
    assert f"alpha / alpha: one: Claude session {ALPHA_ID[:8]} is not running" in machine.report()
    assert not machine.ran("brew", "cleanup")


def test_two_runs_in_the_same_second_get_a_state_folder_each(machine):
    cli.main(["--dry-run"])
    cli.main(["--dry-run"])
    assert len(machine.state_dirs()) == 2
