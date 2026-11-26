"""Stand-ins for every command zellij-upgrade runs, sharing one small simulated machine.

`install` writes one executable under each command's name. Each run of one loads the machine from
`$FAKE_WORLD` (a JSON file), appends what it was asked to `calls.log` beside it, acts on the
machine as the real command would, and saves it. A test sets the machine up, runs the real
zellij-upgrade against these, and then reads the calls and the machine back.

The machine:
  version, newer        installed zellij version, and the one Homebrew would upgrade to (or None)
  iterm                 whether iTerm2 is open
  sessions              name -> {"state": running|exited, "panes": [...]}
  windows, workspaces   iTerm2's windows as [[id, [tab titles]]], and window id -> workspace
  claude                pid -> the arguments `ps` shows for a live Claude Code process
  resurrect_fails       sessions that stay exited when attached

`$FAKE_CLAUDE_NEVER_STARTS` names a Claude session id that does not start when resumed.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

COMMANDS = ("zellij", "brew", "osascript", "aerospace", "ps", "pgrep")
WAITING = "Waiting to run: {command}\n<ENTER> run, <ESC> drop to shell, <Ctrl-c> exit"
FIRST_NEW_WINDOW = 500
FIRST_NEW_PID = 7000


def install(bin_dir: Path) -> None:
    """Write an executable for each command into `bin_dir`."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).read_text()
    for name in COMMANDS:
        script = bin_dir / name
        script.write_text(f"#!{sys.executable}\n{source}")
        script.chmod(0o755)


def calls(world_file: Path) -> list[list[str]]:
    """Every command run so far, as [name, *arguments]."""
    log = world_file.with_name("calls.log")
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


def _pane(panes: list[dict], pane_id: str) -> dict:
    number = int(pane_id.removeprefix("terminal_"))
    return next(p for p in panes if p["id"] == number)


def _zellij(world: dict, args: list[str]) -> tuple[str, int]:
    sessions = world["sessions"]
    if args == ["--version"]:
        return f"zellij {world['version']}\n", 0
    if args[:1] == ["list-sessions"]:
        lines = [
            f"{name} [Created 1h ago] "
            + ("(EXITED - attach to resurrect)" if s["state"] != "running" else "")
            for name, s in sessions.items()
        ]
        return "\n".join(lines) + "\n", 0
    if args[:1] == ["kill-all-sessions"]:
        for session in sessions.values():
            session["state"] = "exited"
            for pane in session["panes"]:
                # zellij holds back every pane's command but a plain shell's.
                command = pane.get("pane_command") or ""
                pane["waiting"] = bool(command) and not command.endswith("/nu")
        world["claude"] = {}
        return "", 0
    if "attach" in args:
        name = args[-1]
        if "--layout" in args:
            sessions[name] = {
                "state": "running",
                "panes": [
                    {
                        "id": 0,
                        "tab_name": "Tab #1",
                        "tab_position": 0,
                        "title": "~",
                        "pane_command": "",
                    }
                ],
            }
        elif name not in world.get("resurrect_fails", []) and name in sessions:
            sessions[name]["state"] = "running"
        return "", 0
    if args[:1] == ["--session"]:
        return _zellij_action(world, sessions.get(args[1]), args[3:])
    return "", 1


def _zellij_action(world: dict, session: dict | None, action: list[str]) -> tuple[str, int]:
    if session is None or session["state"] != "running":
        return "Session not found\n", 1
    panes = session["panes"]
    if action[0] == "list-panes":
        plugin = {"id": 0, "is_plugin": True, "plugin_url": "zellij:bars"}
        shown = [{k: v for k, v in p.items() if k != "waiting"} for p in panes]
        return json.dumps([plugin, *shown]), 0
    pane = _pane(panes, action[action.index("--pane-id") + 1])
    if action[0] == "dump-screen":
        waiting = WAITING.format(command=pane["pane_command"]) if pane.get("waiting") else "> \n"
        return waiting, 0
    if action[0] == "send-keys" and action[-1] == "Esc":
        pane["waiting"] = False
        pane["pane_command"] = "/opt/homebrew/bin/nu"
    if action[0] == "write-chars":
        resumed = re.match(r"claude .*--resume (\S+)$", action[-1])
        if resumed and resumed[1] != os.environ.get("FAKE_CLAUDE_NEVER_STARTS"):
            pid = FIRST_NEW_PID + len(world["claude"])
            world["claude"][str(pid)] = "/home/bin/" + action[-1]
            pane["pane_command"] = "/home/bin/" + action[-1]
            record = {
                "pid": pid,
                "sessionId": resumed[1],
                "entrypoint": "cli",
                "name": pane["title"],
                "cwd": "/somewhere",
            }
            sessions_dir = Path(os.environ["HOME"]) / ".claude/sessions"
            sessions_dir.mkdir(parents=True, exist_ok=True)
            (sessions_dir / f"{pid}.json").write_text(json.dumps(record))
    return "", 0


def _osascript(world: dict, args: list[str]) -> tuple[str, int]:
    script = args[-1]
    if "is running" in script:
        return ("true\n" if world["iterm"] else "false\n"), 0
    if "repeat with w in windows" in script:
        lines = []
        for window_id, titles in world["windows"]:
            lines.append(f"W {window_id}")
            lines.extend(f"S {title}" for title in titles)
        return "\n".join(lines) + "\n", 0
    attached = re.search(r'attach (--create )?\\"([^"\\]+)\\"', script)
    if attached:
        name = attached[2]
        if "--layout" in script:
            world["sessions"][name] = {
                "state": "running",
                "panes": [
                    {
                        "id": 0,
                        "tab_name": "Tab #1",
                        "tab_position": 0,
                        "title": "~",
                        "pane_command": "",
                    }
                ],
            }
        elif name not in world.get("resurrect_fails", []) and name in world["sessions"]:
            world["sessions"][name]["state"] = "running"
    world["next_window"] = world.get("next_window", FIRST_NEW_WINDOW) + 1
    return f"window id {world['next_window']}\n", 0


def _brew(world: dict, args: list[str]) -> tuple[str, int]:
    if args[:1] == ["outdated"]:
        return ("zellij\n" if world.get("newer") else ""), 0
    if args[:1] == ["upgrade"] and world.get("newer"):
        world["version"], world["newer"] = world["newer"], None
    return "", 0


def _aerospace(world: dict, args: list[str]) -> tuple[str, int]:
    if args[:1] == ["list-windows"]:
        return "".join(f"{w}\t{ws}\n" for w, ws in world["workspaces"].items()), 0
    return "", 0


def _ps(world: dict, args: list[str]) -> tuple[str, int]:
    found = world["claude"].get(args[-1])
    return (f"{found}\n", 0) if found else ("", 1)


def _pgrep(world: dict, args: list[str]) -> tuple[str, int]:
    del args
    running = any(s["state"] == "running" for s in world["sessions"].values())
    return ("4242\n", 0) if running else ("", 1)


def _main() -> int:
    world_file = Path(os.environ["FAKE_WORLD"])
    name, args = Path(sys.argv[0]).name, sys.argv[1:]
    with world_file.with_name("calls.log").open("a") as log:
        log.write(json.dumps([name, *args]) + "\n")
    world = json.loads(world_file.read_text())
    handler = {
        "zellij": _zellij,
        "brew": _brew,
        "osascript": _osascript,
        "aerospace": _aerospace,
        "ps": _ps,
        "pgrep": _pgrep,
    }[name]
    output, status = handler(world, args)
    world_file.write_text(json.dumps(world))
    sys.stdout.write(output)
    return status


if __name__ == "__main__":
    sys.exit(_main())
