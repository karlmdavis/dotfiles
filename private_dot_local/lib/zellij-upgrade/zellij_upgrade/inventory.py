"""What was running before an upgrade, as plain data, and the pure functions that build it.

Nothing here runs a command or reads a file: every function takes the text or the parsed JSON that
a command printed. That is what lets the decisions be tested directly.

The inventory records three things. Which zellij sessions are running, and in each one which panes
hold a Claude Code session (with the id, folder and flags needed to resume it). And, where a
terminal app shows them, which sessions share a window and which workspace that window is on.

Anything that would stop a pane from being resumed is found here, before a single session is
ended, and reported as a problem. A pane with a problem is left at its shell after the restart.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass

# `zellij list-sessions --no-formatting` line: `<name> [Created <age> ago]<flags>`. The greedy name
# anchors on the LAST ` [Created `, since session names may hold spaces, parens, and brackets.
SESSION_LINE = re.compile(r"^(?P<name>.+) \[Created [^\]]* ago\](?P<flags>.*)$")
# What zellij shows in a resurrected pane whose command it has not run yet.
WAITING_TO_RUN = "Waiting to run"
# Claude Code marks a pane's title with one of these while it has no other way to show status.
TITLE_MARKS = "✳⠂⠐✻ "
# Flags that say which conversation to open, with whether each takes a value. They are dropped from
# a session's recorded flags, because the resume command names the conversation itself.
CONVERSATION_FLAGS = {
    "--resume": True,
    "-r": True,
    "--name": True,
    "-n": True,
    "--continue": False,
    "-c": False,
    "--fork-session": False,
}


@dataclass(frozen=True)
class ClaudePane:
    """A pane that held a Claude Code session, and what is needed to resume it there."""

    tab: str
    title: str
    session_id: str | None
    cwd: str | None
    flags: tuple[str, ...]

    @property
    def resume_command(self) -> str:
        """The command typed into the pane's shell to bring the session back."""
        return " ".join(["claude", *self.flags, "--resume", self.session_id or ""])


@dataclass(frozen=True)
class Session:
    """A running zellij session and the Claude panes in it."""

    name: str
    claude_panes: tuple[ClaudePane, ...]


@dataclass(frozen=True)
class Window:
    """A terminal window: the sessions in its tabs, in order, and its workspace if it has one."""

    workspace: str | None
    sessions: tuple[str, ...]


@dataclass(frozen=True)
class Origin:
    """The pane the upgrade was started from, when that pane holds a Claude session."""

    session: str
    tab: str


@dataclass(frozen=True)
class Inventory:
    """Everything recorded before the upgrade."""

    taken: str
    zellij_version: str
    sessions: tuple[Session, ...]
    windows: tuple[Window, ...]
    problems: tuple[str, ...]
    origin: Origin | None

    def to_json(self) -> str:
        """Serialise for the state folder."""
        return json.dumps(asdict(self), indent=1)

    @staticmethod
    def from_json(text: str) -> Inventory:
        """Read back what `to_json` wrote."""
        raw = json.loads(text)
        sessions = tuple(
            Session(
                name=s["name"],
                claude_panes=tuple(
                    ClaudePane(
                        tab=p["tab"],
                        title=p["title"],
                        session_id=p["session_id"],
                        cwd=p["cwd"],
                        flags=tuple(p["flags"]),
                    )
                    for p in s["claude_panes"]
                ),
            )
            for s in raw["sessions"]
        )
        windows = tuple(
            Window(workspace=w["workspace"], sessions=tuple(w["sessions"])) for w in raw["windows"]
        )
        origin = Origin(**raw["origin"]) if raw["origin"] else None
        return Inventory(
            taken=raw["taken"],
            zellij_version=raw["zellij_version"],
            sessions=sessions,
            windows=windows,
            problems=tuple(raw["problems"]),
            origin=origin,
        )


@dataclass(frozen=True)
class ClaudeProcess:
    """A live Claude Code session started from a terminal, as its session file and `ps` show it."""

    session_id: str
    name: str
    cwd: str
    args: str
    has_transcript: bool


def parse_running_sessions(listing: str) -> list[str]:
    """Names of the running sessions in `zellij list-sessions --no-formatting` output."""
    names = []
    for line in listing.splitlines():
        match = SESSION_LINE.match(line.strip())
        if match and "EXITED" not in match["flags"]:
            names.append(match["name"])
    return names


def terminal_panes(panes_json: str) -> list[dict[str, object]]:
    """The terminal panes in `zellij action list-panes --json --all` output, in tab order."""
    try:
        panes = json.loads(panes_json)
    except ValueError:
        return []
    if not isinstance(panes, list):
        return []
    terminals = [p for p in panes if isinstance(p, dict) and not p.get("is_plugin")]
    return sorted(terminals, key=lambda p: (_number(p.get("tab_position")), _number(p.get("id"))))


def _number(value: object) -> int:
    return value if isinstance(value, int) else 0


def pane_number(pane: dict[str, object]) -> int | None:
    """A pane's id, as zellij's `terminal_<n>` names it."""
    value = pane.get("id")
    return value if isinstance(value, int) else None


def pane_command(pane: dict[str, object]) -> str:
    """The command zellij reports for a pane, or an empty string."""
    for key in ("pane_command", "terminal_command"):
        value = pane.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def is_claude_pane(pane: dict[str, object]) -> bool:
    """Whether a pane's command is Claude Code."""
    words = pane_command(pane).split()
    return bool(words) and words[0].rsplit("/", 1)[-1] == "claude"


def clean_title(title: object) -> str:
    """A pane title without Claude Code's status marks."""
    return title.lstrip(TITLE_MARKS).strip() if isinstance(title, str) else ""


def resume_flags(args: str) -> tuple[str, ...]:
    """The flags to resume a session with, from the arguments its process was started with.

    `ps` prints arguments unquoted, so a value with spaces (a session name) arrives as several
    words. A flag that takes a value therefore swallows every word up to the next flag.
    """
    kept: list[str] = []
    swallowing = False
    for word in args.split()[1:]:
        if word.startswith("-"):
            swallowing = CONVERSATION_FLAGS.get(word, False)
            if word not in CONVERSATION_FLAGS:
                kept.append(word)
        elif not swallowing:
            kept.append(word)
    return tuple(kept)


def build_session(
    name: str, panes: list[dict[str, object]], processes: list[ClaudeProcess]
) -> tuple[Session, list[str]]:
    """One session's Claude panes, each joined to its Claude session, plus any problems."""
    problems: list[str] = []
    claude_panes: list[ClaudePane] = []
    per_tab: dict[str, int] = {}
    for pane in panes:
        if not is_claude_pane(pane):
            continue
        tab = str(pane.get("tab_name") or "")
        title = clean_title(pane.get("title"))
        per_tab[tab] = per_tab.get(tab, 0) + 1
        where = f"{name} / {tab}"
        matches = [p for p in processes if p.name == title]
        found = matches[0] if len(matches) == 1 else None
        if found is None:
            problems.append(
                f"{where}: {len(matches)} running Claude sessions are named {title!r}, so the pane"
                " cannot be matched to one"
            )
        elif not found.has_transcript:
            problems.append(
                f"{where}: Claude session {found.session_id[:8]} has no saved conversation yet (it"
                " has not taken a turn), so there is nothing to resume"
            )
            found = None
        claude_panes.append(
            ClaudePane(
                tab=tab,
                title=title,
                session_id=found.session_id if found else None,
                cwd=found.cwd if found else None,
                flags=resume_flags(found.args) if found else (),
            )
        )
    for tab, count in per_tab.items():
        if count > 1:
            problems.append(
                f"{name} / {tab}: {count} Claude panes share this tab and cannot be told apart"
                " after a restart"
            )
            claude_panes = [
                ClaudePane(p.tab, p.title, None, None, ()) if p.tab == tab else p
                for p in claude_panes
            ]
    return Session(name=name, claude_panes=tuple(claude_panes)), problems


def parse_terminal_windows(listing: str) -> list[tuple[str, list[str]]]:
    """Windows and the zellij session in each tab, from the terminal app's listing.

    The listing has a `W <window id>` line per window and an `S <session title>` line per tab.
    A tab attached to zellij is titled `<zellij session> | <tab name> (zellij)`.
    """
    windows: list[tuple[str, list[str]]] = []
    for raw in listing.splitlines():
        line = raw.strip()
        if line.startswith("W "):
            windows.append((line[2:].strip(), []))
        elif line.startswith("S ") and windows:
            title = line[2:].strip().removesuffix(" (zellij)")
            windows[-1][1].append(title.split(" | ")[0])
    return windows


def parse_workspaces(listing: str) -> dict[str, str]:
    """Window id to workspace, from `aerospace list-windows` printed as `<id> TAB <workspace>`."""
    workspaces = {}
    for line in listing.splitlines():
        window_id, _, workspace = line.partition("\t")
        if window_id.strip() and workspace.strip():
            workspaces[window_id.strip()] = workspace.strip()
    return workspaces


def build_windows(
    terminal_windows: list[tuple[str, list[str]]], workspaces: dict[str, str], running: list[str]
) -> tuple[Window, ...]:
    """The windows to reopen: recorded ones first, then one for each session that had none."""
    windows: list[Window] = []
    placed: set[str] = set()
    for window_id, titles in terminal_windows:
        sessions = tuple(t for t in titles if t in running and t not in placed)
        if sessions:
            placed.update(sessions)
            windows.append(Window(workspace=workspaces.get(window_id), sessions=sessions))
    windows.extend(
        Window(workspace=None, sessions=(name,)) for name in running if name not in placed
    )
    return tuple(windows)


def find_origin(
    session: str | None, pane_id: str | None, panes: list[dict[str, object]]
) -> Origin | None:
    """The tab of the pane the command was started from, if that pane holds Claude."""
    if not session or pane_id is None or not pane_id.isdigit():
        return None
    for pane in panes:
        if pane.get("id") == int(pane_id) and is_claude_pane(pane):
            return Origin(session=session, tab=str(pane.get("tab_name") or ""))
    return None


def match_pane(
    recorded: ClaudePane, panes: list[dict[str, object]], screens: dict[int, str]
) -> int | None:
    """The id of the restarted pane that should host `recorded`, or None when it is unclear.

    Pane ids change across a restart, so the pane is found by its tab's name. Within the tab it is
    the one pane that zellij is holding a `claude` command for, or that already runs one.
    """
    candidates = []
    for pane in panes:
        pane_id = pane.get("id")
        if pane.get("tab_name") != recorded.tab or not isinstance(pane_id, int):
            continue
        screen = screens.get(pane_id, "")
        if is_claude_pane(pane) or (WAITING_TO_RUN in screen and "claude" in screen):
            candidates.append(pane_id)
    return candidates[0] if len(candidates) == 1 else None


def applescript_string(text: str) -> str:
    """`text` as an AppleScript string literal."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def shell_quote_double(text: str) -> str:
    """`text` inside double quotes, safe within the single-quoted `sh -c` scripts built here."""
    if "'" in text:
        msg = f"cannot pass {text!r} to a terminal window: it contains a single quote"
        raise ValueError(msg)
    return '"' + re.sub(r'(["\\$`])', r"\\\1", text) + '"'
