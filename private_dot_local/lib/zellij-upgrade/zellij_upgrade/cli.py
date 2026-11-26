"""The `zellij-upgrade` command: the order of the steps, and what is said along the way.

It runs in two parts, because ending every zellij session would end the command too when it was
started from inside one.

`start` takes the inventory, shows it, and asks. It changes nothing but its own state folder. It
then hands over to `run`, which it starts outside zellij: in a new terminal window, or as a
detached process. Started outside zellij already, it simply carries on.

`run` waits for the Claude sessions to stop working, upgrades zellij, ends every session, brings
each one back, and resumes each Claude session by typing into a shell in its pane: `cd` to its
folder, then `claude ... --resume <id>`. Claude is never made the pane's own command, so that
leaving Claude leaves a shell in the right folder. It writes a report, and removes the old zellij
version only if everything came back.

Nothing is ended on a guess. What cannot be resumed is found by the inventory and shown before the
question is asked, and a pane that cannot be matched afterwards is left alone and reported with
the command to run in it by hand.
"""

from __future__ import annotations

import argparse
import functools
import os
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from zellij_upgrade.hosts import Host, pick_host, zellij_path
from zellij_upgrade.inventory import (
    WAITING_TO_RUN,
    ClaudePane,
    Inventory,
    build_session,
    build_windows,
    find_origin,
    match_pane,
    pane_number,
    parse_terminal_windows,
    parse_workspaces,
)
from zellij_upgrade.tools import Tools

INVENTORY_FILE = "inventory.json"
LOG_FILE = "run.log"
REPORT_FILE = "report.md"
BACKUP_DIR = "session-cache"
METADATA_FILE = "session-metadata.kdl"
LAYOUT_FILE = "session-layout.kdl"
EXIT_INCOMPLETE = 1
EXIT_REFUSED = 2


def state_home() -> Path:
    """Where each run keeps its folder."""
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local/state")
    return Path(base) / "zellij-upgrade"


def new_state_dir() -> Path:
    """Make this run's folder, named for the time, with a suffix if that name is taken."""
    stamp = time.strftime("%Y-%m-%d-%H%M%S")
    for suffix in ("", *(f"-{n}" for n in range(2, 100))):
        state = state_home() / f"{stamp}{suffix}"
        try:
            state.mkdir(parents=True)
        except FileExistsError:
            continue
        return state
    msg = f"could not make a state folder under {state_home()}"
    raise RuntimeError(msg)


def cache_dir() -> Path:
    """Where zellij keeps its saved sessions."""
    if sys.platform == "darwin":
        return Path.home() / "Library/Caches/org.Zellij-Contributors.Zellij"
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "zellij"


# ------------------------------------------------------------------------------------------- start


def take_inventory(tools: Tools) -> Inventory:
    """Record the running sessions, their Claude panes, and the windows that show them."""
    processes = tools.claude_processes()
    running = tools.running_sessions()
    sessions = []
    problems: list[str] = []
    panes_by_session = {name: tools.panes(name) for name in running}
    # A session with no terminal pane is a chooser nobody picked from: there is nothing to restore.
    restorable = [name for name in running if panes_by_session[name]]
    for name in restorable:
        session, found = build_session(name, panes_by_session[name], processes)
        sessions.append(session)
        problems.extend(found)
    terminal_windows: list[tuple[str, list[str]]] = []
    workspaces: dict[str, str] = {}
    if tools.iterm_running():
        terminal_windows = parse_terminal_windows(tools.terminal_window_listing())
        workspaces = parse_workspaces(tools.workspace_listing())
    own_session = os.environ.get("ZELLIJ_SESSION_NAME")
    return Inventory(
        taken=time.strftime("%Y-%m-%d %H:%M:%S"),
        zellij_version=tools.zellij_version(),
        sessions=tuple(sessions),
        windows=build_windows(terminal_windows, workspaces, restorable),
        problems=tuple(problems),
        origin=find_origin(
            own_session,
            os.environ.get("ZELLIJ_PANE_ID"),
            panes_by_session.get(own_session or "", []),
        ),
    )


def describe(inventory: Inventory, host: Host) -> str:
    """The inventory as the text shown before the question."""
    lines = [
        f"{inventory.zellij_version} is installed. Sessions come back as {host.description}.",
        "",
    ]
    for window in inventory.windows:
        where = f"workspace {window.workspace}" if window.workspace else "no particular workspace"
        lines.append(f"Window on {where}: {', '.join(window.sessions)}")
    for session in inventory.sessions:
        lines.append("")
        lines.append(f"{session.name}:")
        if not session.claude_panes:
            lines.append("  no Claude sessions")
        for pane in session.claude_panes:
            what = f"{pane.resume_command}   (in {pane.cwd})" if pane.session_id else "NOT RESUMED"
            lines.append(f"  {pane.tab}: {what}")
    if not inventory.sessions:
        lines.append("No zellij sessions are running.")
    lines.append("")
    if inventory.problems:
        lines.append("Problems (these panes are left at a shell):")
        lines.extend(f"  - {problem}" for problem in inventory.problems)
    else:
        lines.append("No problems found.")
    return "\n".join(lines)


def back_up(state: Path, tools: Tools) -> None:
    """Copy zellij's saved sessions and the current binary into the state folder."""
    saved = cache_dir() / "contract_version_1"
    if saved.is_dir():
        shutil.copytree(saved, state / BACKUP_DIR, symlinks=True)
    binary = Path(zellij_path(tools))
    if binary.is_file():
        shutil.copy2(binary.resolve(), state / "zellij-before-upgrade")


def confirmed(*, yes: bool) -> bool:
    """Ask before ending anything, unless told not to."""
    if yes:
        return True
    if not sys.stdin.isatty():
        print("Not asking, since nobody is at the keyboard: pass --yes to go ahead.")
        return False
    answer = input("\nEnd every zellij session, upgrade, and bring all of this back? [y/N] ")
    return answer.strip().lower() in {"y", "yes"}


def start(*, dry_run: bool, yes: bool, force: bool) -> int:
    """Take and show the inventory, ask, and hand over to `run` outside zellij."""
    reader = Tools(dry_run=False, log=print)
    host = pick_host(reader)
    inventory = take_inventory(reader)
    print(describe(inventory, host))
    outdated = bool(reader.read("brew", "outdated", "--quiet", "zellij").strip())
    if not outdated and not force:
        print(
            "\nHomebrew has no newer zellij, so there is nothing to do (--force restarts anyway)."
        )
        return 0
    if not dry_run and not confirmed(yes=yes):
        return EXIT_REFUSED

    state = new_state_dir()
    (state / INVENTORY_FILE).write_text(inventory.to_json())
    if not dry_run:
        back_up(state, reader)
    if "ZELLIJ" not in os.environ:
        return run(state, dry_run=dry_run, force=force, hold=False)

    command = [str(Path(sys.argv[0]).resolve()), "--run", str(state), "--hold"]
    # The second half must load the same package as this half (the shim's seam for the source copy).
    lib_dir = os.environ.get("ZELLIJ_UPGRADE_LIB_DIR")
    if lib_dir:
        command = ["/usr/bin/env", f"ZELLIJ_UPGRADE_LIB_DIR={lib_dir}", *command]
    command += ["--dry-run"] if dry_run else []
    command += ["--force"] if force else []
    host.relaunch(command, state / LOG_FILE)
    print(f"\nCarrying on outside zellij. The log is {state / LOG_FILE}")
    return 0


# --------------------------------------------------------------------------------------------- run


@dataclass
class Run:
    """One upgrade in progress: the tools, the host, and what is going into the report."""

    state: Path
    tools: Tools
    host: Host
    inventory: Inventory
    notes: list[str] = field(default_factory=list)
    incomplete: bool = False

    def problem(self, text: str) -> None:
        """Record something that did not come back."""
        self.incomplete = True
        self.notes.append(f"- NOT DONE: {text}")
        self.tools.log(f"NOT DONE: {text}")

    def wait_until_idle(self) -> None:
        """Hold off while any Claude session is in the middle of a turn."""
        while True:
            busy = [
                f"{session.name} / {pane.get('tab_name')}"
                for session in self.inventory.sessions
                for pane in self.tools.panes(session.name)
                if _is_working(pane)
            ]
            if not busy:
                self.tools.log("no Claude session is in the middle of a turn")
                return
            if self.tools.dry_run:
                self.tools.log(f"would wait for: {'; '.join(busy)}")
                return
            self.tools.log(f"waiting for: {'; '.join(busy)}   (Ctrl-C stops; nothing changed)")
            self.tools.pause(5)

    def upgrade(self, *, force: bool) -> bool:
        """Upgrade zellij; False when there was nothing newer and no --force."""
        before = self.tools.zellij_version()
        if self.tools.read("brew", "outdated", "--quiet", "zellij").strip():
            self.tools.act("upgrade zellij with Homebrew", "brew", "upgrade", "zellij")
        after = self.tools.zellij_version()
        self.notes.append(f"zellij was `{before}` and is now `{after}`.")
        if before == after and not force and not self.tools.dry_run:
            self.tools.log("zellij did not change version; nothing was ended")
            return False
        return True

    def end_sessions(self) -> None:
        """End every session and wait for the old servers to go."""
        self.tools.act("end all zellij sessions", "zellij", "kill-all-sessions", "--yes")
        if not self.tools.wait_for(lambda: not self.tools.servers_running()):
            self.problem("some old zellij servers are still running")
        self.tools.pause(3)

    def bring_back(self) -> None:
        """Reopen each window; a session that is missing is recreated from its backed-up layout."""
        for window in self.inventory.windows:
            self.host.reopen(window)
            if self.tools.dry_run:
                continue
            for name in window.sessions:
                if self.tools.wait_for(functools.partial(self._is_up, name), tries=8):
                    self.notes.append(f"- `{name}` is back ({_where(window.workspace)}).")
                    continue
                layout = self._backed_up_layout(name)
                if layout is None:
                    self.problem(f"`{name}` did not come back and has no backed-up layout")
                    continue
                self.host.recreate(name, layout, window.workspace)
                if self.tools.wait_for(functools.partial(self._is_up, name), tries=8):
                    self.notes.append(f"- `{name}` did not resurrect; recreated from its backup.")
                else:
                    self.problem(f"`{name}` did not come back, even from its backed-up layout")

    def _is_up(self, name: str) -> bool:
        return name in self.tools.running_sessions() and bool(self.tools.panes(name))

    def _backed_up_layout(self, name: str) -> Path | None:
        for folder in sorted((self.state / BACKUP_DIR / "session_info").glob("*")):
            metadata = folder / METADATA_FILE
            named = folder.name == name or (
                metadata.is_file() and f'name "{name}"' in metadata.read_text(errors="replace")
            )
            if named and (folder / LAYOUT_FILE).is_file():
                return folder / LAYOUT_FILE
        return None

    def resume_all(self) -> None:
        """Resume every Claude session, the one the upgrade was started from last."""
        origin = self.inventory.origin
        last: list[tuple[str, ClaudePane]] = []
        for session in self.inventory.sessions:
            for pane in session.claude_panes:
                if origin and (session.name, pane.tab) == (origin.session, origin.tab):
                    last.append((session.name, pane))
                else:
                    self.resume(session.name, pane)
        for name, pane in last:
            self.resume(name, pane)

    def resume(self, session: str, pane: ClaudePane) -> None:
        """Shell first, then `cd`, then `claude ... --resume <id>`, typed into the shell."""
        where = f"{session} / {pane.tab}"
        if not pane.session_id or not pane.cwd:
            self.problem(f"{where} was not resumed (see the problems found beforehand)")
            return
        by_hand = f"`cd {pane.cwd}` then `{pane.resume_command}`"
        if self.tools.dry_run:
            self.tools.log(f"would resume {where}: {by_hand}")
            return
        panes = self.tools.panes(session)
        ids = [i for i in map(pane_number, panes) if i is not None]
        screens = {i: self.tools.screen(session, i) for i in ids}
        pane_id = match_pane(pane, panes, screens)
        if pane_id is None:
            self.problem(f"{where}: could not tell which pane to use. By hand: {by_hand}")
            return
        if WAITING_TO_RUN in screens.get(pane_id, ""):
            self.tools.press(session, pane_id, "Esc")
            self.tools.wait_for(
                lambda: WAITING_TO_RUN not in self.tools.screen(session, pane_id), tries=10, every=1
            )
        self.tools.type_line(session, pane_id, f"cd {pane.cwd}")
        self.tools.type_line(session, pane_id, pane.resume_command)
        self.notes.append(f"- resumed {where} ({pane.session_id[:8]}).")

    def check_claude(self) -> None:
        """Confirm that each resumed Claude session is running again."""
        wanted = {
            pane.session_id: f"{session.name} / {pane.tab}"
            for session in self.inventory.sessions
            for pane in session.claude_panes
            if pane.session_id
        }
        if self.tools.dry_run or not wanted:
            return

        def missing() -> set[str]:
            return set(wanted) - {p.session_id for p in self.tools.claude_processes()}

        self.tools.wait_for(lambda: not missing(), tries=30)
        for session_id in sorted(missing()):
            self.problem(f"{wanted[session_id]}: Claude session {session_id[:8]} is not running")

    def finish(self) -> None:
        """Write the report, remove the old version if all is well, and tell the origin pane."""
        if not self.incomplete:
            self.tools.act("remove the old zellij version", "brew", "cleanup", "zellij")
        outcome = "Something did not come back." if self.incomplete else "Everything came back."
        report = "\n".join(
            [f"# zellij upgrade, {time.strftime('%Y-%m-%d %H:%M')}", "", outcome, ""]
        )
        report += "\n".join(self.notes) + "\n"
        if not self.tools.dry_run:
            (self.state / REPORT_FILE).write_text(report)
        self.tools.log(report)
        origin = self.inventory.origin
        if origin and not self.tools.dry_run:
            for pane in self.tools.panes(origin.session):
                number = pane_number(pane)
                if pane.get("tab_name") == origin.tab and number is not None:
                    self.tools.pause(10)
                    self.tools.type_line(
                        origin.session,
                        number,
                        f"The zellij upgrade has finished. {outcome} Read"
                        f" {self.state / REPORT_FILE} and check the result.",
                    )
                    break


def _is_working(pane: dict[str, object]) -> bool:
    statuses = pane.get("program_status")
    return isinstance(statuses, list) and any(
        isinstance(s, dict) and s.get("state") == "Working" for s in statuses
    )


def _where(workspace: str | None) -> str:
    return f"workspace {workspace}" if workspace else "no particular workspace"


def run(state: Path, *, dry_run: bool, force: bool, hold: bool) -> int:
    """Do the upgrade recorded in `state`. Must not be inside zellij."""
    log_path = state / LOG_FILE

    def log(message: str) -> None:
        line = f"{time.strftime('%H:%M:%S')}  {message}"
        print(line, flush=True)
        with log_path.open("a") as out:
            out.write(line + "\n")

    tools = Tools(dry_run=dry_run, log=log)
    tools.env.update(HOMEBREW_NO_INSTALL_CLEANUP="1", HOMEBREW_NO_AUTO_UPDATE="1")
    inventory = Inventory.from_json((state / INVENTORY_FILE).read_text())
    this = Run(state=state, tools=tools, host=pick_host(tools), inventory=inventory)
    log(f"{'DRY RUN' if dry_run else 'RUN'} of the inventory taken {inventory.taken}")
    try:
        this.wait_until_idle()
        if this.upgrade(force=force):
            this.end_sessions()
            this.bring_back()
            this.resume_all()
            this.check_claude()
            this.finish()
    except (RuntimeError, ValueError, OSError) as error:
        this.incomplete = True
        log(f"STOPPED: {error}")
    except KeyboardInterrupt:
        this.incomplete = True
        log("STOPPED by Ctrl-C")
    if hold and sys.stdin.isatty():
        input("\nPress Enter to close this window. ")
    return EXIT_INCOMPLETE if this.incomplete else 0


def main(argv: list[str] | None = None) -> int:
    """Parse the arguments and run the right half."""
    parser = argparse.ArgumentParser(
        prog="zellij-upgrade",
        description="Upgrade zellij with Homebrew, then bring every session, terminal window and"
        " Claude Code session back as it was.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="show what would be done; change nothing"
    )
    parser.add_argument("--yes", action="store_true", help="do not ask before ending sessions")
    parser.add_argument(
        "--force", action="store_true", help="restart everything even with no newer zellij"
    )
    parser.add_argument("--run", metavar="STATE_DIR", help=argparse.SUPPRESS)
    parser.add_argument("--hold", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.run:
        if "ZELLIJ" in os.environ:
            print("--run must be started outside zellij.", file=sys.stderr)
            return EXIT_REFUSED
        return run(Path(args.run), dry_run=args.dry_run, force=args.force, hold=args.hold)
    return start(dry_run=args.dry_run, yes=args.yes, force=args.force)
