"""Unit tests for the shared workspace loading / labeling / sanitization logic."""

from __future__ import annotations

import subprocess
import textwrap
import time

import pytest

from aerospace_workspaces.workspaces import (
    DEFAULT_TIMEOUT,
    aerospace_bin,
    aerospace_timeout,
    label,
    load_workspaces,
    run_aerospace,
    sanitize,
    workspaces_yaml,
)

# A nested fixture exercising every field combination:
#   C: icon + name, no hint.
#   I: icon + name + hint (hint has quotes -> sanitization when used as a tooltip).
#   9: name only, no icon.
#   V: long name (title truncation, tested in test_swiftbar).
NESTED_YAML = textwrap.dedent(
    """\
    workspaces:
      C:
        icon: 💬
        name: Comms
      I:
        icon: 🖥️
        name: Local IT
        hint: 'the "i" is for "IT"'
      9:
        name: Hiring
      V:
        icon: 📹
        name: 'Meetings (the "v" is for "video calls")'
    """
)


@pytest.fixture()
def nested_file(tmp_path):
    path = tmp_path / "workspaces.yaml"
    path.write_text(NESTED_YAML, encoding="utf-8")
    return str(path)


# --- env seams ------------------------------------------------------------------------------


def test_aerospace_bin_default(monkeypatch):
    monkeypatch.delenv("AEROSPACE_BIN", raising=False)
    assert aerospace_bin() == "/opt/homebrew/bin/aerospace"


def test_aerospace_bin_override(monkeypatch):
    monkeypatch.setenv("AEROSPACE_BIN", "/fake/aerospace")
    assert aerospace_bin() == "/fake/aerospace"


def test_workspaces_yaml_override(monkeypatch):
    monkeypatch.setenv("AEROSPACE_WORKSPACES_YAML", "/tmp/ws.yaml")
    assert workspaces_yaml() == "/tmp/ws.yaml"


# --- load_workspaces ------------------------------------------------------------------------


def test_load_nested_records(nested_file):
    records, order = load_workspaces(nested_file)
    assert records["C"] == {"icon": "💬", "name": "Comms"}
    assert records["I"] == {"icon": "🖥️", "name": "Local IT", "hint": 'the "i" is for "IT"'}
    assert records["9"] == {"name": "Hiring"}


def test_load_preserves_declared_order(nested_file):
    _, order = load_workspaces(nested_file)
    assert order == ["C", "I", "9", "V"]


def test_load_coerces_int_key(tmp_path):
    # A bare `9` key reads as int from YAML but must become the string id "9".
    path = tmp_path / "ws.yaml"
    path.write_text("workspaces:\n  9:\n    name: Hiring\n", encoding="utf-8")
    records, order = load_workspaces(str(path))
    assert "9" in records and order == ["9"]


def test_load_old_flat_shape(tmp_path):
    # Back-compat: a bare string value is coerced to {"name": <string>}.
    path = tmp_path / "ws.yaml"
    path.write_text("workspaces:\n  C: Comms\n  I: Local IT\n", encoding="utf-8")
    records, order = load_workspaces(str(path))
    assert records == {"C": {"name": "Comms"}, "I": {"name": "Local IT"}}
    assert order == ["C", "I"]


def test_load_missing_file_returns_empty(tmp_path):
    assert load_workspaces(str(tmp_path / "nope.yaml")) == ({}, [])


def test_load_malformed_returns_empty(tmp_path):
    path = tmp_path / "ws.yaml"
    path.write_text("just a string, not a mapping\n", encoding="utf-8")
    assert load_workspaces(str(path)) == ({}, [])


def test_load_no_workspaces_key_returns_empty(tmp_path):
    path = tmp_path / "ws.yaml"
    path.write_text("window-rules: []\n", encoding="utf-8")
    assert load_workspaces(str(path)) == ({}, [])


def test_load_drops_empty_fields(tmp_path):
    path = tmp_path / "ws.yaml"
    path.write_text("workspaces:\n  C:\n    icon: ''\n    name: Comms\n    hint:\n", encoding="utf-8")
    records, _ = load_workspaces(str(path))
    assert records["C"] == {"name": "Comms"}


# --- label ----------------------------------------------------------------------------------


def test_label_icon_and_name():
    assert label("V", {"V": {"icon": "📹", "name": "Meetings"}}) == "📹 V: Meetings"


def test_label_name_no_icon():
    assert label("9", {"9": {"name": "Hiring"}}) == "9: Hiring"


def test_label_bare_id_when_unmapped():
    # No "Z: Z" noise for an unmapped workspace.
    assert label("Z", {}) == "Z"


def test_label_icon_no_name():
    assert label("X", {"X": {"icon": "🔧"}}) == "🔧 X"


# --- sanitize -------------------------------------------------------------------------------


def test_sanitize_pipe():
    assert sanitize("Box | Login") == "Box ¦ Login"


def test_sanitize_quotes():
    assert '"' not in sanitize('the "v" is for "video"')


def test_sanitize_newlines():
    assert sanitize("a\nb\rc") == "a b c"


# --- aerospace_timeout / run_aerospace ----------------------------------------------------------


def test_aerospace_timeout_default(monkeypatch):
    monkeypatch.delenv("AEROSPACE_TIMEOUT", raising=False)
    assert aerospace_timeout() == DEFAULT_TIMEOUT


def test_aerospace_timeout_override(monkeypatch):
    monkeypatch.setenv("AEROSPACE_TIMEOUT", "0.5")
    assert aerospace_timeout() == 0.5


def test_aerospace_timeout_garbage_falls_back(monkeypatch):
    monkeypatch.setenv("AEROSPACE_TIMEOUT", "soon")
    assert aerospace_timeout() == DEFAULT_TIMEOUT


def test_run_aerospace_returns_stdout(echoing_aerospace):
    assert run_aerospace(["list-workspaces", "--focused"]) == "list-workspaces\n--focused\n"


def test_run_aerospace_raises_on_nonzero_exit(failing_aerospace):
    with pytest.raises(subprocess.CalledProcessError):
        run_aerospace(["list-workspaces", "--focused"])


def test_run_aerospace_times_out_and_kills_child(hanging_aerospace, no_sleep_leftover):
    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        run_aerospace(["list-workspaces", "--focused"])
    assert time.monotonic() - started < 2.0


def test_run_aerospace_replaces_undecodable_bytes(invalid_utf8_aerospace):
    # Decoding must never raise; the bad byte becomes the replacement character.
    assert run_aerospace(["list-workspaces", "--focused"]) == "ws\ufffd\n"
