"""Unit tests for the pure inventory functions: parsing, joining, problems, and pane matching."""

from __future__ import annotations

import json

import pytest

from zellij_upgrade.inventory import (
    ClaudePane,
    ClaudeProcess,
    Inventory,
    Origin,
    Session,
    Window,
    applescript_string,
    build_session,
    build_windows,
    clean_title,
    find_origin,
    is_claude_pane,
    match_pane,
    parse_running_sessions,
    parse_terminal_windows,
    parse_workspaces,
    resume_flags,
    shell_quote_double,
    terminal_panes,
)

CLAUDE = "/Users/k/.local/bin/claude --chrome --resume 1111"


def pane(pane_id=0, tab="work: thing", title=None, command=CLAUDE, position=0):
    return {
        "id": pane_id,
        "tab_name": tab,
        "tab_position": position,
        "title": tab if title is None else title,
        "pane_command": command,
    }


def process(name="work: thing", session_id="1111-aaaa", args=CLAUDE, *, transcript=True):
    return ClaudeProcess(
        session_id=session_id, name=name, cwd="/repo", args=args, has_transcript=transcript
    )


# ----------------------------------------------------------------------------------------- parsing


def test_running_sessions_leaves_out_exited_ones_and_keeps_awkward_names():
    listing = (
        "justdavis (monorepo) [Created 2days 17h ago] \n"
        "relax [Created 1month ago] (EXITED - attach to resurrect)\n"
        "dotfiles [Created 6h ago] (current)\n"
    )
    assert parse_running_sessions(listing) == ["justdavis (monorepo)", "dotfiles"]


def test_running_sessions_of_no_sessions_is_empty():
    assert parse_running_sessions("No active zellij sessions found.\n") == []


def test_terminal_panes_drops_plugins_and_orders_by_tab_then_id():
    listing = json.dumps(
        [
            {"id": 0, "is_plugin": True},
            pane(pane_id=5, position=1),
            pane(pane_id=2, position=0),
            pane(pane_id=1, position=1),
        ]
    )
    assert [p["id"] for p in terminal_panes(listing)] == [2, 1, 5]


@pytest.mark.parametrize("output", ["", "Session not found", "{}"])
def test_terminal_panes_of_unusable_output_is_empty(output):
    assert terminal_panes(output) == []


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (CLAUDE, True),
        ("claude", True),
        ("/opt/homebrew/bin/nu", False),
        ("/opt/homebrew/bin/hx notes-about-claude.md", False),
        ("", False),
    ],
)
def test_a_pane_is_claude_when_its_command_is_the_claude_program(command, expected):
    assert is_claude_pane(pane(command=command)) is expected


def test_clean_title_removes_claudes_status_marks():
    assert clean_title("✳ work: thing") == "work: thing"
    assert clean_title(None) == ""


# ------------------------------------------------------------------------------------------- flags


def test_resume_flags_keep_the_sessions_own_flags():
    args = "/bin/claude --chrome --permission-mode plan --allow-dangerously-skip-permissions"
    assert resume_flags(args) == (
        "--chrome",
        "--permission-mode",
        "plan",
        "--allow-dangerously-skip-permissions",
    )


def test_resume_flags_drop_what_names_the_conversation():
    args = "/bin/claude --chrome --resume 3e22b48b --fork-session -n justdavis: organize docs"
    assert resume_flags(args) == ("--chrome",)


def test_resume_flags_drop_a_bare_resume_and_continue():
    assert resume_flags("/bin/claude --resume") == ()
    assert resume_flags("/bin/claude -c --chrome") == ("--chrome",)


# ---------------------------------------------------------------------------------------- sessions


def test_a_claude_pane_is_joined_to_the_session_with_its_title():
    session, problems = build_session("work", [pane(title="✳ work: thing")], [process()])
    assert problems == []
    assert session == Session(
        name="work",
        claude_panes=(
            ClaudePane("work: thing", "work: thing", "1111-aaaa", "/repo", ("--chrome",)),
        ),
    )
    assert session.claude_panes[0].resume_command == "claude --chrome --resume 1111-aaaa"


def test_other_panes_are_not_recorded():
    session, problems = build_session("work", [pane(command="/opt/homebrew/bin/nu")], [process()])
    assert session.claude_panes == ()
    assert problems == []


def test_a_title_matching_no_claude_session_is_a_problem_and_is_not_resumed():
    session, problems = build_session("work", [pane()], [])
    assert session.claude_panes[0].session_id is None
    assert "0 running Claude sessions are named 'work: thing'" in problems[0]


def test_a_title_matching_two_claude_sessions_is_a_problem():
    twins = [process(session_id="1"), process(session_id="2")]
    session, problems = build_session("work", [pane()], twins)
    assert session.claude_panes[0].session_id is None
    assert "2 running Claude sessions" in problems[0]


def test_a_session_that_never_took_a_turn_is_a_problem_and_is_not_resumed():
    session, problems = build_session("work", [pane()], [process(transcript=False)])
    assert session.claude_panes[0].session_id is None
    assert "no saved conversation" in problems[0]


def test_two_claude_panes_in_one_tab_are_a_problem_and_neither_is_resumed():
    panes = [pane(pane_id=1, title="a"), pane(pane_id=2, title="b")]
    processes = [process(name="a", session_id="1"), process(name="b", session_id="2")]
    session, problems = build_session("work", panes, processes)
    assert [p.session_id for p in session.claude_panes] == [None, None]
    assert "2 Claude panes share this tab" in problems[0]


# ----------------------------------------------------------------------------------------- windows

TERMINAL_LISTING = """W 39855
S local-it | local-it: terraria (zellij)
S dotfiles | dotfiles: upgrade (zellij)
W 39869
S justdavis (monorepo) | squawkbox (zellij)
W 39900
S karl@mantis: ~
"""


def test_terminal_windows_give_each_tabs_zellij_session():
    assert parse_terminal_windows(TERMINAL_LISTING) == [
        ("39855", ["local-it", "dotfiles"]),
        ("39869", ["justdavis (monorepo)"]),
        ("39900", ["karl@mantis: ~"]),
    ]


def test_workspaces_map_window_ids():
    assert parse_workspaces("39855\tI\n39869\tO\n\n") == {"39855": "I", "39869": "O"}


def test_windows_keep_their_tabs_and_workspaces_and_skip_what_is_not_a_running_session():
    windows = build_windows(
        parse_terminal_windows(TERMINAL_LISTING),
        {"39855": "I", "39869": "O", "39900": "Y"},
        ["local-it", "dotfiles", "justdavis (monorepo)"],
    )
    assert windows == (
        Window("I", ("local-it", "dotfiles")),
        Window("O", ("justdavis (monorepo)",)),
    )


def test_a_running_session_with_no_window_gets_one_of_its_own():
    windows = build_windows([("1", ["alpha"])], {}, ["alpha", "beta"])
    assert windows == (Window(None, ("alpha",)), Window(None, ("beta",)))


def test_a_session_shown_in_two_windows_is_reopened_once():
    windows = build_windows([("1", ["alpha"]), ("2", ["alpha"])], {"1": "I", "2": "O"}, ["alpha"])
    assert windows == (Window("I", ("alpha",)),)


# ------------------------------------------------------------------------------------------ origin


def test_origin_is_the_tab_of_the_claude_pane_the_command_was_started_from():
    panes = [pane(pane_id=3, tab="other"), pane(pane_id=7, tab="mine")]
    assert find_origin("work", "7", panes) == Origin("work", "mine")


@pytest.mark.parametrize(("session", "pane_id"), [(None, "7"), ("work", None), ("work", "99")])
def test_origin_is_none_outside_zellij_or_when_the_pane_is_unknown(session, pane_id):
    assert find_origin(session, pane_id, [pane(pane_id=7)]) is None


def test_origin_is_none_when_started_from_a_plain_shell():
    assert find_origin("work", "7", [pane(pane_id=7, command="/opt/homebrew/bin/nu")]) is None


# ---------------------------------------------------------------------------------------- matching

RECORDED = ClaudePane("work: thing", "work: thing", "1111", "/repo", ())
SHELL = "/opt/homebrew/bin/nu"


def test_the_pane_zellij_is_holding_a_claude_command_for_is_matched():
    panes = [pane(pane_id=4, command=SHELL), pane(pane_id=9, command="")]
    screens = {4: "> ", 9: "Waiting to run: /bin/claude --resume\n<ENTER> run"}
    assert match_pane(RECORDED, panes, screens) == 9


def test_a_pane_waiting_to_run_something_else_is_not_matched():
    panes = [pane(pane_id=9, command="")]
    assert match_pane(RECORDED, panes, {9: "Waiting to run: /opt/homebrew/bin/hx notes.md"}) is None


def test_panes_in_other_tabs_are_ignored():
    panes = [pane(pane_id=1, tab="elsewhere"), pane(pane_id=2)]
    assert match_pane(RECORDED, panes, {}) == 2


def test_two_candidates_in_the_tab_match_nothing():
    assert match_pane(RECORDED, [pane(pane_id=1), pane(pane_id=2)], {}) is None


# ----------------------------------------------------------------------------------------- quoting


def test_applescript_strings_escape_quotes_and_backslashes():
    assert applescript_string('say "hi" \\ there') == '"say \\"hi\\" \\\\ there"'


def test_shell_double_quoting_keeps_spaces_and_parens_and_escapes_the_rest():
    assert shell_quote_double("justdavis (monorepo)") == '"justdavis (monorepo)"'
    assert shell_quote_double('a"b$c`d') == '"a\\"b\\$c\\`d"'


def test_a_single_quote_cannot_be_passed_to_a_terminal_window():
    with pytest.raises(ValueError, match="single quote"):
        shell_quote_double("karl's session")


# ------------------------------------------------------------------------------------------- state


def test_an_inventory_survives_being_written_and_read_back():
    inventory = Inventory(
        taken="2026-11-25 10:39:08",
        zellij_version="zellij 0.46.0",
        sessions=(Session("work", (RECORDED,)), Session("idle", ())),
        windows=(Window("I", ("work", "idle")), Window(None, ("spare",))),
        problems=("work / x: something",),
        origin=Origin("work", "work: thing"),
    )
    assert Inventory.from_json(inventory.to_json()) == inventory
