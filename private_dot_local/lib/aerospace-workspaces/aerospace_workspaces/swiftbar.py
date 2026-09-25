"""SwiftBar menu-bar rendering for the AeroSpace workspace indicator.

`main()` is the entry point invoked by the thin SwiftBar plugin shim
(~/.config/swiftbar/plugins/aerospace-workspaces.10s.py). It queries AeroSpace, then renders:

  - a menu-bar title of the focused workspace as "<emoji> <id>: <name>" (name truncated so it
    doesn't overrun the bar);
  - a dropdown listing every workspace the same way (declared workspaces first, in file order),
    each switching to that workspace on click, with a hover tooltip when the workspace has a hint;
  - under each workspace, its open windows as an indented submenu, each focusing that exact window.

`render()` is pure (all inputs injected) so it's unit-testable without a live AeroSpace.

Every `aerospace` call is bounded (see `run_aerospace`): the server silently stops answering focus
queries while the screen is locked or Universal Control has the cursor, and an unbounded call would
never return — SwiftBar then never re-runs the plugin, and the menu-bar item freezes on stale
output until the stuck processes are killed by hand. On any failure `main()` prints a small
"unavailable" menu instead, and the next 10s tick simply tries again.
"""

from __future__ import annotations

import json
import subprocess

from aerospace_workspaces.workspaces import (
    Record,
    aerospace_bin,
    aerospace_timeout,
    label,
    load_workspaces,
    run_aerospace,
    sanitize,
    workspaces_yaml,
)

# Friendly names longer than this are truncated (with an ellipsis) in the menu-bar title only;
# the dropdown always shows the full name.
TITLE_NAME_LIMIT = 30

# Menu-bar title shown while AeroSpace can't be queried.
UNAVAILABLE_TITLE = "⚠️ AeroSpace"


def truncate(text: str, limit: int = TITLE_NAME_LIMIT) -> str:
    """Cap text at `limit` characters, appending an ellipsis when shortened."""
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def ordered_ids(ids: list[str], declared_order: list[str]) -> list[str]:
    """List declared workspaces first (in file order), then any remaining live workspaces.

    Only declared ids that are actually live are kept up front; live ids not in the file follow in
    their original order.
    """
    declared_live = [ws for ws in declared_order if ws in ids]
    declared_set = set(declared_live)
    remaining = [ws for ws in ids if ws not in declared_set]
    return declared_live + remaining


def render(
    focused: str,
    ids: list[str],
    windows_by_ws: dict[str, list[dict[str, object]]],
    records: dict[str, Record],
    declared_order: list[str],
) -> str:
    """Build the full SwiftBar menu string from already-gathered data (pure: no I/O).

    `windows_by_ws` maps a workspace id to a list of {"window-id", "app-name",
    "window-title"} dicts.
    """
    aerospace = aerospace_bin()
    lines: list[str] = []

    # Menu-bar title: focused workspace, name truncated so it doesn't overrun the bar.
    lines.append(truncate(label(focused, records)))
    lines.append("---")

    for workspace_id in ordered_ids(ids, declared_order):
        marker = "✓ " if workspace_id == focused else ""
        # A hint becomes a hover tooltip on the workspace row.
        hint = records.get(workspace_id, {}).get("hint")
        tooltip = f' tooltip="{sanitize(hint)}"' if hint else ""
        lines.append(
            f"{marker}{label(workspace_id, records)} | "
            f'bash="{aerospace}" param0=workspace param1={workspace_id} '
            f"terminal=false refresh=true{tooltip}"
        )
        windows = windows_by_ws.get(workspace_id, [])
        if not windows:
            lines.append("-- (empty) | color=#999999")
            continue
        for window in windows:
            app = sanitize(str(window.get("app-name", "")))
            title = sanitize(str(window.get("window-title", "")))
            window_id = window.get("window-id", "")
            entry = f"{app} — {title}" if title else app
            lines.append(
                f"-- {entry} | "
                f'bash="{aerospace}" param0=focus param1=--window-id param2={window_id} '
                f"terminal=false refresh=true"
            )

    return "\n".join(lines)


def render_unavailable(reason: str) -> str:
    """Build the degraded menu shown when AeroSpace can't be queried (pure: no I/O).

    A visible warning title, the reason (greyed), and a row that re-runs the plugin on click.
    """
    return "\n".join(
        [
            UNAVAILABLE_TITLE,
            "---",
            f"{sanitize(reason)} | color=#999999",
            "Retry now | refresh=true",
        ]
    )


def _run_json(args: list[str]) -> object:
    """Run `aerospace <args>` (bounded) and parse stdout as JSON."""
    return json.loads(run_aerospace(args))


def collect() -> tuple[str, list[str], dict[str, list[dict[str, object]]]]:
    """Query AeroSpace for the focused workspace, all workspace ids, and windows-by-workspace.

    Raises subprocess.TimeoutExpired / CalledProcessError / OSError / json.JSONDecodeError on
    failure; `main()` turns those into the "unavailable" menu.
    """
    focused = run_aerospace(["list-workspaces", "--focused"]).strip()

    workspaces = _run_json(["list-workspaces", "--all", "--json"])
    ids = [str(entry["workspace"]) for entry in workspaces]  # type: ignore[index]

    # One query for every window; the explicit --format adds the "workspace" field to the JSON.
    windows = _run_json(
        [
            "list-windows",
            "--all",
            "--format",
            "%{workspace}%{window-id}%{app-name}%{window-title}",
            "--json",
        ]
    )
    windows_by_ws: dict[str, list[dict[str, object]]] = {}
    for window in windows:  # type: ignore[union-attr]
        workspace_id = str(window["workspace"])  # type: ignore[index]
        windows_by_ws.setdefault(workspace_id, []).append(window)  # type: ignore[arg-type]

    return focused, ids, windows_by_ws


def main() -> None:
    try:
        focused, ids, windows_by_ws = collect()
    except subprocess.TimeoutExpired:
        print(
            render_unavailable(
                f"AeroSpace didn't answer within {aerospace_timeout():g}s "
                "(screen locked or Universal Control active?)"
            )
        )
        return
    except subprocess.CalledProcessError as exc:
        # str(exc) only says "exit status N"; the CLI's own explanation is on stderr.
        detail = (exc.stderr or "").strip().splitlines()
        reason = detail[0] if detail else str(exc)
        print(render_unavailable(f"AeroSpace query failed: {reason}"))
        return
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(render_unavailable(f"AeroSpace query failed: {exc}"))
        return
    records, declared_order = load_workspaces(workspaces_yaml())
    print(render(focused, ids, windows_by_ws, records, declared_order))
