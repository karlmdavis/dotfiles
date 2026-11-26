"""The only code that runs commands or reads the machine: zellij, Homebrew, the terminal app.

Every command is found on one search path, so the tests can stand in for all of them by putting
their own executables first on it (`ZELLIJ_UPGRADE_PATH`). The command is often started from an
app with a bare system PATH, so Homebrew's bin folder is probed for here, as zellij-welcome does.

A step that changes something goes through `Tools.act`, which in a dry run prints the command and
does nothing. Steps that only read go through `Tools.read` and always run.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from zellij_upgrade.inventory import ClaudeProcess, parse_running_sessions, terminal_panes

if TYPE_CHECKING:
    from collections.abc import Callable

BREW_BINS = ("/opt/homebrew/bin", "/home/linuxbrew/.linuxbrew/bin")
SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"
# Variables zellij sets inside a session; a command meant to outlive the session must not see them.
ZELLIJ_VARIABLES = ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID")

LIST_TERMINAL_WINDOWS = """
tell application "iTerm2"
  set out to ""
  repeat with w in windows
    set out to out & "W " & (id of w) & linefeed
    repeat with t in tabs of w
      repeat with s in sessions of t
        set out to out & "S " & (name of s) & linefeed
      end repeat
    end repeat
  end repeat
  return out
end tell
"""


def search_path() -> str:
    """Where commands are looked up: the test seam, or Homebrew's bin plus the system folders."""
    override = os.environ.get("ZELLIJ_UPGRADE_PATH")
    if override:
        return override
    brew = [d for d in BREW_BINS if Path(d).is_dir()]
    return ":".join([*brew, str(Path.home() / ".local/bin"), SYSTEM_PATH])


def clean_environment() -> dict[str, str]:
    """The environment for commands: the search path, and none of zellij's own variables."""
    env = {k: v for k, v in os.environ.items() if k not in ZELLIJ_VARIABLES}
    env["PATH"] = search_path()
    return env


@dataclass
class Tools:
    """Runs commands, logging each step that changes something."""

    dry_run: bool
    log: Callable[[str], None]
    env: dict[str, str] = field(default_factory=clean_environment)
    # Scales every wait; the tests set it to 0 through ZELLIJ_UPGRADE_PAUSE_SCALE.
    pause_scale: float = field(
        default_factory=lambda: float(os.environ.get("ZELLIJ_UPGRADE_PAUSE_SCALE", "1"))
    )

    def read(self, *args: str) -> str:
        """Run a command that changes nothing and return what it printed, even if it failed."""
        try:
            done = subprocess.run(
                args,
                capture_output=True,
                text=True,
                env=self.env,
                stdin=subprocess.DEVNULL,
                check=False,
            )
        except OSError:
            return ""
        return done.stdout

    def act(self, description: str, *args: str) -> str:
        """Run a command that changes something, or in a dry run only say what it would be."""
        if self.dry_run:
            self.log(f"would {description}: {' '.join(args)}")
            return ""
        self.log(description)
        done = subprocess.run(
            args,
            capture_output=True,
            text=True,
            env=self.env,
            stdin=subprocess.DEVNULL,
            check=False,
        )
        if done.returncode != 0:
            detail = (done.stderr or done.stdout).strip()
            msg = f"could not {description} (exit {done.returncode}): {detail}"
            raise RuntimeError(msg)
        return done.stdout

    def pause(self, seconds: float) -> None:
        """Wait, unless this is a dry run."""
        if not self.dry_run:
            time.sleep(seconds * self.pause_scale)

    def wait_for(self, test: Callable[[], bool], *, tries: int = 20, every: float = 2) -> bool:
        """Poll `test` until it holds. A dry run does not wait."""
        if self.dry_run:
            return True
        for _ in range(tries):
            if test():
                return True
            time.sleep(every * self.pause_scale)
        return test()

    # -------------------------------------------------------------------------------------- zellij

    def zellij_version(self) -> str:
        """What `zellij --version` prints, e.g. `zellij 0.46.1`."""
        return self.read("zellij", "--version").strip()

    def running_sessions(self) -> list[str]:
        """Names of the sessions that are running now."""
        return parse_running_sessions(self.read("zellij", "list-sessions", "--no-formatting"))

    def panes(self, session: str) -> list[dict[str, object]]:
        """A session's terminal panes."""
        listing = self.read(
            "zellij", "--session", session, "action", "list-panes", "--json", "--all"
        )
        return terminal_panes(listing)

    def screen(self, session: str, pane_id: int) -> str:
        """What a pane is showing."""
        return self.read(
            "zellij",
            "--session",
            session,
            "action",
            "dump-screen",
            "--pane-id",
            f"terminal_{pane_id}",
        )

    def press(self, session: str, pane_id: int, key: str) -> None:
        """Press a key in a pane."""
        self.act(
            f"press {key} in {session} pane {pane_id}",
            *("zellij", "--session", session, "action", "send-keys"),
            *("--pane-id", f"terminal_{pane_id}", key),
        )

    def type_line(self, session: str, pane_id: int, text: str) -> None:
        """Type a line into a pane and press Enter."""
        self.act(
            f"type into {session} pane {pane_id}: {text}",
            *("zellij", "--session", session, "action", "write-chars"),
            *("--pane-id", f"terminal_{pane_id}", text),
        )
        self.pause(0.5)
        self.press(session, pane_id, "Enter")

    def servers_running(self) -> bool:
        """Whether any zellij server process is still alive."""
        return bool(self.read("pgrep", "-f", "zellij --server").strip())

    # -------------------------------------------------------------------------------- claude code

    def claude_processes(self) -> list[ClaudeProcess]:
        """The live Claude Code sessions that were started from a terminal."""
        home = Path.home() / ".claude"
        found = []
        for path in sorted((home / "sessions").glob("*.json")):
            try:
                record = json.loads(path.read_text())
            except (OSError, ValueError):
                continue
            if not isinstance(record, dict) or record.get("entrypoint") != "cli":
                continue
            args = self.read("ps", "-o", "args=", "-p", str(record.get("pid"))).strip()
            session_id = str(record.get("sessionId") or "")
            if not args or not session_id:
                continue
            transcript = any((home / "projects").glob(f"*/{session_id}.jsonl"))
            found.append(
                ClaudeProcess(
                    session_id=session_id,
                    name=str(record.get("name") or ""),
                    cwd=str(record.get("cwd") or ""),
                    args=args,
                    has_transcript=transcript,
                )
            )
        return found

    # ------------------------------------------------------------------------------- terminal app

    def iterm_running(self) -> bool:
        """Whether this is a Mac with iTerm2 open, which is where windows can be reopened."""
        answer = self.read("osascript", "-e", 'application "iTerm2" is running')
        return answer.strip() == "true"

    def terminal_window_listing(self) -> str:
        """iTerm2's windows and the title of each tab's session."""
        return self.read("osascript", "-e", LIST_TERMINAL_WINDOWS)

    def workspace_listing(self) -> str:
        """AeroSpace's windows as `<id> TAB <workspace>`; empty when AeroSpace is not there."""
        return self.read(
            "aerospace", "list-windows", "--all", "--format", "%{window-id}\t%{workspace}"
        )
