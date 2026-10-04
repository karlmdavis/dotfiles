"""SketchyBar rendering for the AeroSpace workspace strip.

`main()` is the entry point invoked by the thin plugin shim
(~/.config/sketchybar/plugins/aerospace-workspaces.py), which SketchyBar runs on every workspace
change and on a slow fallback tick. It queries AeroSpace and the bar, then sends SketchyBar one
batched command that makes the left side of the bar a strip of the occupied workspaces:

  - one `space.<id>` item per workspace, in AeroSpace's own order, shown only while the workspace
    has a window or has focus;
  - the focused one labelled "<emoji> <id>: <name>" in the accent colour;
  - the others labelled "<emoji> <id>" in the dim colour, or just "<id>" once the strip grows past
    `ICON_ENTRY_LIMIT` entries, so a busy strip still fits beside the display notch;
  - each switching to its workspace on click.

SketchyBar's own `space` component is no use here: it tracks macOS Spaces, and AeroSpace keeps
all of its workspaces inside one Space.

The items are created here rather than in sketchybarrc, from whatever the bar is missing, so the
bar does not depend on AeroSpace answering at the moment SketchyBar starts. Two runs that overlap
on a fresh bar can both find the items missing and both add them; SketchyBar reports the
duplicates in its log and applies the rest of each command, so the strip still ends up right.

`render()` is pure (all inputs injected) so it's unit-testable without a live AeroSpace or bar.
`--dry-run` prints the SketchyBar command instead of running it, and $SKETCHYBAR_BIN overrides
the binary; both double as test seams, alongside the ones in `workspaces`.

Every `aerospace` call is bounded (see `run_aerospace`): the server stops answering while the
screen is locked or Universal Control has the cursor. On any failure the bar is left as it is and
the next event or tick simply tries again.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys

from aerospace_workspaces.workspaces import (
    Record,
    aerospace_bin,
    aerospace_timeout,
    load_workspaces,
    run_aerospace,
    workspaces_yaml,
)

# Workspace items are named "space.<id>".
ITEM_PREFIX = "space."

# With more entries than this in the strip, the unfocused ones drop their emoji and show the bare
# id. The left side of the bar ends at the display notch, and an entry with an emoji is roughly
# twice as wide as one without.
ICON_ENTRY_LIMIT = 8


def sketchybar_bin() -> str:
    """Path to the `sketchybar` binary. $SKETCHYBAR_BIN overrides (default: Homebrew prefix)."""
    return os.environ.get("SKETCHYBAR_BIN", "/opt/homebrew/bin/sketchybar")


def shown_ids(focused: str, ids: list[str], occupied: set[str]) -> list[str]:
    """The workspaces the strip shows, in `ids` order: those with a window, plus the focused one."""
    return [ws for ws in ids if ws == focused or ws in occupied]


def entry_text(workspace_id: str, records: dict[str, Record], *, named: bool, icon: bool) -> str:
    """Label for one strip entry: "<icon> <id>: <name>" when `named`, else "<icon> <id>".

    The icon is included only when `icon` is set and the workspace has one, and the name only
    when the workspace has one, so an unmapped workspace degrades to its bare id either way.
    """
    record = records.get(workspace_id, {})
    name = record.get("name") if named else None
    text = f"{workspace_id}: {name}" if name else workspace_id
    emoji = record.get("icon") if icon else None
    return f"{emoji} {text}" if emoji else text


def render(
    existing: set[str],
    focused: str,
    ids: list[str],
    occupied: set[str],
    records: dict[str, Record],
    *,
    dim: str | None = None,
    accent: str | None = None,
) -> list[str]:
    """Build the SketchyBar arguments that bring the strip up to date (pure: no I/O).

    `existing` is the set of item names already in the bar; any `space.<id>` item missing from it
    is added first. `ids` is every live workspace in AeroSpace's order, which is the order new
    items are added in, so a fresh bar gets them in workspace order. A focused workspace missing
    from `ids` is treated as one more workspace at the end. `dim` and `accent` are SketchyBar
    colours (0xAARRGGBB) for the unfocused and focused labels; without them the colour is left
    to the bar's defaults.
    """
    all_ids = ids if not focused or focused in ids else [*ids, focused]
    shown = shown_ids(focused, all_ids, occupied)
    icons = len(shown) <= ICON_ENTRY_LIMIT

    args: list[str] = []
    for workspace_id in all_ids:
        item = ITEM_PREFIX + workspace_id
        if item not in existing:
            click = f"{shlex.quote(aerospace_bin())} workspace {shlex.quote(workspace_id)}"
            args += ["--add", "item", item, "left"]
            args += ["--set", item, "icon.drawing=off", f"click_script={click}"]

        if workspace_id not in shown:
            args += ["--set", item, "drawing=off"]
            continue

        is_focused = workspace_id == focused
        text = entry_text(workspace_id, records, named=is_focused, icon=is_focused or icons)
        args += ["--set", item, "drawing=on", f"label={text}"]
        colour = accent if is_focused else dim
        if colour:
            args.append(f"label.color={colour}")
    return args


def collect() -> tuple[str, list[str], set[str]]:
    """Query AeroSpace for the focused workspace, every workspace id, and the occupied ids.

    The focused id is "" when no workspace reports focus. Raises subprocess.TimeoutExpired /
    CalledProcessError / OSError / json.JSONDecodeError on failure, and KeyError / TypeError when
    the JSON parses but has an unexpected shape; `main()` turns all of those into a no-op.
    """
    workspaces = json.loads(
        run_aerospace(
            ["list-workspaces", "--all", "--format", "%{workspace}%{workspace-is-focused}", "--json"]
        )
    )
    ids = [str(entry["workspace"]) for entry in workspaces]
    focused = next(
        (str(entry["workspace"]) for entry in workspaces if entry["workspace-is-focused"]), ""
    )
    occupied = set(run_aerospace(["list-workspaces", "--monitor", "all", "--empty", "no"]).split())
    return focused, ids, occupied


def existing_items() -> set[str]:
    """Names of the items currently in the bar, from `sketchybar --query bar` (bounded).

    Raises the same exception types as `collect()` when the bar can't be queried.
    """
    result = subprocess.run(
        [sketchybar_bin(), "--query", "bar"],
        capture_output=True,
        text=True,
        check=True,
        timeout=aerospace_timeout(),
    )
    return {str(item) for item in json.loads(result.stdout)["items"]}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Update SketchyBar's AeroSpace workspace strip.")
    parser.add_argument("--dim", help="label colour for unfocused workspaces (0xAARRGGBB)")
    parser.add_argument("--accent", help="label colour for the focused workspace (0xAARRGGBB)")
    parser.add_argument(
        "--dry-run", action="store_true", help="print the sketchybar command instead of running it"
    )
    options = parser.parse_args(argv)

    try:
        focused, ids, occupied = collect()
        records, _ = load_workspaces(workspaces_yaml())
        args = render(
            existing_items(),
            focused,
            ids,
            occupied,
            records,
            dim=options.dim,
            accent=options.accent,
        )
        command = [sketchybar_bin(), *args]
        if options.dry_run:
            print(shlex.join(command))
        elif args:
            subprocess.run(command, check=True, timeout=aerospace_timeout())
    except (
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
    ) as exc:
        print(f"aerospace-workspaces: leaving the bar as it is: {exc}", file=sys.stderr)
