"""Sticky windows: keep selected windows visible on every AeroSpace workspace.

AeroSpace has no show-on-all-workspaces option (https://github.com/nikitabobko/AeroSpace/issues/2),
so this emulates one. `main()` is the entry point invoked by the thin shim
(~/.config/aerospace/follow-sticky-windows.py), which ~/.aerospace.toml runs from
`exec-on-workspace-change`. On each switch it floats every window matching a `sticky-windows` rule
in workspaces.yaml and moves it onto the newly focused workspace, leaving focus where it is.

Sticky windows are always floating: a tiled window moved on every switch would be re-inserted into
each workspace's tiling tree, re-splitting the layout and losing its own size and position.

`plan_commands` is pure so it's unit-testable without a running AeroSpace. `--dry-run` prints the
`aerospace` commands that WOULD run instead of executing them.

Every `aerospace` call is bounded (see `run_aerospace`): the server doesn't answer while the screen is
locked or Universal Control has the cursor, and a hung workspace-change hook would delay the
SwiftBar refresh chained after it. Any failure just skips this switch; the next one retries.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

import yaml

from aerospace_workspaces.workspaces import run_aerospace, workspaces_yaml

# (app bundle id, optional title pattern). A rule with no pattern matches every window of the app.
Rule = tuple[str, "re.Pattern[str] | None"]


def load_sticky_rules(path: str) -> list[Rule]:
    """Parse the `sticky-windows:` list from workspaces.yaml.

    Each entry needs an `app-id`; `title-regex` (a Python regex, matched with `re.search`) is
    optional. Entries without an `app-id` or with an invalid regex are skipped (the latter with a
    warning on stderr). Returns [] if the
    file is absent or malformed, or has no `sticky-windows` list.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except FileNotFoundError:
        return []
    if not isinstance(data, dict) or not isinstance(data.get("sticky-windows"), list):
        return []

    rules: list[Rule] = []
    for entry in data["sticky-windows"]:
        if not isinstance(entry, dict) or not entry.get("app-id"):
            continue
        pattern = entry.get("title-regex")
        try:
            compiled = re.compile(str(pattern)) if pattern else None
        except re.error as err:
            # The hook runs headless, so this only shows on manual / --dry-run runs; that's where
            # you'd look when a rule never seems to apply.
            print(
                f"sticky-windows: skipping rule for {entry['app-id']}: "
                f"invalid title-regex {str(pattern)!r} ({err})",
                file=sys.stderr,
            )
            continue
        rules.append((str(entry["app-id"]), compiled))
    return rules


def _matches(window: dict[str, object], rules: list[Rule]) -> bool:
    app_id = window.get("app-bundle-id")
    title = str(window.get("window-title", ""))
    return any(
        app_id == rule_app and (pattern is None or pattern.search(title))
        for rule_app, pattern in rules
    )


def plan_commands(windows: list[object], rules: list[Rule], target: str) -> list[list[str]]:
    """The `aerospace` argument lists that make every matching window floating and on `target`.

    `windows` are `aerospace list-windows --json` records with app-bundle-id, window-id,
    window-title, workspace and window-layout fields. Windows already floating on `target` need
    nothing. Malformed records (not a dict, or no window-id) are skipped, so one bad entry can't
    keep the rest from following.
    """
    commands: list[list[str]] = []
    for window in windows:
        if not isinstance(window, dict) or window.get("window-id") in (None, ""):
            continue
        if not _matches(window, rules):
            continue
        window_id = str(window["window-id"])
        if window.get("window-layout") != "floating":
            commands.append(["layout", "--window-id", window_id, "floating"])
        if str(window.get("workspace")) != target:
            commands.append(["move-node-to-workspace", "--window-id", window_id, target])
    return commands


def _list_windows() -> list[dict[str, object]]:
    """Every window on every monitor, with the fields `plan_commands` reads."""
    windows = json.loads(
        run_aerospace(
            [
                "list-windows",
                "--monitor",
                "all",
                "--format",
                "%{window-id}%{app-bundle-id}%{window-title}%{workspace}%{window-layout}",
                "--json",
            ]
        )
    )
    return windows if isinstance(windows, list) else []


def _focused_workspace() -> str:
    return run_aerospace(["list-workspaces", "--focused"]).strip()


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    dry_run = "--dry-run" in args

    rules = load_sticky_rules(workspaces_yaml())
    if not rules:
        return
    try:
        # AeroSpace sets this for exec-on-workspace-change; fall back to asking for manual runs.
        target = os.environ.get("AEROSPACE_FOCUSED_WORKSPACE") or _focused_workspace()
        if not target:
            return
        for command in plan_commands(_list_windows(), rules, target):
            if dry_run:
                print(" ".join(["aerospace", *command]))
            else:
                run_aerospace(command)
    except (subprocess.SubprocessError, OSError, ValueError):
        # ValueError covers json.JSONDecodeError. Skip this switch rather than fail the hook.
        return
