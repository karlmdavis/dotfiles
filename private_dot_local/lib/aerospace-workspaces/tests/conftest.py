"""Shared fixtures: fake `aerospace` binaries for exercising the bounded CLI runner."""

from __future__ import annotations

import os
import stat

import pytest


def _write_script(path, body: str) -> str:
    path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return str(path)


@pytest.fixture()
def hanging_aerospace(tmp_path, monkeypatch):
    """A fake `aerospace` that never answers (what the real server does while the screen is
    locked / Universal Control is active). `exec` so the timeout kill hits `sleep` itself and no
    grandchild survives. Timeout is shortened so the tests stay fast."""
    path = _write_script(tmp_path / "aerospace", "exec sleep 30\n")
    monkeypatch.setenv("AEROSPACE_BIN", path)
    monkeypatch.setenv("AEROSPACE_TIMEOUT", "0.2")
    return path


@pytest.fixture()
def echoing_aerospace(tmp_path, monkeypatch):
    """A fake `aerospace` that prints its arguments, one per line, and exits 0."""
    path = _write_script(tmp_path / "aerospace", 'for a in "$@"; do printf "%s\\n" "$a"; done\n')
    monkeypatch.setenv("AEROSPACE_BIN", path)
    monkeypatch.delenv("AEROSPACE_TIMEOUT", raising=False)
    return path


@pytest.fixture()
def failing_aerospace(tmp_path, monkeypatch):
    """A fake `aerospace` that exits non-zero."""
    path = _write_script(tmp_path / "aerospace", 'echo "boom" >&2\nexit 3\n')
    monkeypatch.setenv("AEROSPACE_BIN", path)
    monkeypatch.delenv("AEROSPACE_TIMEOUT", raising=False)
    return path


@pytest.fixture()
def no_sleep_leftover():
    """Assert the test left no `sleep 30` child behind (the timeout must kill the CLI)."""
    yield
    assert os.system("pgrep -f 'sleep 30' >/dev/null") != 0, "timeout left a hung child alive"
