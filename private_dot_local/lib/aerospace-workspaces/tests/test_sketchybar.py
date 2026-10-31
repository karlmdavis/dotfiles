"""Unit tests for the SketchyBar workspace strip (pure render(), plus main() via fake binaries)."""

from __future__ import annotations

import shlex
import stat
import time

import pytest

from aerospace_workspaces import sketchybar
from aerospace_workspaces.sketchybar import ICON_ENTRY_LIMIT, entry_text, render, shown_ids

RECORDS = {
    "C": {"icon": "💬", "name": "Comms"},
    "I": {"icon": "🖥️", "name": "Local IT", "hint": 'the "i" is for "IT"'},
    "9": {"name": "Hiring"},
}
IDS = ["1", "9", "C", "I", "Z"]
OCCUPIED = {"1", "C", "I"}
DIM = "0xff565f89"
ACCENT = "0xff7aa2f7"


def sets(args: list[str]) -> dict[str, list[str]]:
    """Group rendered arguments as {item: [every property set on it]}."""
    out: dict[str, list[str]] = {}
    index = 0
    while index < len(args):
        if args[index] == "--add":
            index += 4  # --add item <name> <position>
        elif args[index] == "--set":
            item = args[index + 1]
            index += 2
            while index < len(args) and not args[index].startswith("--"):
                out.setdefault(item, []).append(args[index])
                index += 1
        else:
            raise AssertionError(f"unexpected argument {args[index]!r}")
    return out


def added(args: list[str]) -> list[str]:
    """Names of the items the rendered arguments add, in order."""
    return [args[i + 2] for i, arg in enumerate(args) if arg == "--add"]


def render_default(existing=frozenset(), focused="C", **colours):
    return render(set(existing), focused, IDS, OCCUPIED, RECORDS, **colours)


# --- shown_ids / entry_text -----------------------------------------------------------------


def test_shown_ids_are_occupied_plus_focused_in_aerospace_order():
    assert shown_ids("9", IDS, OCCUPIED) == ["1", "9", "C", "I"]


def test_entry_text_named_with_icon():
    assert entry_text("C", RECORDS, named=True, icon=True) == "💬 C: Comms"


def test_entry_text_unnamed_with_icon():
    assert entry_text("C", RECORDS, named=False, icon=True) == "💬 C"


def test_entry_text_without_icon():
    assert entry_text("C", RECORDS, named=False, icon=False) == "C"


def test_entry_text_unmapped_workspace_is_bare_id():
    assert entry_text("Z", RECORDS, named=True, icon=True) == "Z"


# --- adding items ---------------------------------------------------------------------------


def test_fresh_bar_adds_an_item_per_workspace_in_aerospace_order():
    assert added(render_default()) == ["space.1", "space.9", "space.C", "space.I", "space.Z"]


def test_items_are_added_on_the_left():
    args = render_default()
    index = args.index("space.C") - 2
    assert args[index : index + 4] == ["--add", "item", "space.C", "left"]


def test_existing_items_are_not_added_again():
    args = render_default(existing={"space.1", "space.C", "clock"})
    assert added(args) == ["space.9", "space.I", "space.Z"]


def test_new_item_switches_workspace_on_click(monkeypatch):
    monkeypatch.setenv("AEROSPACE_BIN", "/opt/homebrew/bin/aerospace")
    assert "click_script=/opt/homebrew/bin/aerospace workspace C" in sets(render_default())["space.C"]


def test_existing_item_keeps_its_click_script():
    props = sets(render_default(existing={"space.C"}))["space.C"]
    assert not any(prop.startswith("click_script=") for prop in props)


def test_focused_workspace_missing_from_ids_still_gets_an_item():
    args = render(set(), "Q", IDS, OCCUPIED, RECORDS)
    assert added(args)[-1] == "space.Q" and "label=Q" in sets(args)["space.Q"]


# --- shown and hidden entries ---------------------------------------------------------------


def test_occupied_and_focused_workspaces_are_drawn():
    props = sets(render_default(focused="9"))
    assert all("drawing=on" in props[f"space.{ws}"] for ws in ("1", "9", "C", "I"))


def test_empty_unfocused_workspace_is_hidden():
    props = sets(render_default(focused="C"))
    assert props["space.9"][-1] == "drawing=off" and props["space.Z"][-1] == "drawing=off"


def test_focused_entry_is_named():
    assert "label=💬 C: Comms" in sets(render_default(focused="C"))["space.C"]


def test_unfocused_entry_is_icon_and_id():
    props = sets(render_default(focused="C"))
    assert "label=🖥️ I" in props["space.I"] and "label=1" in props["space.1"]


def test_no_focused_workspace_shows_only_the_occupied_ones():
    props = sets(render(set(), "", IDS, OCCUPIED, RECORDS))
    assert "label=💬 C" in props["space.C"] and props["space.9"][-1] == "drawing=off"


# --- colours --------------------------------------------------------------------------------


def test_focused_entry_takes_the_accent_and_the_rest_the_dim_colour():
    props = sets(render_default(focused="C", dim=DIM, accent=ACCENT))
    assert f"label.color={ACCENT}" in props["space.C"]
    assert f"label.color={DIM}" in props["space.I"]


def test_colours_are_left_alone_when_not_given():
    assert not any("label.color" in arg for arg in render_default())


# --- compaction -----------------------------------------------------------------------------


def busy_strip(count: int) -> tuple[list[str], dict[str, dict[str, str]]]:
    ids = [f"W{n}" for n in range(count)]
    return ids, {ws: {"icon": "📦", "name": f"project {ws}"} for ws in ids}


def test_unfocused_entries_keep_icons_up_to_the_limit():
    ids, records = busy_strip(ICON_ENTRY_LIMIT)
    props = sets(render(set(), ids[0], ids, set(ids), records))
    assert "label=📦 W1" in props["space.W1"]


def test_unfocused_entries_drop_icons_past_the_limit():
    ids, records = busy_strip(ICON_ENTRY_LIMIT + 1)
    props = sets(render(set(), ids[0], ids, set(ids), records))
    assert "label=W1" in props["space.W1"]
    # The focused entry keeps its icon and name however busy the strip is.
    assert "label=📦 W0: project W0" in props["space.W0"]


# --- main(): driven through fake `aerospace` and `sketchybar` binaries -------------------------


def write_script(path, body: str) -> str:
    path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return str(path)


@pytest.fixture()
def fake_aerospace(tmp_path, monkeypatch):
    """A fake `aerospace` answering the two queries collect() makes: C focused, C and I occupied."""
    body = """case "$*" in
  *--json*) echo '[{"workspace":"9","workspace-is-focused":false},
                   {"workspace":"C","workspace-is-focused":true},
                   {"workspace":"I","workspace-is-focused":false}]' ;;
  *) printf 'C\\nI\\n' ;;
esac
"""
    monkeypatch.setenv("AEROSPACE_BIN", write_script(tmp_path / "aerospace", body))
    monkeypatch.setenv("AEROSPACE_WORKSPACES_YAML", str(tmp_path / "absent.yaml"))
    monkeypatch.delenv("AEROSPACE_TIMEOUT", raising=False)


@pytest.fixture()
def fake_sketchybar(tmp_path, monkeypatch):
    """A fake `sketchybar` that reports one existing item and logs every other invocation."""
    log = tmp_path / "sketchybar.log"
    body = f"""if [ "$1" = "--query" ]; then
  echo '{{"items": ["space.C", "clock"]}}'
else
  for arg in "$@"; do printf '%s\\n' "$arg"; done >> "{log}"
fi
"""
    monkeypatch.setenv("SKETCHYBAR_BIN", write_script(tmp_path / "sketchybar", body))
    return log


def test_main_dry_run_prints_the_command_and_runs_nothing(fake_aerospace, fake_sketchybar, capsys):
    sketchybar.main(["--dry-run", "--accent", ACCENT])
    command = shlex.split(capsys.readouterr().out)
    assert command[0].endswith("/sketchybar")
    props = sets(command[1:])
    assert props["space.C"] == ["drawing=on", "label=C", f"label.color={ACCENT}"]
    assert not fake_sketchybar.exists()


def test_main_sends_one_batched_command(fake_aerospace, fake_sketchybar):
    sketchybar.main(["--dim", DIM])
    args = fake_sketchybar.read_text(encoding="utf-8").splitlines()
    # space.C already exists in the fake bar, so only the other two are added.
    assert added(args) == ["space.9", "space.I"]
    props = sets(args)
    assert props["space.9"][-1] == "drawing=off"
    assert props["space.I"][-3:] == ["drawing=on", "label=I", f"label.color={DIM}"]


def test_main_leaves_the_bar_alone_when_aerospace_hangs(
    hanging_aerospace, no_sleep_leftover, fake_sketchybar, capsys
):
    started = time.monotonic()
    sketchybar.main([])
    assert time.monotonic() - started < 2.0
    assert not fake_sketchybar.exists()
    assert "leaving the bar as it is" in capsys.readouterr().err


def test_main_leaves_the_bar_alone_when_aerospace_fails(failing_aerospace, fake_sketchybar, capsys):
    sketchybar.main([])
    assert not fake_sketchybar.exists()
    assert "leaving the bar as it is" in capsys.readouterr().err


def test_main_survives_a_missing_sketchybar(fake_aerospace, monkeypatch, capsys):
    monkeypatch.setenv("SKETCHYBAR_BIN", "/nonexistent/sketchybar")
    sketchybar.main([])
    assert "leaving the bar as it is" in capsys.readouterr().err
