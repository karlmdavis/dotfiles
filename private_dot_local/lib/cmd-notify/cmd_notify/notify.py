"""cmd-notify core: gating, formatting, and notifier dispatch.

The pure functions (`should_notify`, `command_base`, `format_duration`, `display_command`,
`build_body`, `render_dispatch`) carry all the logic and are unit-tested directly. `dispatch` and
`main` are the thin I/O layer: they read env seams, resolve the optional icon, and either print the
would-be invocation (`--dry-run`) or shell out to the platform notifier.

Mirrors the original bash helper's behavior exactly, including the dry-run output format the tests
assert on.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

from cmd_notify import icons

# TUI/REPL commands whose foreground sessions don't want a completion notification.
BLOCKLIST = frozenset(
    {
        "hx", "vim", "nvim", "nano", "emacs", "less", "more", "man",
        "htop", "top", "btop", "bash", "zsh", "fish", "nu", "ssh", "claude",
    }
)

DEFAULT_THRESHOLD_SECONDS = 60
TITLE_LIMIT = 40


def command_base(cmd: str) -> str:
    """The command's leading whitespace-delimited token, path-stripped.

    Mirrors bash `read -r first_token _ <<<"$CMD"` + `${first_token##*/}`: split on any whitespace
    (so "vim\\nfoo" → "vim"), then drop everything up to the last slash.
    """
    tokens = cmd.split()
    if not tokens:
        return ""
    return tokens[0].rsplit("/", 1)[-1]


def should_notify(
    cmd: str,
    duration: str,
    *,
    disabled: bool,
    threshold: int,
) -> bool:
    """Whether a notification should fire. False → caller exits 0 silently.

    Gates (in order): kill-switch, numeric duration ≥ threshold, non-empty command, and a
    command base that isn't blank or in the TUI/REPL blocklist.
    """
    if disabled:
        return False
    # Duration must be a non-negative integer string (bash: `*[!0-9]*` → bail).
    if not duration.isdigit():
        return False
    if int(duration) < threshold:
        return False
    if not cmd:
        return False
    base = command_base(cmd)
    if not base or base in BLOCKLIST:
        return False
    return True


def format_duration(seconds: int) -> str:
    """Human-readable duration: `Ns` (<1m), `Nm Ns` (<1h), or `Nh Nm`."""
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    return f"{seconds // 3600}h {(seconds % 3600) // 60}m"


def display_command(cmd: str, limit: int = TITLE_LIMIT) -> str:
    """Collapse control chars to spaces, then truncate to `limit-1` + ellipsis when too long."""
    collapsed = "".join(" " if ord(ch) < 0x20 else ch for ch in cmd)
    if len(collapsed) > limit:
        return collapsed[: limit - 1] + "…"
    return collapsed


def build_body(exit_code: str, duration: int, cwd: str) -> str:
    """"<status> in <dur> · <cwd_base>"; status is succeeded / failed (exit N)."""
    status = "succeeded" if exit_code == "0" else f"failed (exit {exit_code})"
    cwd_base = cwd.rstrip("/").rsplit("/", 1)[-1] or "/"
    return f"{status} in {format_duration(duration)} · {cwd_base}"


def render_dispatch(
    platform: str,
    title: str,
    body: str,
    group: str,
    icon: str | None,
) -> str:
    """The exact notifier invocation, as a single line (also the --dry-run output).

    Darwin uses terminal-notifier (title/message/group + optional contentImage); other platforms
    use notify-send with a synchronous-grouping hint + optional icon, ending with title and body.
    """
    if platform == "Darwin":
        parts = ["terminal-notifier", "-title", title, "-message", body, "-group", group]
        if icon:
            parts += ["-contentImage", icon]
        return " ".join(parts)
    parts = ["notify-send", "-h", f"string:x-canonical-private-synchronous:cmd-notify-{group_suffix(group)}"]
    if icon:
        parts += ["--icon", icon]
    parts += [title, body]
    return " ".join(parts)


def group_suffix(group: str) -> str:
    """The command-base part of a "cmd-notify:<base>" group string (for the Linux sync hint)."""
    return group.split(":", 1)[1] if ":" in group else group


def dispatch(
    platform: str,
    title: str,
    body: str,
    group: str,
    icon: str | None,
    *,
    dry_run: bool,
) -> None:
    """Print the invocation (dry-run) or shell out to the platform notifier (best-effort)."""
    if dry_run:
        print(render_dispatch(platform, title, body, group, icon))
        return

    if platform == "Darwin":
        if not shutil.which("terminal-notifier"):
            return
        args = ["terminal-notifier", "-title", title, "-message", body, "-group", group]
        if icon:
            args += ["-contentImage", icon]
    else:
        if not shutil.which("notify-send"):
            return
        args = ["notify-send", "-h", f"string:x-canonical-private-synchronous:cmd-notify-{group_suffix(group)}"]
        if icon:
            args += ["--icon", icon]
        args += [title, body]

    try:
        subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except OSError:
        pass


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)

    if os.environ.get("CMD_NOTIFY_DISABLE") == "1":
        return

    dry_run = False
    if args and args[0] == "--dry-run":
        dry_run = True
        args = args[1:]

    cmd = args[0] if len(args) > 0 else ""
    duration_raw = args[1] if len(args) > 1 else "0"
    exit_code = args[2] if len(args) > 2 else "0"
    cwd = args[3] if len(args) > 3 else "?"

    threshold = _int_env("CMD_NOTIFY_THRESHOLD", DEFAULT_THRESHOLD_SECONDS)

    if not should_notify(cmd, duration_raw, disabled=False, threshold=threshold):
        return

    duration = int(duration_raw)
    base = command_base(cmd)
    title = display_command(cmd)
    body = build_body(exit_code, duration, cwd)
    group = f"cmd-notify:{base}"

    cache_dir = os.path.join(
        os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")),
        "cmd-notify",
        "icons",
    )
    icons_file = os.environ.get(
        "CMD_NOTIFY_ICONS", os.path.expanduser("~/.local/share/cmd-notify/icons.txt")
    )
    icon = icons.resolve(base, cache_dir=cache_dir, icons_file=icons_file)

    platform = os.environ.get("CMD_NOTIFY_PLATFORM") or os.uname().sysname
    dispatch(platform, title, body, group, icon, dry_run=dry_run)


def _int_env(name: str, default: int) -> int:
    """Read an int env var, falling back to `default` when unset or non-numeric."""
    raw = os.environ.get(name)
    if raw is None or not raw.isdigit():
        return default
    return int(raw)
