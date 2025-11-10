# Claude Code Hooks - Capabilities Analysis

**Date:** 2025-11-09
**Status:** Complete
**Method:** Experimental testing with instrumented hooks

## Summary

Empirical analysis of Claude Code hook behavior to determine what's possible for building a notification system. Key findings: hooks run asynchronously, have configurable timeouts, and provide rich context via JSON and transcript access.

## Hook Types Tested

### Stop Hook

**Purpose:** Runs when Claude finishes responding (per docs: "when the main Claude Code agent has finished responding")

**Timing:**
- ✅ Fires when Claude naturally completes a response
- ❌ Does NOT fire on user interrupt
- ✅ Fires every response turn while waiting for user input

**Data Received (JSON via stdin):**
```json
{
  "session_id": "552e9a77-4cac-4533-8dc5-d6715c4733a2",
  "transcript_path": "/Users/karl/.claude/projects/.../session.jsonl",
  "cwd": "/Users/karl/.local/share/chezmoi",
  "permission_mode": "default",
  "hook_event_name": "Stop",
  "stop_hook_active": false
}
```

**Capabilities:**
- Access to full conversation history via `transcript_path` (JSONL format)
- Can block Claude from stopping (return non-zero exit code)
- Can provide feedback to prompt Claude to continue
- Default timeout: 60 seconds (configurable)

### Notification Hook

**Purpose:** Runs for permission requests and idle input (per docs)

**Timing:**
- ✅ Fires on permission requests (Claude needs tool approval)
- ✅ Fires on idle input (60+ seconds without user response)
- ❌ Does NOT fire for Stop events (separate hook)

**Data Received (JSON via stdin):**
```json
{
  "session_id": "2d0db740-a53c-4d40-bb47-1cc9bba718f2",
  "transcript_path": "/Users/karl/.claude/projects/.../session.jsonl",
  "cwd": "/Users/karl/.local/share/chezmoi",
  "hook_event_name": "Notification",
  "message": "Claude needs your permission to use Bash",
  "notification_type": "permission_prompt"
}
```

**Key Findings:**
- Includes human-readable `message` field
- Has `notification_type` to distinguish prompt types
- No unique ID for correlation across concurrent requests

## Execution Behavior

### Asynchronous Execution

**Test:** 65-second sleep in Notification hook

**Result:**
- ✅ UI remained fully responsive during hook execution
- ✅ User could type, interact, and respond to prompts
- ✅ Hook continued running in background

**Implication:** Hooks can perform slow operations (API calls, file I/O, presence detection) without degrading user experience.

### Hook Cancellation

**Initial hypothesis:** Hook gets killed when user responds to prompt

**Test:** Monitor hook with per-second logging

**Result:**
- ❌ Hook was NOT cancelled when user responded quickly
- ✅ Hook continued to completion (65 seconds)
- ✅ Audio played after full delay, proving hook ran

**Implication:** Hooks run to completion even after user responds. Can't use transcript monitoring to detect "user answered this specific notification."

### Timeout Behavior

**Default:**
- Timeout: 60 seconds
- No error messages when timeout occurs
- Hook simply terminates mid-execution

**Configurable:**
```json
{
  "type": "command",
  "command": "/path/to/script.sh",
  "timeout": 120
}
```

**Test:** Set timeout to 120 seconds, sleep for 65

**Result:**
- ✅ Hook ran to completion with increased timeout
- ✅ No timeout-related errors in logs

## Limitations Discovered

### 1. No TTY Context

**Finding:** Claude Code hooks run without TTY
**Impact:** Cannot determine which specific terminal session has focus
**Mitigation:** Can only check if iTerm2 is frontmost application (not session-specific)

### 2. No Request Correlation

**Finding:** Notification hook doesn't provide unique ID for the triggering request
**Impact:** Cannot reliably track "did user respond to THIS specific notification?"
**Mitigation:** Spawn background jobs for delayed actions instead of monitoring transcript

### 3. Multiple Concurrent Requests

**Problem:** If Claude tries to use `Bash` twice in quick succession:
- Both trigger Notification hooks
- Both have identical `message` field
- No way to distinguish which was answered

**Impact:** Cannot build "wait until user answers THIS notification" logic

### 4. Presence Detection Unreliable

**Available signals:**
- iTerm frontmost: `osascript` can check
- Keyboard/mouse idle time: `ioreg` can check
- Specific session focus: ❌ Not available

**Problem:** User reading long response appears "idle"
- iTerm focused: ✅
- Idle time: 20 seconds (appears away)
- Reality: User actively reading

**Impact:** Any idle-based heuristic has false positives

## Notification Click Actions (macOS)

### osascript Notifications

**Problem:** Native `osascript` notifications are attributed to Script Editor
- Clicking notification activates Script Editor, not terminal
- Shows "Show" buttons for file paths that open Script Editor's file dialog
- Cannot execute custom commands on click

**Verdict:** ❌ Not suitable for actionable notifications

### terminal-notifier

**Installation:** `brew install terminal-notifier`

**Capabilities:**
- ✅ Properly attributed to terminal/iTerm
- ✅ Supports `-execute` parameter to run commands on click
- ✅ No spurious "Show" buttons

**Example:**
```bash
terminal-notifier \
  -title "Claude Code" \
  -message "Session finished" \
  -sound Glass \
  -execute "/path/to/script.sh"
```

### Cross-Space Session Jumping

**Goal:** Click notification from any macOS Space/Desktop and jump to specific iTerm session

**Solution:**
1. Capture session ID when creating notification:
   ```bash
   SESSION_ID=$(osascript -e "tell application \"iTerm2\" to tell current session of current window to get id")
   ```

2. Helper script uses `select window` (not `set frontmost`):
   ```applescript
   tell application "iTerm2"
       activate
       repeat with w in windows
           repeat with t in tabs of w
               repeat with s in sessions of t
                   if id of s is "$SESSION_ID" then
                       select w  -- This triggers space switch!
                       select t
                       return
                   end if
               end repeat
           end repeat
       end repeat
   end tell
   ```

3. Full notification command:
   ```bash
   terminal-notifier \
     -title "Title" \
     -message "Message" \
     -execute "/path/to/jump-to-iterm-session-by-id.sh $SESSION_ID"
   ```

**Key insight:** Using `select window` in AppleScript triggers macOS to switch spaces.

**macOS Dependency:** This relies on the following system setting being enabled:
- **Settings → Desktop & Dock → "When switching to an application, switch to a Space with open windows for the application"**

**Tested:** ✅ Works reliably across spaces/desktops when setting is enabled

**Implementation:** See `jump-to-iterm-session-by-id.sh` in this directory

## Progressive Notifications

### Marker File Approach

**Goal:** Implement progressive notification escalation:
1. Immediate desktop notification (click to acknowledge)
2. Delayed push notification if not acknowledged (escalation)

**Solution:** Use marker files as acknowledgement flags

**Flow:**
1. Event occurs (command completes, Claude finishes)
2. Create marker file: `/tmp/ntfy-notifications/notification-{session_id}`
3. Show desktop notification with click handler that:
   - Deletes marker file (claims acknowledgement atomically)
   - Jumps to session
4. Spawn background task:
   - Waits N minutes (e.g., 10 minutes)
   - Checks if marker still exists
   - If exists: deletes marker, sends ntfy push
   - If missing: user acknowledged, no action needed

**Race Condition Prevention:**

Critical: Delete marker BEFORE slow operations (network, AppleScript):

```bash
# ✓ CORRECT - atomic claim
if [ -f "$MARKER_FILE" ]; then
    rm -f "$MARKER_FILE"  # Claim first
    # Now do slow operations
    curl ...
fi

# ✗ WRONG - race condition
if [ -f "$MARKER_FILE" ]; then
    curl ...  # Slow operation
    rm -f "$MARKER_FILE"  # Another process could trigger here
fi
```

**Benefits:**
- No false positives from presence detection
- User controls escalation (click = acknowledge)
- Progressive: desktop first, push only if needed
- Works across reboots (marker persists in /tmp)

**Tested:** ✅ Marker file approach works reliably

**Implementation:** See `progressive-notification-experiment.sh` in this directory

### Environment Detection

**Terminal environments have different capabilities:**

| Environment | Session ID | Activate Specific Window | Activate App | Focus Detection | Fallback Level |
|------------|-----------|-------------------------|--------------|----------------|----------------|
| iTerm2 | ✅ | ✅ | ✅ | ✅ | Level 1: Full support |
| VS Code | ❌ | ❌ | ✅ | ✅ | Level 2: App activation |
| Terminal.app | ❌ | ❌ | ✅ | ✅ | Level 2: App activation |
| SSH/API | ❌ | ❌ | ❌ | ❌ | Level 4: Push only |

**Detection Method:**

Check environment variables and capabilities:
```bash
# Check TERM_PROGRAM
if [ "${TERM_PROGRAM:-}" = "iTerm.app" ]; then
    # Try to get session ID
    if SESSION_ID=$(osascript -e "tell application \"iTerm2\" to ..."); then
        LEVEL=1  # Full support
    else
        LEVEL=2  # Partial
    fi
elif [ -n "${VSCODE_INJECTION:-}" ]; then
    LEVEL=3  # VS Code terminal
else
    LEVEL=4  # Unknown/minimal
fi
```

**Fallback Strategy:**

- **Level 1** (iTerm2): Full progressive notifications with click-to-jump-to-specific-session
  - Can get unique session ID via AppleScript
  - Can activate specific window across macOS Spaces
  - Focus detection: iTerm frontmost + user idle time

- **Level 2** (VS Code, Terminal.app): Desktop notification + click-to-activate-app
  - Cannot get session/window ID (not exposed to terminal or AppleScript)
  - Can activate entire application (all windows come to front)
  - User manually switches to correct window if multiple open
  - Focus detection: Check if app process is frontmost
  - Still "good enough" - matches typical macOS app switching (Cmd+Tab behavior)

- **Level 4** (SSH/API): ntfy push only (no desktop notification)

**Tested:**
- ✅ Environment detection works in iTerm2
- ✅ Environment detection works in VS Code terminal

**Implementation:** See `terminal-environment-detection.sh` in this directory

### VS Code Terminal Findings

**Test results from VS Code integrated terminal:**

**Detected capabilities:**
- ✅ Can detect VS Code environment (`VSCODE_INJECTION=1`, `TERM_PROGRAM=vscode`)
- ✅ Can call iTerm AppleScript commands (but returns iTerm session, not VS Code)
- ✅ Can send desktop notifications via terminal-notifier
- ✅ Can detect frontmost app for focus detection
- ✅ Can get user idle time via `ioreg`

**Limitations discovered:**
- ❌ Cannot get VS Code window ID from terminal environment
  - Window config UUIDs exist in process args but not exposed as env vars
  - No parent process chain to identify which VS Code window spawned terminal
- ❌ VS Code has no AppleScript dictionary (unlike iTerm2)
  - Can use System Events for basic app activation
  - Cannot query windows or target specific windows
- ❌ `code` CLI has no window management flags
- ❌ No VS Code extension API to expose window IDs to terminal

**Activation methods that work:**
```applescript
-- Activate VS Code (all windows come to front)
tell application "System Events"
    set frontmost of process "Code" to true
end tell
```

**Focus detection:**
```bash
# Check if VS Code is frontmost
FRONTMOST=$(osascript -e 'tell application "System Events" to get name of first application process whose frontmost is true')
if [[ "$FRONTMOST" == "Code" ]]; then
    # VS Code has focus
fi
```

**Verdict:** VS Code terminal supports Level 2 fallback (activate entire app, not specific window). This is acceptable - matches typical macOS app switching behavior where Cmd+Tab brings all windows to front.

## Configuration Schema

```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "ToolPattern",  // PreToolUse/PostToolUse only
        "hooks": [
          {
            "type": "command",      // or "prompt"
            "command": "/path/to/script.sh",
            "timeout": 120          // seconds (default: 60)
          }
        ]
      }
    ]
  }
}
```

## Transcript Format

Each entry in `transcript_path` is JSONL with structure:
```json
{
  "type": "assistant" | "user" | "tool_result" | "permission_grant",
  "timestamp": "2025-11-09T23:07:50.921Z",
  "uuid": "4b9dafec-ac3e-4e7e-9722-7bb53abd68dc",
  "sessionId": "62bd9004-db63-45d5-8f56-4165aa74a004",
  "message": { /* Claude API message format */ }
}
```

**Challenges for monitoring:**
- No correlation ID between Notification event and transcript entries
- Subagent activity adds entries
- Parallel session activity can interleave

## Linux Equivalents (Research-Based)

**Note:** This section is based on web research only. Suggested experiments below should be validated on actual Linux systems.

### Capability Comparison Matrix

| Capability | macOS | Linux (X11) | Linux (Wayland) | Notes |
|-----------|-------|-------------|-----------------|-------|
| **Desktop Notifications** | terminal-notifier | notify-send / dunstify | notify-send / dunstify | Linux notifications use freedesktop.org standard |
| **Click Actions** | `-execute` parameter | `-A` / `--action` parameter | `-A` / `--action` parameter | Returns action name to stdout |
| **Focus Detection** | osascript System Events | xdotool / wmctrl | D-Bus (compositor-specific) | Wayland is security-isolated by design |
| **Idle Time** | ioreg | xprintidle / XScreenSaver API | swayidle / ext-idle-notify | Wayland requires compositor support |
| **Terminal Session ID** | iTerm2 AppleScript | tmux/zellij session names | tmux/zellij session names | No direct equivalent to iTerm session ID |
| **Session Jumping** | AppleScript `select window` | `tmux switch-client` | `tmux switch-client` | zellij lacks direct session switching |

### Desktop Notifications

**notify-send (Standard):**
```bash
# Basic notification
notify-send "Title" "Message"

# With actions (blocks until user responds)
ACTION=$(notify-send --action="ack,Acknowledge" --action="ignore,Ignore" "Command finished")
if [ "$ACTION" = "ack" ]; then
    # User clicked "Acknowledge"
    rm -f "$MARKER_FILE"
fi
```

**dunstify (Enhanced):**
```bash
# dunst daemon provides richer functionality
dunstify -A yes,ACCEPT -A no,DECLINE "Call waiting"

# Returns action name on stdout (blocks until notification closed)
# Exit codes: 1 = timeout, 2 = dismissed manually, selected action name = action clicked
```

**Key Differences from macOS:**
- **Action paradigm**: Linux notifications use `-A action_name,label` to define clickable actions
- **Blocking behavior**: notify-send with `--action` blocks until user responds (different from terminal-notifier `-execute`)
- **Return value**: Action name goes to stdout; must wrap in shell logic to execute commands
- **Context menu**: dunst uses right-click context menu for actions (not inline buttons)

**Progressive Notification Implementation:**
```bash
# Spawn notification handler in background
(
    ACTION=$(notify-send --wait --action="ack,Acknowledge" "Command finished")
    if [ "$ACTION" = "ack" ]; then
        rm -f "$MARKER_FILE"  # Claim acknowledgement
        # Jump to session (see Terminal Automation below)
    fi
) &

# Spawn delayed push notification checker
(
    sleep 600  # 10 minutes
    if [ -f "$MARKER_FILE" ]; then
        rm -f "$MARKER_FILE"  # Atomic claim
        curl -X POST "https://ntfy.sh/topic" -d "Still waiting"
    fi
) &
```

### Terminal Automation

**tmux (Traditional):**
```bash
# Get current session name
TMUX_SESSION=$(tmux display-message -p '#S')

# Switch to session programmatically
tmux switch-client -t "$SESSION_NAME"

# Attach from outside tmux
tmux attach -t "$SESSION_NAME"

# Target specific window
tmux attach -t "$SESSION_NAME:$WINDOW_INDEX"
```

**zellij (Modern):**
```bash
# List sessions
zellij list-sessions

# Attach to session
zellij attach "$SESSION_NAME"

# Get session from inside zellij
# (No direct equivalent - would need to parse process tree or use layouts)

# CLI actions for automation
zellij action switch-mode normal
zellij action list-clients
```

**Limitations vs iTerm2:**
- **No unique session ID**: tmux/zellij use named sessions, not UUIDs
- **No direct switch**: zellij requires detach + attach (tmux has `switch-client`)
- **No window focus**: Cannot programmatically focus terminal emulator window
- **Plugin system**: zellij has WebAssembly plugins for custom session management

**Session Jumping Strategy:**
```bash
# For tmux - can switch directly if inside tmux
if [ -n "$TMUX" ]; then
    tmux switch-client -t "$SESSION_NAME"
else
    # Cannot jump to session from outside - must rely on terminal emulator
    # Best effort: activate terminal emulator application
    # (see Focus Detection below)
fi
```

### Focus Detection

**X11 (Traditional):**
```bash
# Get focused window (xdotool)
FOCUSED_WINDOW=$(xdotool getactivewindow)

# Get window properties
xdotool getactivewindow getwindowpid  # Get PID
xprop -id $(xdotool getactivewindow)  # Get all properties

# Get focused window class (wmctrl)
ACTIVE_CLASS=$(xdotool getactivewindow getwindowclassname)

# Check if terminal is focused
if [ "$ACTIVE_CLASS" = "kitty" ] || [ "$ACTIVE_CLASS" = "Alacritty" ]; then
    # Terminal has focus
fi
```

**Wayland (Modern, Compositor-Specific):**

Wayland has no global window focus concept by design (security isolation). Solutions vary by compositor:

**GNOME/Mutter:**
```bash
# Requires shell extension + D-Bus query
# No standard method - would need custom extension
```

**KDE/KWin:**
```bash
# D-Bus query for active window (if compositor exposes it)
gdbus call --session --dest org.kde.KWin \
    --object-path /KWin \
    --method org.kde.KWin.activeWindow
```

**Sway/wlroots:**
```bash
# Use swaymsg to query focused window
swaymsg -t get_tree | jq '.. | select(.focused? == true)'
```

**Detection Strategy:**
```bash
# Detect display server type
if [ -n "$WAYLAND_DISPLAY" ]; then
    # Wayland - compositor-specific methods
    case "$XDG_CURRENT_DESKTOP" in
        "GNOME") # Use GNOME-specific method ;;
        "KDE") # Use KDE-specific method ;;
        "sway") # Use sway-specific method ;;
    esac
elif [ -n "$DISPLAY" ]; then
    # X11 - use xdotool/wmctrl
    xdotool getactivewindow
fi
```

### Idle Time Detection

**X11:**
```bash
# xprintidle - simple and reliable
IDLE_MS=$(xprintidle)  # Milliseconds since last keyboard/mouse input

# XScreenSaver API (C library)
# Requires linking against libXss
# Returns idle time via XScreenSaverQueryInfo()
```

**Wayland:**

**ext-idle-notify-v1 protocol** (supported by KDE, wlroots compositors):
```bash
# swayidle - daemon that monitors idle state
swayidle -w \
    timeout 300 'echo "User idle for 5 minutes"' \
    resume 'echo "User active again"'
```

**GNOME/Mutter:**
```bash
# D-Bus query to IdleMonitor
gdbus call --session --dest org.gnome.Mutter.IdleMonitor \
    --object-path /org/gnome/Mutter/IdleMonitor/Core \
    --method org.gnome.Mutter.IdleMonitor.GetIdletime
```

**Challenges:**
- **Protocol fragmentation**: No universal Wayland idle detection API
- **Compositor support**: ext-idle-notify-v1 not implemented by GNOME as of 2025
- **Inhibitor awareness**: ext-idle-notify respects idle inhibitors (e.g., video playback)

**Hybrid Detection Strategy:**
```bash
# Try Wayland methods first, fall back to X11
detect_idle_time() {
    if command -v xprintidle &>/dev/null && [ -n "$DISPLAY" ]; then
        # X11 or XWayland
        xprintidle
    elif [ "$XDG_CURRENT_DESKTOP" = "gnome" ]; then
        # GNOME Wayland - use D-Bus
        gdbus call --session --dest org.gnome.Mutter.IdleMonitor ...
    else
        # Unknown - cannot detect
        echo "error"
    fi
}
```

### Terminal Emulator Detection

**Environment Variables:**
```bash
# Common terminal emulator identifiers
case "${TERM_PROGRAM:-}" in
    "vscode") TERM_TYPE="vscode" ;;
    "tmux") TERM_TYPE="tmux" ;;
    *) TERM_TYPE="unknown" ;;
esac

# Additional checks
[ -n "$KITTY_WINDOW_ID" ] && TERM_TYPE="kitty"
[ -n "$ALACRITTY_SOCKET" ] && TERM_TYPE="alacritty"
[ -n "$TMUX" ] && TERM_TYPE="tmux"
```

**Session Identification:**
- **kitty**: `$KITTY_WINDOW_ID`, supports remote control via `kitty @`
- **alacritty**: No session ID or remote control API
- **gnome-terminal**: D-Bus interface for window management
- **tmux**: Session name via `tmux display-message -p '#S'`
- **zellij**: Session name via environment or parsing `zellij list-sessions`

### Suggested Experiments

**Experiment 1: notify-send action handling**
```bash
# Test interactive notification with actions
#!/usr/bin/env bash
ACTION=$(notify-send --wait --action="yes,Yes" --action="no,No" "Test notification")
echo "User selected: $ACTION"
```

**Expected outcome:** Notification blocks until user clicks action or dismisses. Action name goes to stdout.

---

**Experiment 2: dunstify vs notify-send**
```bash
# Compare dunst vs libnotify behavior
if command -v dunstify &>/dev/null; then
    dunstify -A test,TestAction "Dunst test"
else
    notify-send --action="test,TestAction" "libnotify test"
fi
```

**Expected outcome:** Different UX - dunst uses context menu, libnotify may use inline buttons (depends on notification daemon).

---

**Experiment 3: tmux session switching**
```bash
# Test programmatic session switching
tmux new-session -d -s test-session
tmux switch-client -t test-session  # If inside tmux
tmux attach -t test-session  # If outside tmux
```

**Expected outcome:** Successful session switch. Note whether inside/outside tmux matters.

---

**Experiment 4: X11 vs Wayland idle detection**
```bash
# Detect idle time across display servers
#!/usr/bin/env bash
if command -v xprintidle &>/dev/null; then
    echo "X11 idle: $(xprintidle)ms"
fi

if [ "$XDG_CURRENT_DESKTOP" = "gnome" ]; then
    gdbus call --session --dest org.gnome.Mutter.IdleMonitor \
        --object-path /org/gnome/Mutter/IdleMonitor/Core \
        --method org.gnome.Mutter.IdleMonitor.GetIdletime
fi
```

**Expected outcome:** X11 returns milliseconds. GNOME D-Bus may require different object path. Other compositors vary.

---

**Experiment 5: Focus detection reliability**
```bash
# Test focus detection across terminals
#!/usr/bin/env bash
if command -v xdotool &>/dev/null; then
    ACTIVE_CLASS=$(xdotool getactivewindow getwindowclassname)
    echo "Active window: $ACTIVE_CLASS"
fi
```

**Expected outcome:** Works on X11. Fails on Wayland unless compositor-specific method used.

---

**Experiment 6: zellij session identification**
```bash
# Determine current zellij session name
#!/usr/bin/env bash
if [ -n "$ZELLIJ" ]; then
    # Inside zellij - parse from environment or process tree
    # (No direct environment variable as of 2025)
    ps -p $PPID -o comm=  # May show "zellij"
fi
```

**Expected outcome:** No direct session name variable. Must infer from process tree or zellij CLI output.

---

**Experiment 7: Terminal emulator activation**
```bash
# Test activating terminal window from script
#!/usr/bin/env bash
# X11 approach
TERM_WINDOW=$(xdotool search --class "kitty" | head -1)
xdotool windowactivate "$TERM_WINDOW"

# Wayland approach (compositor-specific)
# sway: swaymsg '[app_id="kitty"]' focus
```

**Expected outcome:** X11 works reliably. Wayland requires compositor-specific commands.

---

**Experiment 8: Progressive notifications on Linux**
```bash
# Full progressive notification flow
#!/usr/bin/env bash
MARKER="/tmp/test-notification-$$"
echo "test" > "$MARKER"

# Desktop notification with action
(
    ACTION=$(notify-send --wait --action="ack,Got it" "Test complete")
    [ "$ACTION" = "ack" ] && rm -f "$MARKER"
) &

# Delayed push
(
    sleep 60
    if [ -f "$MARKER" ]; then
        rm -f "$MARKER"
        curl -X POST "https://ntfy.sh/test" -d "Still waiting"
    fi
) &
```

**Expected outcome:** Desktop notification appears. If clicked, marker deleted and no push. If ignored for 60s, push notification sent.

---

### Platform Differences Summary

**Advantages on Linux:**
- **Standardized notifications**: freedesktop.org Desktop Notifications Specification
- **Rich terminal multiplexers**: tmux mature and ubiquitous, zellij modern with plugins
- **Package availability**: All tools available via package managers

**Challenges on Linux:**
- **Display server fragmentation**: X11 vs Wayland require different approaches
- **Compositor variation**: Wayland behavior varies by compositor (GNOME, KDE, Sway, etc.)
- **No universal focus detection**: Wayland security model prevents global window queries
- **Terminal emulator diversity**: No dominant terminal like iTerm2 on macOS
- **Session identification**: No UUID-based session IDs like iTerm2

**Recommended Linux Stack:**
- **Notifications**: dunst + dunstify (more features than basic notify-send)
- **Terminal multiplexer**: tmux (mature, predictable) or zellij (modern, extensible)
- **Idle detection**: xprintidle (X11) + compositor-specific Wayland methods
- **Focus detection**: xdotool (X11) + compositor-specific D-Bus/IPC (Wayland)

## Recommendations

Based on these findings:

1. **Use Stop hook for completion notifications**
   - Reliable trigger for "Claude finished"
   - Has all needed context (session, cwd, transcript)

2. **Keep hook logic simple and fast**
   - Default 60s timeout is reasonable
   - Spawn background jobs for delayed actions
   - Don't try to monitor transcript from within hook

3. **Avoid complex presence detection**
   - No reliable way to distinguish "reading" from "away"
   - Keep notification logic simple and predictable
   - Better to have occasional false positives with clear behavior

4. **Use terminal-notifier for actionable notifications**
   - Install with: `brew install terminal-notifier`
   - Capture iTerm session ID at notification time
   - Use `-execute` parameter with helper script for click-to-jump functionality
   - Requires macOS space-switching setting to be enabled

5. **Background job pattern for progressive notifications**
   ```bash
   # In hook:
   nohup /path/to/delayed-notifier.sh "$session_id" &
   exit 0  # Hook exits immediately

   # Background job can wait, re-check conditions, send notifications
   ```

## Nushell Integration

### Hook Function Requirements

**Environment Variable Persistence:**

Nushell hook functions must use `def --env` instead of `def` to persist environment variable changes:

```nushell
# ✗ WRONG - environment changes won't persist
export def my-pre-execution-hook [] {
    $env.MY_VAR = "value"  # Lost when function returns
}

# ✓ CORRECT - environment changes persist
export def --env my-pre-execution-hook [] {
    $env.MY_VAR = "value"  # Available after function returns
}
```

**Root Cause:** Regular `def` functions run in their own scope. Environment variable modifications are local to the function and don't propagate to the parent shell environment. The `--env` flag is required for hooks that need to communicate state between `pre_execution` and `pre_prompt` hooks.

### Type Conversions

**Environment Variables are Strings:**

Nushell environment variables are always strings and must be explicitly converted for arithmetic operations:

```nushell
# ✗ WRONG - CMD_DURATION_MS is a string
let duration_ns = ($env.CMD_DURATION_MS * 1_000_000)
# Error: The '*' operator does not work on values of type 'string'

# ✓ CORRECT - convert to int first
let duration_ns = (($env.CMD_DURATION_MS | into int) * 1_000_000)
```

**Relevant Variables:**
- `$env.CMD_DURATION_MS` - Command execution duration in milliseconds (string, environment variable)
- `$nu.pid` - Current shell process ID (int, built-in variable, not an environment variable)
- Custom environment variables set in hooks are strings by default

## Testing Methodology

**Test scripts in this directory:**
- `hook-stop-experiment.sh` - Stop hook timing and data
- `hook-notification-experiment.sh` - Notification hook async behavior and timeouts
- `notification-action-experiment.sh` - macOS notification click actions
- `jump-to-iterm-session-by-id.sh` - Cross-space session jumping (production-ready)
- `progressive-notification-experiment.sh` - Marker file approach for progressive notifications
- `terminal-environment-detection.sh` - Terminal capability detection and fallback strategy

**Instruments used:**
- Per-second timestamped logging
- Audio feedback on hook start
- Exit status tracking
- Cross-space desktop switching tests
