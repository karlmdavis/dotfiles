"""Shared AeroSpace workspace data: the name map, labeling, and sanitization.

This module is consumed by both `aerospace_workspaces.swiftbar` (the SwiftBar menu-bar plugin) and
`aerospace_workspaces.hud` (the workspace-switch HUD), which is why it lives in a shared package
rather than being duplicated in each entry-point script.

Two environment seams double as runtime overrides and test seams:
  - $AEROSPACE_BIN — the `aerospace` binary path (SwiftBar's launchd PATH omits Homebrew).
  - $AEROSPACE_WORKSPACES_YAML — the names file location.
  - $AEROSPACE_TIMEOUT — seconds to wait for an `aerospace` CLI call (default 3).
All are read at call time (not import time) so tests can set them per-case.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import yaml

# A per-workspace record: any of "icon" (emoji), "name", "hint" may be present.
Record = dict[str, str]


def aerospace_bin() -> str:
    """Path to the `aerospace` binary. $AEROSPACE_BIN overrides (default: Homebrew prefix)."""
    return os.environ.get("AEROSPACE_BIN", "/opt/homebrew/bin/aerospace")


def workspaces_yaml() -> str:
    """Path to workspaces.yaml. $AEROSPACE_WORKSPACES_YAML overrides (default: ~/.config/...)."""
    return os.environ.get(
        "AEROSPACE_WORKSPACES_YAML",
        str(Path.home() / ".config" / "aerospace" / "workspaces.yaml"),
    )


def load_workspaces(path: str) -> tuple[dict[str, Record], list[str]]:
    """Parse the `workspaces:` map from workspaces.yaml.

    Returns (records, declared_order): `records` maps a workspace id to its {icon?, name?, hint?}
    record, and `declared_order` is the ids in the order they appear in the file (PyYAML preserves
    map insertion order), so the menu can list configured workspaces first.

    Tolerates the older flat shape (`id: "Name"`) by coercing a bare string to {"name": ...}.
    Returns ({}, []) if the file is absent or malformed.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except FileNotFoundError:
        return {}, []
    if not isinstance(data, dict):
        return {}, []
    workspaces = data.get("workspaces")
    if not isinstance(workspaces, dict):
        return {}, []

    records: dict[str, Record] = {}
    order: list[str] = []
    for key, value in workspaces.items():
        # YAML reads a bare `9` key as int, but AeroSpace ids are strings.
        workspace_id = str(key)
        if isinstance(value, dict):
            # Keep only the fields we know about, coercing values to str (drop empty/None).
            record = {
                field: str(value[field])
                for field in ("icon", "name", "hint")
                if value.get(field) not in (None, "")
            }
        else:
            # Old flat shape: the value IS the name.
            record = {"name": str(value)}
        records[workspace_id] = record
        order.append(workspace_id)
    return records, order


def sanitize(text: str) -> str:
    """Neutralize characters that would break SwiftBar's "title | params" line grammar.

    Free text (window titles, hints) can contain `|` (which SwiftBar reads as the param
    separator), newlines (which split the menu line), or `"` (which would close a quoted param
    value early, e.g. tooltip="..."). Swap each for a harmless look-alike / space.
    """
    return (
        text.replace("|", "¦")
        .replace('"', "”")
        .replace("\n", " ")
        .replace("\r", " ")
        .strip()
    )


def label(workspace_id: str, records: dict[str, Record]) -> str:
    """Compose a workspace label: "<icon> <id>: <name>", degrading as fields are missing.

    With a name: "<id>: <name>" (icon prepended when present). Without a name: the bare id (icon
    prepended when present), avoiding "id: id" noise for unmapped workspaces.
    """
    record = records.get(workspace_id, {})
    name = record.get("name")
    text = f"{workspace_id}: {name}" if name else workspace_id
    icon = record.get("icon")
    return f"{sanitize(icon)} {text}" if icon else text


# Seconds to wait for the `aerospace` CLI before giving up. Bounded because the AeroSpace server
# stops answering *focus* queries (list-workspaces --focused etc.) whenever the frontmost "app" is
# one it can't reach over accessibility — loginwindow while the screen is locked, or
# com.apple.universalcontrol while the cursor is on another device. Its socket accepts the
# connection but never replies, so an unbounded call blocks forever and wedges the caller.
DEFAULT_TIMEOUT = 3.0


def aerospace_timeout() -> float:
    """Seconds to wait for an `aerospace` call. $AEROSPACE_TIMEOUT overrides (default 3)."""
    raw = os.environ.get("AEROSPACE_TIMEOUT")
    if raw is None:
        return DEFAULT_TIMEOUT
    try:
        return float(raw)
    except ValueError:
        return DEFAULT_TIMEOUT


def run_aerospace(args: list[str]) -> str:
    """Run `aerospace <args>` and return its stdout, waiting at most `aerospace_timeout()` seconds.

    Raises subprocess.TimeoutExpired when the server doesn't answer in time (the child is killed
    first, so no `aerospace` process is left behind), subprocess.CalledProcessError on a non-zero
    exit, and OSError if the binary can't be launched. Callers decide how to degrade.
    """
    result = subprocess.run(
        [aerospace_bin(), *args],
        capture_output=True,
        text=True,
        check=True,
        timeout=aerospace_timeout(),
    )
    return result.stdout
