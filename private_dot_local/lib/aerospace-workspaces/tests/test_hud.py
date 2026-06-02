"""Unit tests for the workspace-switch HUD (pure builders + --dry-run path, no real alerts)."""

from __future__ import annotations

import textwrap
from urllib.parse import unquote

import pytest

from aerospace_workspaces import hud

RECORDS = {
    "V": {"icon": "📹", "name": "Meetings", "hint": 'the "v" is for "video calls"'},
    "N": {"icon": "📝", "name": "Notes"},
    "9": {"name": "Hiring"},
}


# --- resolve_display ------------------------------------------------------------------------


def test_resolve_display_icon_name_hint():
    display, hint = hud.resolve_display("V", "", RECORDS)
    assert display == "📹 Meetings"
    assert hint == 'the "v" is for "video calls"'


def test_resolve_display_no_icon():
    display, hint = hud.resolve_display("9", "", RECORDS)
    assert display == "9: Hiring".replace("9: ", "")  # name only, no "id:" form in the HUD
    assert display == "Hiring" and hint == ""


def test_resolve_display_prefix():
    display, _ = hud.resolve_display("V", "→ ", RECORDS)
    assert display == "📹 → Meetings"


def test_resolve_display_bare_id_fallback():
    display, hint = hud.resolve_display("Z", "", RECORDS)
    assert display == "Z" and hint == ""


# --- build_hammerspoon_url ------------------------------------------------------------------


def test_url_encodes_emoji_and_round_trips():
    url = hud.build_hammerspoon_url("📹 Meetings", "")
    assert "📹" not in url  # encoded, not raw
    name = url.split("name=")[1].split("&")[0]
    assert unquote(name) == "📹 Meetings"


def test_url_encodes_quotes_in_hint():
    url = hud.build_hammerspoon_url("📹 Meetings", 'the "v" is for "video calls"')
    assert "&hint=" in url
    hint = url.split("hint=")[1]
    assert '"' not in hint and unquote(hint) == 'the "v" is for "video calls"'


def test_url_omits_hint_when_absent():
    assert "&hint=" not in hud.build_hammerspoon_url("📝 Notes", "")


# --- build_osascript_body -------------------------------------------------------------------


def test_osascript_body_with_hint():
    assert hud.build_osascript_body("📹 Meetings", "video calls") == "📹 Meetings — video calls"


def test_osascript_body_without_hint():
    assert hud.build_osascript_body("📝 Notes", "") == "📝 Notes"


# --- main --dry-run -------------------------------------------------------------------------


@pytest.fixture()
def yaml_seam(tmp_path, monkeypatch):
    path = tmp_path / "ws.yaml"
    path.write_text(
        textwrap.dedent(
            """\
            workspaces:
              V:
                icon: 📹
                name: Meetings
                hint: 'the "v" is for "video calls"'
              N:
                icon: 📝
                name: Notes
            """
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AEROSPACE_WORKSPACES_YAML", str(path))
    return path


def test_dry_run_hammerspoon_url(capsys, monkeypatch, yaml_seam):
    monkeypatch.setattr(hud, "_hammerspoon_running", lambda: True)
    hud.main(["--dry-run", "V"])
    out = capsys.readouterr().out.strip()
    assert out.startswith("hammerspoon://workspace?name=")
    assert "&hint=" in out and unquote(out.split("name=")[1].split("&")[0]) == "📹 Meetings"


def test_dry_run_unhinted_has_no_hint(capsys, monkeypatch, yaml_seam):
    monkeypatch.setattr(hud, "_hammerspoon_running", lambda: True)
    hud.main(["--dry-run", "N"])
    out = capsys.readouterr().out.strip()
    assert "&hint=" not in out


def test_dry_run_osascript_fallback(capsys, monkeypatch, yaml_seam):
    monkeypatch.setattr(hud, "_hammerspoon_running", lambda: False)
    hud.main(["--dry-run", "V"])
    out = capsys.readouterr().out.strip()
    assert out == "📹 Meetings — the \"v\" is for \"video calls\""


def test_dry_run_prefix_applied(capsys, monkeypatch, yaml_seam):
    monkeypatch.setattr(hud, "_hammerspoon_running", lambda: True)
    hud.main(["--dry-run", "V", "→ "])
    out = capsys.readouterr().out.strip()
    assert unquote(out.split("name=")[1].split("&")[0]) == "📹 → Meetings"


def test_empty_workspace_id_is_noop(capsys, monkeypatch, yaml_seam):
    monkeypatch.setattr(hud, "_focused_workspace", lambda: "")
    hud.main(["--dry-run"])
    assert capsys.readouterr().out == ""
