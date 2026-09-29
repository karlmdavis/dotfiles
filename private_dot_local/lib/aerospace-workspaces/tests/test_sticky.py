"""Unit tests for sticky windows (rule loading, the pure command planner, and --dry-run)."""

from __future__ import annotations

import textwrap

import pytest

from aerospace_workspaces import sticky


def _write(tmp_path, text: str) -> str:
    path = tmp_path / "ws.yaml"
    path.write_text(textwrap.dedent(text), encoding="utf-8")
    return str(path)


def _window(window_id, app="com.example.Popup", title="Popup", workspace="A", layout="floating"):
    return {
        "window-id": window_id,
        "app-bundle-id": app,
        "window-title": title,
        "workspace": workspace,
        "window-layout": layout,
    }


# --- load_sticky_rules ----------------------------------------------------------------------


def test_load_rules_with_and_without_title_regex(tmp_path):
    path = _write(
        tmp_path,
        """\
        sticky-windows:
          - app-id: com.example.Popup
            title-regex: '^[0-9]+ Alerts?$'
          - app-id: com.example.Palette
        """,
    )
    rules = sticky.load_sticky_rules(path)
    assert [app for app, _ in rules] == ["com.example.Popup", "com.example.Palette"]
    assert rules[0][1] is not None and rules[0][1].search("3 Alerts")
    assert rules[1][1] is None


def test_load_rules_missing_file(tmp_path):
    assert sticky.load_sticky_rules(str(tmp_path / "absent.yaml")) == []


def test_load_rules_missing_key(tmp_path):
    assert sticky.load_sticky_rules(_write(tmp_path, "workspaces:\n  C:\n    name: Comms\n")) == []


def test_load_rules_skips_malformed_entries(tmp_path):
    path = _write(
        tmp_path,
        """\
        sticky-windows:
          - just-a-string
          - title-regex: 'no app id'
          - app-id: com.example.Bad
            title-regex: '(unclosed'
          - app-id: com.example.Good
        """,
    )
    assert [app for app, _ in sticky.load_sticky_rules(path)] == ["com.example.Good"]


# --- plan_commands --------------------------------------------------------------------------

RULES = [("com.example.Popup", sticky.re.compile(r"^[0-9]+ Alerts?$")), ("com.example.Palette", None)]


def test_plan_moves_matching_floating_window():
    windows = [_window(1, title="1 Alert", workspace="A")]
    assert sticky.plan_commands(windows, RULES, "B") == [
        ["move-node-to-workspace", "--window-id", "1", "B"]
    ]


def test_plan_floats_tiled_window_before_moving():
    windows = [_window(2, title="2 Alerts", workspace="A", layout="h_tiles")]
    assert sticky.plan_commands(windows, RULES, "B") == [
        ["layout", "--window-id", "2", "floating"],
        ["move-node-to-workspace", "--window-id", "2", "B"],
    ]


def test_plan_floats_tiled_window_already_on_target():
    windows = [_window(3, title="1 Alert", workspace="B", layout="v_tiles")]
    assert sticky.plan_commands(windows, RULES, "B") == [["layout", "--window-id", "3", "floating"]]


def test_plan_skips_floating_window_already_on_target():
    assert sticky.plan_commands([_window(4, title="1 Alert", workspace="B")], RULES, "B") == []


def test_plan_title_regex_must_match():
    # Same app, but a title the rule doesn't cover (e.g. the app's main window).
    windows = [_window(5, title="Inbox", layout="h_tiles")]
    assert sticky.plan_commands(windows, RULES, "B") == []


def test_plan_rule_without_regex_matches_any_title():
    windows = [_window(6, app="com.example.Palette", title="anything")]
    assert sticky.plan_commands(windows, RULES, "B") == [
        ["move-node-to-workspace", "--window-id", "6", "B"]
    ]


def test_plan_ignores_other_apps():
    windows = [_window(7, app="com.example.Other", title="1 Alert", layout="h_tiles")]
    assert sticky.plan_commands(windows, RULES, "B") == []


# --- main --dry-run -------------------------------------------------------------------------


@pytest.fixture()
def rules_seam(tmp_path, monkeypatch):
    path = _write(
        tmp_path,
        """\
        sticky-windows:
          - app-id: com.example.Popup
            title-regex: 'Alert'
        """,
    )
    monkeypatch.setenv("AEROSPACE_WORKSPACES_YAML", path)
    return path


def test_dry_run_prints_commands_for_focused_workspace(capsys, monkeypatch, rules_seam):
    monkeypatch.setenv("AEROSPACE_FOCUSED_WORKSPACE", "B")
    monkeypatch.setattr(sticky, "_list_windows", lambda: [_window(8, title="1 Alert", layout="h_tiles")])
    sticky.main(["--dry-run"])
    assert capsys.readouterr().out.splitlines() == [
        "aerospace layout --window-id 8 floating",
        "aerospace move-node-to-workspace --window-id 8 B",
    ]


def test_dry_run_falls_back_to_focused_query(capsys, monkeypatch, rules_seam):
    monkeypatch.delenv("AEROSPACE_FOCUSED_WORKSPACE", raising=False)
    monkeypatch.setattr(sticky, "focused_workspace", lambda: "C")
    monkeypatch.setattr(sticky, "_list_windows", lambda: [_window(9, title="1 Alert")])
    sticky.main(["--dry-run"])
    assert capsys.readouterr().out.strip() == "aerospace move-node-to-workspace --window-id 9 C"


def test_no_rules_skips_window_query(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("AEROSPACE_WORKSPACES_YAML", _write(tmp_path, "workspaces: {}\n"))

    def fail():
        raise AssertionError("list-windows should not be queried without rules")

    monkeypatch.setattr(sticky, "_list_windows", fail)
    sticky.main(["--dry-run"])
    assert capsys.readouterr().out == ""
