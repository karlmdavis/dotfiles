"""Unit tests for cmd-notify gating, formatting, and dispatch rendering.

Mirrors the former bats suite: drive main() with --dry-run (capturing the would-be notifier line)
and assert on substrings, plus direct unit tests of the pure helpers. Env seams (CMD_NOTIFY_*,
HOME, XDG_CACHE_HOME) are set per-test; no mocking framework.
"""

from __future__ import annotations

import pytest

from cmd_notify import notify
from cmd_notify.notify import (
    build_body,
    command_base,
    display_command,
    format_duration,
    render_dispatch,
    should_notify,
)


@pytest.fixture(autouse=True)
def clean_env(tmp_path, monkeypatch):
    """Isolate HOME + caches and clear cmd-notify env seams before each test."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    # Empty icons table by default so icon resolution is a no-op unless a test opts in.
    icons_file = tmp_path / "icons.txt"
    icons_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("CMD_NOTIFY_ICONS", str(icons_file))
    for var in ("CMD_NOTIFY_DISABLE", "CMD_NOTIFY_THRESHOLD", "CMD_NOTIFY_PLATFORM"):
        monkeypatch.delenv(var, raising=False)


def run_main(capsys, *argv, env=None, monkeypatch=None):
    """Invoke main(['--dry-run', ...]) and return its stdout (stripped)."""
    if env:
        for key, value in env.items():
            monkeypatch.setenv(key, value)
    notify.main(["--dry-run", *argv])
    return capsys.readouterr().out.strip()


# --- Happy paths ----------------------------------------------------------------------------


def test_darwin_dispatches_terminal_notifier(capsys, monkeypatch):
    out = run_main(capsys, "sleep 90", "120", "0", "/tmp/work",
                   env={"CMD_NOTIFY_PLATFORM": "Darwin"}, monkeypatch=monkeypatch)
    assert "terminal-notifier" in out
    assert "-title sleep 90" in out
    assert "-message succeeded in 2m 0s · work" in out
    assert "-group cmd-notify:sleep" in out


def test_linux_dispatches_notify_send(capsys, monkeypatch):
    out = run_main(capsys, "sleep 90", "120", "0", "/tmp/work",
                   env={"CMD_NOTIFY_PLATFORM": "Linux"}, monkeypatch=monkeypatch)
    assert "notify-send" in out
    assert "string:x-canonical-private-synchronous:cmd-notify-sleep" in out
    assert "sleep 90 succeeded in 2m 0s · work" in out


# --- Threshold and blocklist gating ---------------------------------------------------------


def test_below_threshold_silent(capsys, monkeypatch):
    out = run_main(capsys, "sleep 30", "30", "0", "/tmp",
                   env={"CMD_NOTIFY_PLATFORM": "Darwin"}, monkeypatch=monkeypatch)
    assert out == ""


def test_threshold_env_raised_above_duration(capsys, monkeypatch):
    out = run_main(capsys, "sleep 120", "120", "0", "/tmp",
                   env={"CMD_NOTIFY_THRESHOLD": "300", "CMD_NOTIFY_PLATFORM": "Darwin"},
                   monkeypatch=monkeypatch)
    assert out == ""


def test_blocklist_nvim(capsys, monkeypatch):
    out = run_main(capsys, "nvim foo.txt", "600", "0", "/tmp",
                   env={"CMD_NOTIFY_PLATFORM": "Darwin"}, monkeypatch=monkeypatch)
    assert out == ""


def test_blocklist_claude(capsys, monkeypatch):
    out = run_main(capsys, "claude --resume", "1800", "0", "/tmp",
                   env={"CMD_NOTIFY_PLATFORM": "Darwin"}, monkeypatch=monkeypatch)
    assert out == ""


def test_blocklist_strips_path(capsys, monkeypatch):
    out = run_main(capsys, "/usr/bin/vim notes.md", "600", "0", "/tmp",
                   env={"CMD_NOTIFY_PLATFORM": "Darwin"}, monkeypatch=monkeypatch)
    assert out == ""


def test_disable_kill_switch(capsys, monkeypatch):
    out = run_main(capsys, "cargo build", "600", "0", "/tmp",
                   env={"CMD_NOTIFY_DISABLE": "1", "CMD_NOTIFY_PLATFORM": "Darwin"},
                   monkeypatch=monkeypatch)
    assert out == ""


def test_empty_command_silent(capsys, monkeypatch):
    out = run_main(capsys, "", "600", "0", "/tmp",
                   env={"CMD_NOTIFY_PLATFORM": "Darwin"}, monkeypatch=monkeypatch)
    assert out == ""


def test_non_numeric_duration_silent(capsys, monkeypatch):
    out = run_main(capsys, "cargo build", "not-a-number", "0", "/tmp",
                   env={"CMD_NOTIFY_PLATFORM": "Darwin"}, monkeypatch=monkeypatch)
    assert out == ""


# --- Title trimming and status --------------------------------------------------------------


def test_trims_long_command(capsys, monkeypatch):
    out = run_main(capsys, "a" * 80, "120", "0", "/tmp",
                   env={"CMD_NOTIFY_PLATFORM": "Darwin"}, monkeypatch=monkeypatch)
    assert f"-title {'a' * 39}…" in out


def test_exactly_40_chars_not_truncated(capsys, monkeypatch):
    out = run_main(capsys, "b" * 40, "120", "0", "/tmp",
                   env={"CMD_NOTIFY_PLATFORM": "Darwin"}, monkeypatch=monkeypatch)
    assert f"-title {'b' * 40}" in out
    assert "…" not in out


def test_exit_1_body(capsys, monkeypatch):
    out = run_main(capsys, "cargo test", "120", "1", "/tmp",
                   env={"CMD_NOTIFY_PLATFORM": "Darwin"}, monkeypatch=monkeypatch)
    assert "failed (exit 1)" in out


def test_exit_130_body(capsys, monkeypatch):
    out = run_main(capsys, "cargo test", "120", "130", "/tmp",
                   env={"CMD_NOTIFY_PLATFORM": "Darwin"}, monkeypatch=monkeypatch)
    assert "failed (exit 130)" in out


def test_duration_seconds_only(capsys, monkeypatch):
    out = run_main(capsys, "yes", "5", "0", "/tmp",
                   env={"CMD_NOTIFY_THRESHOLD": "0", "CMD_NOTIFY_PLATFORM": "Darwin"},
                   monkeypatch=monkeypatch)
    assert "succeeded in 5s" in out


def test_duration_hours_minutes(capsys, monkeypatch):
    out = run_main(capsys, "long-job", "3725", "0", "/tmp",
                   env={"CMD_NOTIFY_PLATFORM": "Darwin"}, monkeypatch=monkeypatch)
    assert "succeeded in 1h 2m" in out


# --- cwd basename ---------------------------------------------------------------------------


def test_cwd_basename_in_body(capsys, monkeypatch):
    out = run_main(capsys, "cargo build", "120", "0", "/Users/karl/projects/sneck-app",
                   env={"CMD_NOTIFY_PLATFORM": "Darwin"}, monkeypatch=monkeypatch)
    assert "· sneck-app" in out


def test_cwd_root(capsys, monkeypatch):
    out = run_main(capsys, "rsync -av", "120", "0", "/",
                   env={"CMD_NOTIFY_PLATFORM": "Darwin"}, monkeypatch=monkeypatch)
    assert "· /" in out


# --- Special characters ---------------------------------------------------------------------


def test_control_chars_collapsed_single_line(capsys, monkeypatch):
    out = run_main(capsys, "cargo\ntest\t--all", "120", "0", "/tmp",
                   env={"CMD_NOTIFY_PLATFORM": "Darwin"}, monkeypatch=monkeypatch)
    assert "\n" not in out  # newline in the command was collapsed to a space


def test_shell_metacharacters_passed_through(capsys, monkeypatch):
    out = run_main(capsys, 'echo "hello $world"', "120", "0", "/tmp",
                   env={"CMD_NOTIFY_PLATFORM": "Darwin"}, monkeypatch=monkeypatch)
    assert 'echo "hello $world' in out


# --- Pure-helper unit tests -----------------------------------------------------------------


def test_command_base_path_stripped():
    assert command_base("/usr/bin/vim notes.md") == "vim"


def test_command_base_newline_split():
    assert command_base("vim\nfoo") == "vim"


def test_command_base_empty():
    assert command_base("   ") == ""


def test_format_duration_variants():
    assert format_duration(5) == "5s"
    assert format_duration(120) == "2m 0s"
    assert format_duration(3725) == "1h 2m"


def test_display_command_truncation():
    assert display_command("a" * 80) == "a" * 39 + "…"
    assert display_command("b" * 40) == "b" * 40


def test_build_body_success_and_failure():
    assert build_body("0", 120, "/tmp/work") == "succeeded in 2m 0s · work"
    assert build_body("1", 120, "/tmp/work") == "failed (exit 1) in 2m 0s · work"


def test_render_dispatch_darwin_with_icon():
    line = render_dispatch("Darwin", "t", "b", "cmd-notify:cargo", "/icons/cargo.png")
    assert line == "terminal-notifier -title t -message b -group cmd-notify:cargo -contentImage /icons/cargo.png"


def test_render_dispatch_linux_without_icon():
    line = render_dispatch("Linux", "t", "b", "cmd-notify:cargo", None)
    assert line == "notify-send -h string:x-canonical-private-synchronous:cmd-notify-cargo t b"


def test_should_notify_gating():
    assert should_notify("cargo build", "120", disabled=False, threshold=60) is True
    assert should_notify("cargo build", "120", disabled=True, threshold=60) is False
    assert should_notify("cargo build", "30", disabled=False, threshold=60) is False
    assert should_notify("vim x", "120", disabled=False, threshold=60) is False
    assert should_notify("", "120", disabled=False, threshold=60) is False
    assert should_notify("cargo", "nope", disabled=False, threshold=60) is False
