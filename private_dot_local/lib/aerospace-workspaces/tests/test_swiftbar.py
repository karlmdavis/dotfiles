"""Unit tests for the SwiftBar menu rendering (pure render(), no live AeroSpace)."""

from __future__ import annotations

from aerospace_workspaces.swiftbar import ordered_ids, render, truncate

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


def test_title_is_focused_icon_label():
    assert render_default(focused="C").splitlines()[0] == "💬 C: Comms"


def test_title_includes_focused_emoji():
    assert render_default(focused="I").splitlines()[0].startswith("🖥️")


def test_long_focused_name_truncated_with_ellipsis():
    out = render("V", ["V"], {}, RECORDS, DECLARED).splitlines()[0]
    assert out.startswith("📹 V: Meetings") and out.endswith("…") and len(out) <= 30


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
