"""Unit tests for the SwiftBar menu rendering (pure render(), no live AeroSpace)."""

from __future__ import annotations

import time

from aerospace_workspaces import swiftbar
from aerospace_workspaces.swiftbar import (
    TITLE_ACCENT,
    TITLE_DIM,
    TITLE_NAME_LIMIT,
    UNAVAILABLE_TITLE,
    menu_bar_title,
    ordered_ids,
    render,
    render_unavailable,
    truncate,
)

# Records used across the render tests (mirrors the former bats fixture).
RECORDS = {
    "C": {"icon": "💬", "name": "Comms"},
    "I": {"icon": "🖥️", "name": "Local IT", "hint": 'the "i" is for "IT"'},
    "9": {"name": "Hiring"},
    "V": {"icon": "📹", "name": 'Meetings (the "v" is for "video calls")'},
}
DECLARED = ["C", "I", "9", "V"]

# Windows keyed by workspace; C has a pipe in a title (sanitization), 9 has none (empty submenu).
WINDOWS = {
    "C": [
        {"window-id": 242, "app-name": "Firefox", "window-title": "Box | Login"},
        {"window-id": 55672, "app-name": "Microsoft Outlook", "window-title": "Inbox"},
    ],
    "I": [{"window-id": 65529, "app-name": "Dialog", "window-title": "Dialog"}],
    "Z": [{"window-id": 264, "app-name": "Slack", "window-title": "general"}],
}


def render_default(focused="C", ids=None):
    # Live ids in a DIFFERENT order than the file, with Z undeclared, to test ordering.
    if ids is None:
        ids = ["I", "9", "C", "Z"]
    return render(focused, ids, WINDOWS, RECORDS, DECLARED)


# --- truncate / ordered_ids -----------------------------------------------------------------


def test_truncate_under_limit_unchanged():
    assert truncate("short", 30) == "short"


def test_truncate_appends_ellipsis_within_cap():
    out = truncate("x" * 50, 30)
    assert out.endswith("…") and len(out) <= 30


def test_ordered_ids_declared_first_then_remaining():
    # File order C,I,9,V; live I,9,C,Z; V not live -> declared-live C,I,9 then undeclared Z.
    assert ordered_ids(["I", "9", "C", "Z"], DECLARED) == ["C", "I", "9", "Z"]


# --- title ----------------------------------------------------------------------------------


def strip(focused="C", ids=None, windows=None):
    """The title line as (plain text with the colour codes removed, SwiftBar params)."""
    if ids is None:
        ids = ["I", "9", "C", "Z"]
    line = menu_bar_title(focused, ids, WINDOWS if windows is None else windows, RECORDS)
    text, _, params = line.partition(" | ")
    return text.replace(TITLE_DIM, "").replace(TITLE_ACCENT, ""), params


def test_title_is_first_rendered_line():
    expected = menu_bar_title("C", ["I", "9", "C", "Z"], WINDOWS, RECORDS)
    assert render_default(focused="C").splitlines()[0] == expected


def test_title_lists_occupied_workspaces_in_aerospace_order():
    # I, C and Z have windows; 9 is empty and not focused, so it is left out. Order follows the
    # live `ids`, not the declared order the dropdown uses.
    assert strip(focused="C")[0] == "I 💬 C: Comms Z"


def test_title_shows_focused_workspace_even_when_empty():
    assert strip(focused="9")[0] == "I 9: Hiring C Z"


def test_title_shows_focused_workspace_missing_from_ids():
    assert strip(focused="Q", ids=["I", "C"])[0] == "I C Q"


def test_title_with_only_the_focused_workspace():
    assert strip(focused="C", ids=["C", "9"], windows={})[0] == "💬 C: Comms"


def test_title_enables_ansi_rendering():
    assert strip()[1] == "ansi=true"


def test_title_colours_every_entry():
    # SwiftBar leaves uncoloured text in an ANSI title black, so no entry may go without a code:
    # the focused entry carries the accent and each of the others the dim colour.
    text = menu_bar_title("C", ["I", "9", "C", "Z"], WINDOWS, RECORDS).partition(" | ")[0]
    assert text == f"{TITLE_DIM}I {TITLE_ACCENT}💬 C: Comms {TITLE_DIM}Z"


def test_long_focused_name_truncated_with_ellipsis():
    focused = strip(focused="V", ids=["V"], windows={})[0]
    assert focused.startswith("📹 V: Meetings") and focused.endswith("…")
    assert len(focused) <= TITLE_NAME_LIMIT


def test_pipe_in_workspace_name_neutralized():
    # A raw `|` in the title would start SwiftBar's params early and swallow `ansi=true`.
    line = menu_bar_title("P", ["P"], {}, {"P": {"name": "a | b"}})
    assert line.count("|") == 1 and "a ¦ b" in line


def test_separator_follows_title():
    assert render_default().splitlines()[1] == "---"


# --- workspace rows -------------------------------------------------------------------------


def test_every_live_workspace_present():
    out = render_default()
    assert "C: Comms" in out and "I: Local IT" in out and "9: Hiring" in out


def test_focused_row_marked():
    assert "✓ 💬 C: Comms" in render_default(focused="C")


def test_nonfocused_row_unmarked():
    out = render_default(focused="C")
    assert "\n🖥️ I: Local IT" in out and "✓ 🖥️ I" not in out


def test_unmapped_workspace_bare_id():
    out = render_default()
    assert "\nZ |" in out and "Z: Z" not in out


def test_no_icon_row_has_no_leading_emoji():
    assert "\n9: Hiring |" in render_default()


def test_rows_switch_workspace_on_click():
    out = render_default()
    assert "param0=workspace param1=C" in out and "param0=workspace param1=Z" in out


def test_ordering_in_rendered_rows():
    out = render_default()
    ids = [line.split("param1=")[1].split()[0] for line in out.splitlines() if "param0=workspace" in line]
    assert ids == ["C", "I", "9", "Z"]


# --- tooltips -------------------------------------------------------------------------------


def test_hinted_row_has_tooltip():
    out = render_default()
    # The I row carries a tooltip; the embedded quotes are neutralized (no raw `"` inside).
    i_row = next(line for line in out.splitlines() if "param1=I " in line)
    assert "tooltip=" in i_row and '"i"' not in i_row.split("tooltip=")[1][1:]


def test_unhinted_row_has_no_tooltip():
    c_row = next(line for line in render_default().splitlines() if "param1=C " in line)
    assert "tooltip=" not in c_row


# --- window submenus ------------------------------------------------------------------------


def test_windows_nested_as_submenu():
    out = render_default()
    assert "-- Firefox — Box" in out and "-- Microsoft Outlook — Inbox" in out


def test_window_click_focuses_window_id():
    out = render_default()
    assert "param0=focus param1=--window-id param2=55672" in out
    assert "param0=focus param1=--window-id param2=264" in out


def test_empty_workspace_placeholder():
    assert "-- (empty)" in render_default()


def test_pipe_in_window_title_neutralized():
    out = render_default()
    assert "Box ¦ Login" in out and "Box | Login" not in out


# --- failure handling: the plugin must never hang or crash SwiftBar ----------------------------


def test_render_unavailable_shape():
    out = render_unavailable('server | "down"').splitlines()
    assert out[0] == UNAVAILABLE_TITLE
    assert out[1] == "---"
    assert "|" not in out[2].split(" | ")[0] and "color=" in out[2]  # reason sanitized, greyed
    assert "refresh=true" in out[3]


def test_main_prints_fallback_when_aerospace_hangs(hanging_aerospace, no_sleep_leftover, capsys):
    started = time.monotonic()
    swiftbar.main()
    assert time.monotonic() - started < 2.0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == UNAVAILABLE_TITLE
    assert "didn't answer within 0.2s" in out[2]


def test_main_prints_fallback_when_aerospace_fails(failing_aerospace, capsys):
    swiftbar.main()
    out = capsys.readouterr().out.splitlines()
    assert out[0] == UNAVAILABLE_TITLE
    assert "query failed" in out[2]
    # The CLI's stderr ("boom") is the useful part; the exit status alone explains nothing.
    assert "boom" in out[2]


def test_main_prints_fallback_on_bad_json(echoing_aerospace, capsys):
    # The echoing fake answers "--focused" fine but returns non-JSON for the --json queries.
    swiftbar.main()
    out = capsys.readouterr().out.splitlines()
    assert out[0] == UNAVAILABLE_TITLE


def test_main_prints_fallback_when_binary_missing(monkeypatch, capsys):
    monkeypatch.setenv("AEROSPACE_BIN", "/nonexistent/aerospace")
    swiftbar.main()
    assert capsys.readouterr().out.splitlines()[0] == UNAVAILABLE_TITLE


def test_main_prints_fallback_on_wrong_json_shape(null_json_aerospace, capsys):
    # `null` parses fine but isn't a list of dicts; subscripting it raises TypeError, which must
    # degrade to the fallback menu rather than escape main().
    swiftbar.main()
    out = capsys.readouterr().out.splitlines()
    assert out[0] == UNAVAILABLE_TITLE
    assert "query failed" in out[2]
