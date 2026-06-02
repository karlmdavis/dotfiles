"""Transient HUD shown when switching AeroSpace workspaces.

`main()` is the entry point invoked by the thin HUD shim
(~/.config/aerospace/hud-display-workspace-name.py), which the AeroSpace keybindings call as
`exec-and-forget ~/.config/aerospace/hud-display-workspace-name.py <ID> ["<prefix>"]`. It resolves
the workspace's icon/name/hint from workspaces.yaml and shows a brief on-screen alert via
Hammerspoon (preferred) or falls back to a macOS notification.

The display/URL/notification builders are pure functions so they're unit-testable without firing a
real alert. `--dry-run` prints the action that WOULD run (Hammerspoon URL or osascript body)
instead of executing it — handy for manual checks; pytest exercises the pure builders directly.
"""

from __future__ import annotations

import subprocess
import sys
from urllib.parse import quote

from aerospace_workspaces.workspaces import aerospace_bin, load_workspaces, workspaces_yaml


def resolve_display(workspace_id: str, prefix: str, records: dict[str, dict[str, str]]) -> tuple[str, str]:
    """Return (display, hint) for a workspace.

    `display` is "<icon> <prefix><name>" (icon and its trailing space omitted when absent; name
    falls back to the bare id). `hint` is the workspace's hint or "".
    """
    record = records.get(workspace_id, {})
    name = record.get("name") or workspace_id
    icon = record.get("icon", "")
    hint = record.get("hint", "")
    body = f"{prefix}{name}"
    display = f"{icon} {body}" if icon else body
    return display, hint


def build_hammerspoon_url(display: str, hint: str) -> str:
    """Build the hammerspoon://workspace URL, percent-encoding name (and hint when present)."""
    url = f"hammerspoon://workspace?name={quote(display)}"
    if hint:
        url += f"&hint={quote(hint)}"
    return url


def build_osascript_body(display: str, hint: str) -> str:
    """Build the notification body for the osascript fallback ("<display>" or "<display> — <hint>")."""
    return f"{display} — {hint}" if hint else display


def _focused_workspace() -> str:
    """The currently focused workspace id (empty string on any failure)."""
    try:
        return subprocess.run(
            [aerospace_bin(), "list-workspaces", "--focused"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return ""


def _hammerspoon_running() -> bool:
    """True if the Hammerspoon app is running (so it can catch the URL event)."""
    return subprocess.run(["pgrep", "-xq", "Hammerspoon"]).returncode == 0


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    dry_run = False
    if "--dry-run" in args:
        dry_run = True
        args = [a for a in args if a != "--dry-run"]

    workspace_id = args[0] if args else _focused_workspace()
    if not workspace_id:
        return
    prefix = args[1] if len(args) > 1 else ""

    records, _ = load_workspaces(workspaces_yaml())
    display, hint = resolve_display(workspace_id, prefix, records)

    if _hammerspoon_running():
        url = build_hammerspoon_url(display, hint)
        if dry_run:
            print(url)
            return
        subprocess.run(["open", "-g", url], check=False)
    else:
        body = build_osascript_body(display, hint)
        if dry_run:
            print(body)
            return
        # Launch Hammerspoon so it's ready (and a login item) next time; it won't catch this event.
        subprocess.run(["open", "-ga", "Hammerspoon"], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(
            ["osascript", "-e", f'display notification "{_osascript_escape(body)}" with title "Workspace"'],
            check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


def _osascript_escape(text: str) -> str:
    """Escape a string for embedding in an AppleScript double-quoted literal."""
    return text.replace("\\", "\\\\").replace('"', '\\"')
