"""Two ways to bring sessions back after the restart, and to start a process outside zellij.

On a Mac with iTerm2 open, each session is attached in a terminal window, so its server starts in
the GUI login session and inherits what macOS grants to apps there. Everywhere else a session is
resurrected detached, in the background, and is simply there at the next attach.

iTerm2 windows are opened with the `zellij` profile, for its look and its close-on-exit, but with
the profile's command replaced: that command always opens the session chooser, and the chooser
cannot be driven by another command. AppleScript is used because it can replace the command, and
because the window id it returns is the id AeroSpace knows the window by.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from zellij_upgrade.inventory import applescript_string, shell_quote_double

if TYPE_CHECKING:
    from pathlib import Path

    from zellij_upgrade.inventory import Window
    from zellij_upgrade.tools import Tools


class Host(Protocol):
    """Where sessions are brought back."""

    description: str

    def reopen(self, window: Window) -> None:
        """Bring back the sessions of one recorded window."""

    def recreate(self, session: str, layout: Path, workspace: str | None) -> None:
        """Start a session afresh from a saved layout, when it did not come back."""

    def relaunch(self, command: list[str], log: Path) -> None:
        """Start `command` where ending every zellij session cannot end it."""


def zellij_path(tools: Tools) -> str:
    """The zellij binary's full path, since a terminal window starts with a bare PATH."""
    return shutil.which("zellij", path=tools.env["PATH"]) or "zellij"


@dataclass
class ITermHost:
    """A Mac with iTerm2 open."""

    tools: Tools
    description: str = "iTerm2 windows"

    def _open(self, target: str, profile: str, script: str) -> str | None:
        """Open a window or tab running `sh -c script`; return the window id iTerm2 reports."""
        command = f"/bin/sh -c '{script}'"
        answer = self.tools.act(
            f"open {target}: {script}",
            "osascript",
            "-e",
            f'tell application "iTerm2" to {target} with profile "{profile}" command '
            + applescript_string(command),
        )
        digits = "".join(ch for ch in answer.strip().rsplit(" ", 1)[-1] if ch.isdigit())
        return digits or None

    def _place(self, window_id: str | None, workspace: str | None) -> None:
        if workspace and (window_id or self.tools.dry_run):
            self.tools.act(
                f"move window {window_id} to workspace {workspace}",
                *("aerospace", "move-node-to-workspace", "--window-id", str(window_id), workspace),
            )

    def reopen(self, window: Window) -> None:
        """Open one window, a tab per session, and put it on its workspace."""
        zellij = zellij_path(self.tools)
        first, *rest = window.sessions
        window_id = self._open(
            "create window", "zellij", f"exec {zellij} attach {shell_quote_double(first)}"
        )
        for session in rest:
            self.tools.pause(2)
            self._open(
                f"tell window id {window_id or 0} to create tab",
                "zellij",
                f"exec {zellij} attach {shell_quote_double(session)}",
            )
        self.tools.pause(3)
        self._place(window_id, window.workspace)

    def recreate(self, session: str, layout: Path, workspace: str | None) -> None:
        """Open a window that starts the session from its backed-up layout."""
        script = (
            f"exec {zellij_path(self.tools)} --layout {shell_quote_double(str(layout))}"
            f" attach --create {shell_quote_double(session)}"
        )
        self._place(self._open("create window", "zellij", script), workspace)

    def relaunch(self, command: list[str], log: Path) -> None:
        """Run `command` in a new window of the `zsh` profile, which is not inside zellij.

        A login shell runs it, so that it gets the PATH the command itself was started with.
        """
        del log  # the window shows the output; the command writes its own log
        line = shlex.join(command)
        if "'" in line:
            msg = f"cannot start {line!r} in a terminal window: it contains a single quote"
            raise ValueError(msg)
        self._open(
            "create window", "zsh", f"NO_ZELLIJ=1 exec /bin/zsh -lc {shell_quote_double(line)}"
        )


@dataclass
class BackgroundHost:
    """A machine with no terminal app to reopen windows in."""

    tools: Tools
    description: str = "background sessions"

    def reopen(self, window: Window) -> None:
        """Resurrect each of the window's sessions, detached."""
        for session in window.sessions:
            self.tools.act(
                f"resurrect {session} in the background",
                *("zellij", "attach", "--create-background", session),
            )

    def recreate(self, session: str, layout: Path, workspace: str | None) -> None:
        """Start the session afresh, detached, from its backed-up layout."""
        del workspace
        self.tools.act(
            f"recreate {session} from its backed-up layout",
            *("zellij", "--layout", str(layout), "attach", "--create-background", session),
        )

    def relaunch(self, command: list[str], log: Path) -> None:
        """Start `command` in its own process session, writing to `log`."""
        with log.open("ab") as out:
            subprocess.Popen(
                command,
                env=self.tools.env,
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )


def pick_host(tools: Tools) -> Host:
    """iTerm2 where it is open, otherwise the background."""
    return ITermHost(tools) if tools.iterm_running() else BackgroundHost(tools)
