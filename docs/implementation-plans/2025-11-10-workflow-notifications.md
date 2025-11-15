# Workflow Notifications V2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a reliable notification system for long-running workflows (Claude Code + nushell commands) with progressive escalation and cross-platform support.

**Architecture:** Unix philosophy with 29 small composable scripts, environment-based strategies, marker files for progressive escalation, comprehensive test coverage.

**Tech Stack:** Bash, nushell, bats (testing), jq (JSON parsing), terminal-notifier (macOS), notify-send (Linux), ntfy (mobile push).

---

## Phase 1: Core Infrastructure

### Task 1: Create directory structure

**Files:**
- Create: `private_dot_local/lib/wkflw-ntfy/README.md`
- Create: `private_dot_local/lib/wkflw-ntfy/core/`
- Create: `private_dot_local/lib/wkflw-ntfy/marker/`
- Create: `private_dot_local/lib/wkflw-ntfy/macos/`
- Create: `private_dot_local/lib/wkflw-ntfy/linux/`
- Create: `private_dot_local/lib/wkflw-ntfy/escalation/`
- Create: `private_dot_local/lib/wkflw-ntfy/push/`
- Create: `private_dot_local/lib/wkflw-ntfy/hooks/`
- Create: `test/wkflw-ntfy/unit/`
- Create: `test/wkflw-ntfy/integration/`
- Create: `test/wkflw-ntfy/mocks/`
- Create: `test/wkflw-ntfy/helpers/`

**Step 1: Create directories**

```bash
mkdir -p private_dot_local/lib/wkflw-ntfy/{core,marker,macos,linux,escalation,push,hooks}
mkdir -p test/wkflw-ntfy/{unit,integration,mocks,helpers}
```

**Step 2: Create main README**

File: `private_dot_local/lib/wkflw-ntfy/README.md`

```markdown
# Workflow Notification System V2

## Architecture Overview

Small, composable bash scripts following Unix philosophy.
Each script does one thing well, tested in isolation.

## Directory Structure

- `core/` - Environment detection, strategy decisions, config, logging
- `marker/` - Marker file operations for progressive escalation
- `macos/` - macOS platform (terminal-notifier, AppleScript)
- `linux/` - Linux platform (notify-send)
- `escalation/` - Progressive escalation (spawn worker, check marker)
- `push/` - ntfy push notifications
- `hooks/` - Entry points for Claude Code and nushell hooks

## Design Documents

See:
- `docs/design-product/2025-11-10-workflow-notifications.md`
- `docs/design-engineering/2025-11-10-workflow-notifications.md`

## Testing

Run tests: `bats test/wkflw-ntfy/`
```

**Step 3: Verify structure**

```bash
ls -R private_dot_local/lib/wkflw-ntfy/
ls -R test/wkflw-ntfy/
```

Expected: All directories exist.

**Step 4: Commit**

```bash
git add private_dot_local/lib/wkflw-ntfy/ test/wkflw-ntfy/
git commit -m "chore: create wkflw-ntfy directory structure

- Add component directories (core, marker, macos, linux, escalation, push, hooks)
- Add test directories (unit, integration, mocks, helpers)
- Add main README explaining architecture

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: Implement config loader

**Files:**
- Create: `private_dot_local/lib/wkflw-ntfy/core/executable_wkflw-ntfy-config`
- Create: `test/wkflw-ntfy/unit/test_config.bats`

**Step 1: Write failing test**

File: `test/wkflw-ntfy/unit/test_config.bats`

```bash
#!/usr/bin/env bats

@test "config loads defaults when env vars not set" {
    unset WKFLW_NTFY_SERVER
    unset WKFLW_NTFY_NUSHELL_THRESHOLD
    unset WKFLW_NTFY_ESCALATION_DELAY
    unset WKFLW_NTFY_DEBUG

    source private_dot_local/lib/wkflw-ntfy/core/wkflw-ntfy-config

    [[ "$WKFLW_NTFY_SERVER" == "https://ntfy.sh" ]]
    [[ "$WKFLW_NTFY_NUSHELL_THRESHOLD" == "90" ]]
    [[ "$WKFLW_NTFY_ESCALATION_DELAY" == "120" ]]
    [[ "$WKFLW_NTFY_DEBUG" == "0" ]]
}

@test "config respects env var overrides" {
    export WKFLW_NTFY_SERVER="https://custom.ntfy.sh"
    export WKFLW_NTFY_NUSHELL_THRESHOLD="120"
    export WKFLW_NTFY_ESCALATION_DELAY="300"
    export WKFLW_NTFY_DEBUG="1"

    source private_dot_local/lib/wkflw-ntfy/core/wkflw-ntfy-config

    [[ "$WKFLW_NTFY_SERVER" == "https://custom.ntfy.sh" ]]
    [[ "$WKFLW_NTFY_NUSHELL_THRESHOLD" == "120" ]]
    [[ "$WKFLW_NTFY_ESCALATION_DELAY" == "300" ]]
    [[ "$WKFLW_NTFY_DEBUG" == "1" ]]
}

@test "config reads ntfy topic from state file if exists" {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR"
    echo "WKFLW_NTFY_TOPIC=macbook-karl-abc123" > "$WKFLW_NTFY_STATE_DIR/config"

    source private_dot_local/lib/wkflw-ntfy/core/wkflw-ntfy-config

    [[ "$WKFLW_NTFY_TOPIC" == "macbook-karl-abc123" ]]
}

@test "config warns if ntfy topic missing" {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR"
    # No config file

    unset WKFLW_NTFY_TOPIC
    source private_dot_local/lib/wkflw-ntfy/core/wkflw-ntfy-config 2>&1 | grep -q "WARNING"
}
```

**Step 2: Run test to verify it fails**

```bash
bats test/wkflw-ntfy/unit/test_config.bats
```

Expected: FAIL with "file not found" errors.

**Step 3: Implement config loader**

File: `private_dot_local/lib/wkflw-ntfy/core/executable_wkflw-ntfy-config`

```bash
#!/usr/bin/env bash
# wkflw-ntfy-config: Load configuration from environment variables
#
# Usage: source wkflw-ntfy-config
#
# Sets environment variables with defaults:
# - WKFLW_NTFY_SERVER (default: https://ntfy.sh)
# - WKFLW_NTFY_NUSHELL_THRESHOLD (default: 90)
# - WKFLW_NTFY_ESCALATION_DELAY (default: 120)
# - WKFLW_NTFY_DEBUG (default: 0)
# - WKFLW_NTFY_TOPIC (from state file or env)
# - WKFLW_NTFY_STATE_DIR (default: ~/.local/state/wkflw-ntfy)

set -euo pipefail

# State directory for config and marker files
: "${WKFLW_NTFY_STATE_DIR:=$HOME/.local/state/wkflw-ntfy}"

# Configuration with defaults
: "${WKFLW_NTFY_SERVER:=https://ntfy.sh}"
: "${WKFLW_NTFY_NUSHELL_THRESHOLD:=90}"
: "${WKFLW_NTFY_ESCALATION_DELAY:=120}"
: "${WKFLW_NTFY_DEBUG:=0}"

# Read ntfy topic from state file if not already set
if [[ -z "${WKFLW_NTFY_TOPIC:-}" ]]; then
    config_file="$WKFLW_NTFY_STATE_DIR/config"
    if [[ -f "$config_file" ]]; then
        # Source config file to load WKFLW_NTFY_TOPIC
        # shellcheck disable=SC1090
        source "$config_file"
    else
        echo "WARNING: WKFLW_NTFY_TOPIC not set and config file not found at $config_file" >&2
        echo "Mobile push notifications will not work until topic is configured." >&2
    fi
fi

# Export all config for use by child processes
export WKFLW_NTFY_STATE_DIR
export WKFLW_NTFY_SERVER
export WKFLW_NTFY_NUSHELL_THRESHOLD
export WKFLW_NTFY_ESCALATION_DELAY
export WKFLW_NTFY_DEBUG
export WKFLW_NTFY_TOPIC
```

**Step 4: Make executable**

```bash
chmod +x private_dot_local/lib/wkflw-ntfy/core/executable_wkflw-ntfy-config
```

**Step 5: Run test to verify it passes**

```bash
bats test/wkflw-ntfy/unit/test_config.bats
```

Expected: All tests PASS.

**Step 6: Commit**

```bash
git add private_dot_local/lib/wkflw-ntfy/core/executable_wkflw-ntfy-config test/wkflw-ntfy/unit/test_config.bats
git commit -m "feat(wkflw-ntfy): add config loader with env var support

- Load config from env vars with sensible defaults
- Read ntfy topic from state file
- Warn if topic missing
- Add comprehensive unit tests

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: Implement logging utility

**Files:**
- Create: `private_dot_local/lib/wkflw-ntfy/core/executable_wkflw-ntfy-log`
- Create: `test/wkflw-ntfy/unit/test_log.bats`

**Step 1: Write failing test**

File: `test/wkflw-ntfy/unit/test_log.bats`

```bash
#!/usr/bin/env bats

setup() {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR"
    export PATH="$PWD/private_dot_local/lib/wkflw-ntfy/core:$PATH"
}

@test "log debug writes to debug log when debug enabled" {
    export WKFLW_NTFY_DEBUG=1
    wkflw-ntfy-log debug "test-component" "test message"

    debug_log="$WKFLW_NTFY_STATE_DIR/debug-$$.log"
    [ -f "$debug_log" ]
    grep -q "test message" "$debug_log"
    grep -q "test-component" "$debug_log"
}

@test "log debug does nothing when debug disabled" {
    export WKFLW_NTFY_DEBUG=0
    wkflw-ntfy-log debug "test-component" "test message"

    debug_log="$WKFLW_NTFY_STATE_DIR/debug-$$.log"
    [ ! -f "$debug_log" ]
}

@test "log warning writes to warnings log" {
    wkflw-ntfy-log warning "test-component" "test warning"

    warnings_log="$WKFLW_NTFY_STATE_DIR/warnings.log"
    [ -f "$warnings_log" ]
    grep -q "test warning" "$warnings_log"
    grep -q "WARNING" "$warnings_log"
}

@test "log error writes to warnings log" {
    wkflw-ntfy-log error "test-component" "test error"

    warnings_log="$WKFLW_NTFY_STATE_DIR/warnings.log"
    [ -f "$warnings_log" ]
    grep -q "test error" "$warnings_log"
    grep -q "ERROR" "$warnings_log"
}
```

**Step 2: Run test to verify it fails**

```bash
bats test/wkflw-ntfy/unit/test_log.bats
```

Expected: FAIL with command not found.

**Step 3: Implement logging utility**

File: `private_dot_local/lib/wkflw-ntfy/core/executable_wkflw-ntfy-log`

```bash
#!/usr/bin/env bash
# wkflw-ntfy-log: Logging utility for wkflw-ntfy components
#
# Usage: wkflw-ntfy-log <level> <component> <message>
#   level: debug, warning, error
#   component: Name of calling component (e.g., "marker-create", "macos-send")
#   message: Log message
#
# Debug logs go to: $WKFLW_NTFY_STATE_DIR/debug-{pid}.log (only if WKFLW_NTFY_DEBUG=1)
# Warnings/errors go to: $WKFLW_NTFY_STATE_DIR/warnings.log (always)

set -euo pipefail

# Load config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/wkflw-ntfy-config"

level="${1:-}"
component="${2:-}"
message="${3:-}"

if [[ -z "$level" || -z "$component" || -z "$message" ]]; then
    echo "Usage: wkflw-ntfy-log <level> <component> <message>" >&2
    exit 1
fi

timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
log_line="[$timestamp] [$(echo "$level" | tr '[:lower:]' '[:upper:]')] [$component] $message"

case "$level" in
    debug)
        if [[ "${WKFLW_NTFY_DEBUG:-0}" == "1" ]]; then
            debug_log="$WKFLW_NTFY_STATE_DIR/debug-$$.log"
            mkdir -p "$WKFLW_NTFY_STATE_DIR"
            echo "$log_line" >> "$debug_log"
        fi
        ;;
    warning|error)
        warnings_log="$WKFLW_NTFY_STATE_DIR/warnings.log"
        mkdir -p "$WKFLW_NTFY_STATE_DIR"
        echo "$log_line" >> "$warnings_log"
        ;;
    *)
        echo "Unknown log level: $level (use debug, warning, or error)" >&2
        exit 1
        ;;
esac
```

**Step 4: Make executable**

```bash
chmod +x private_dot_local/lib/wkflw-ntfy/core/executable_wkflw-ntfy-log
```

**Step 5: Run test to verify it passes**

```bash
bats test/wkflw-ntfy/unit/test_log.bats
```

Expected: All tests PASS.

**Step 6: Commit**

```bash
git add private_dot_local/lib/wkflw-ntfy/core/executable_wkflw-ntfy-log test/wkflw-ntfy/unit/test_log.bats
git commit -m "feat(wkflw-ntfy): add logging utility with debug support

- Support debug/warning/error log levels
- PID-isolated debug logs
- Conditional debug logging based on env var
- Add comprehensive unit tests

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: Implement environment detection

**Files:**
- Create: `private_dot_local/lib/wkflw-ntfy/core/executable_wkflw-ntfy-detect-env`
- Create: `test/wkflw-ntfy/unit/test_detect_env.bats`

**Step 1: Write failing test**

File: `test/wkflw-ntfy/unit/test_detect_env.bats`

```bash
#!/usr/bin/env bats

setup() {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR"
    export WKFLW_NTFY_DEBUG=0
    export PATH="$PWD/private_dot_local/lib/wkflw-ntfy/core:$PATH"
}

@test "detect-env identifies iTerm" {
    export TERM_PROGRAM="iTerm.app"
    result=$(wkflw-ntfy-detect-env)
    [[ "$result" == "iterm" ]]
}

@test "detect-env identifies macOS GUI (non-iTerm)" {
    export TERM_PROGRAM="Apple_Terminal"
    result=$(wkflw-ntfy-detect-env)
    [[ "$result" == "macos-gui" ]]
}

@test "detect-env identifies Linux GUI (X11)" {
    unset TERM_PROGRAM
    export DISPLAY=":0"
    result=$(wkflw-ntfy-detect-env)
    [[ "$result" == "linux-gui" ]]
}

@test "detect-env identifies Linux GUI (Wayland)" {
    unset TERM_PROGRAM
    unset DISPLAY
    export WAYLAND_DISPLAY="wayland-0"
    result=$(wkflw-ntfy-detect-env)
    [[ "$result" == "linux-gui" ]]
}

@test "detect-env identifies no-GUI (SSH)" {
    unset TERM_PROGRAM
    unset DISPLAY
    unset WAYLAND_DISPLAY
    export SSH_CONNECTION="1.2.3.4 12345 5.6.7.8 22"
    result=$(wkflw-ntfy-detect-env)
    [[ "$result" == "nogui" ]]
}

@test "detect-env identifies no-GUI (headless)" {
    unset TERM_PROGRAM
    unset DISPLAY
    unset WAYLAND_DISPLAY
    unset SSH_CONNECTION
    result=$(wkflw-ntfy-detect-env)
    [[ "$result" == "nogui" ]]
}
```

**Step 2: Run test to verify it fails**

```bash
bats test/wkflw-ntfy/unit/test_detect_env.bats
```

Expected: FAIL with command not found.

**Step 3: Implement environment detection**

File: `private_dot_local/lib/wkflw-ntfy/core/executable_wkflw-ntfy-detect-env`

```bash
#!/usr/bin/env bash
# wkflw-ntfy-detect-env: Detect terminal environment
#
# Usage: wkflw-ntfy-detect-env
#
# Outputs one of:
# - iterm: macOS iTerm2 session
# - macos-gui: macOS GUI terminal (non-iTerm)
# - linux-gui: Linux GUI session (X11/Wayland)
# - nogui: Non-GUI session (SSH, headless, etc.)

set -euo pipefail

# Load config and logging
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/wkflw-ntfy-config"

# Check for iTerm2
if [[ "${TERM_PROGRAM:-}" == "iTerm.app" ]]; then
    "$SCRIPT_DIR/wkflw-ntfy-log" debug "detect-env" "Detected iTerm2 session"
    echo "iterm"
    exit 0
fi

# Check for macOS GUI (any terminal on macOS)
if [[ "$(uname -s)" == "Darwin" ]] && [[ -n "${TERM_PROGRAM:-}" ]]; then
    "$SCRIPT_DIR/wkflw-ntfy-log" debug "detect-env" "Detected macOS GUI (non-iTerm): $TERM_PROGRAM"
    echo "macos-gui"
    exit 0
fi

# Check for Linux GUI (X11 or Wayland)
if [[ -n "${DISPLAY:-}" ]] || [[ -n "${WAYLAND_DISPLAY:-}" ]]; then
    "$SCRIPT_DIR/wkflw-ntfy-log" debug "detect-env" "Detected Linux GUI session"
    echo "linux-gui"
    exit 0
fi

# Default: no GUI (SSH, headless, etc.)
"$SCRIPT_DIR/wkflw-ntfy-log" debug "detect-env" "Detected non-GUI session"
echo "nogui"
```

**Step 4: Make executable**

```bash
chmod +x private_dot_local/lib/wkflw-ntfy/core/executable_wkflw-ntfy-detect-env
```

**Step 5: Run test to verify it passes**

```bash
bats test/wkflw-ntfy/unit/test_detect_env.bats
```

Expected: All tests PASS.

**Step 6: Commit**

```bash
git add private_dot_local/lib/wkflw-ntfy/core/executable_wkflw-ntfy-detect-env test/wkflw-ntfy/unit/test_detect_env.bats
git commit -m "feat(wkflw-ntfy): add environment detection

- Detect iTerm, macOS GUI, Linux GUI, no-GUI
- Use TERM_PROGRAM, DISPLAY, WAYLAND_DISPLAY
- Add comprehensive unit tests

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: Implement strategy decision

**Files:**
- Create: `private_dot_local/lib/wkflw-ntfy/core/executable_wkflw-ntfy-decide-strategy`
- Create: `test/wkflw-ntfy/unit/test_decide_strategy.bats`

**Step 1: Write failing test**

File: `test/wkflw-ntfy/unit/test_decide_strategy.bats`

```bash
#!/usr/bin/env bats

setup() {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR"
    export WKFLW_NTFY_DEBUG=0
    export PATH="$PWD/private_dot_local/lib/wkflw-ntfy/core:$PATH"
}

@test "iTerm + claude-stop → progressive" {
    result=$(wkflw-ntfy-decide-strategy "iterm" "claude-stop" "")
    [[ "$result" == "progressive" ]]
}

@test "iTerm + claude-notification permission_prompt → desktop-only" {
    result=$(wkflw-ntfy-decide-strategy "iterm" "claude-notification" "permission_prompt")
    [[ "$result" == "desktop-only" ]]
}

@test "iTerm + claude-notification idle_input → progressive" {
    result=$(wkflw-ntfy-decide-strategy "iterm" "claude-notification" "idle_input")
    [[ "$result" == "progressive" ]]
}

@test "iTerm + nushell → progressive" {
    result=$(wkflw-ntfy-decide-strategy "iterm" "nushell" "")
    [[ "$result" == "progressive" ]]
}

@test "macos-gui + any event → desktop-only" {
    result=$(wkflw-ntfy-decide-strategy "macos-gui" "claude-stop" "")
    [[ "$result" == "desktop-only" ]]
}

@test "linux-gui + any event → desktop-only" {
    result=$(wkflw-ntfy-decide-strategy "linux-gui" "claude-stop" "")
    [[ "$result" == "desktop-only" ]]
}

@test "nogui + any event → push-only" {
    result=$(wkflw-ntfy-decide-strategy "nogui" "claude-stop" "")
    [[ "$result" == "push-only" ]]
}
```

**Step 2: Run test to verify it fails**

```bash
bats test/wkflw-ntfy/unit/test_decide_strategy.bats
```

Expected: FAIL with command not found.

**Step 3: Implement strategy decision**

File: `private_dot_local/lib/wkflw-ntfy/core/executable_wkflw-ntfy-decide-strategy`

```bash
#!/usr/bin/env bash
# wkflw-ntfy-decide-strategy: Choose notification strategy
#
# Usage: wkflw-ntfy-decide-strategy <environment> <event-type> <notification-type>
#   environment: Output from wkflw-ntfy-detect-env
#   event-type: claude-stop, claude-notification, nushell
#   notification-type: For claude-notification: permission_prompt, idle_input, etc. (empty for others)
#
# Outputs one of:
# - progressive: Desktop notification + escalation to push
# - desktop-only: Desktop notification, no escalation
# - push-only: Mobile push only
# - none: No notification

set -euo pipefail

# Load config and logging
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/wkflw-ntfy-config"

environment="${1:-}"
event_type="${2:-}"
notification_type="${3:-}"

if [[ -z "$environment" || -z "$event_type" ]]; then
    echo "Usage: wkflw-ntfy-decide-strategy <environment> <event-type> <notification-type>" >&2
    exit 1
fi

# Decision logic
case "$environment" in
    iterm)
        # iTerm supports progressive escalation
        if [[ "$event_type" == "claude-notification" && "$notification_type" == "permission_prompt" ]]; then
            # Permission prompts don't escalate (user must be at desktop)
            "$SCRIPT_DIR/wkflw-ntfy-log" debug "decide-strategy" "iTerm + permission_prompt → desktop-only"
            echo "desktop-only"
        else
            # All other events: progressive escalation
            "$SCRIPT_DIR/wkflw-ntfy-log" debug "decide-strategy" "iTerm + $event_type → progressive"
            echo "progressive"
        fi
        ;;
    macos-gui)
        # macOS non-iTerm: desktop only (no window focusing, so no escalation)
        "$SCRIPT_DIR/wkflw-ntfy-log" debug "decide-strategy" "macOS GUI → desktop-only"
        echo "desktop-only"
        ;;
    linux-gui)
        # Linux GUI: desktop only (not yet tested/proven for escalation)
        "$SCRIPT_DIR/wkflw-ntfy-log" debug "decide-strategy" "Linux GUI → desktop-only"
        echo "desktop-only"
        ;;
    nogui)
        # No GUI: push only
        "$SCRIPT_DIR/wkflw-ntfy-log" debug "decide-strategy" "No GUI → push-only"
        echo "push-only"
        ;;
    *)
        "$SCRIPT_DIR/wkflw-ntfy-log" error "decide-strategy" "Unknown environment: $environment"
        echo "none"
        exit 1
        ;;
esac
```

**Step 4: Make executable**

```bash
chmod +x private_dot_local/lib/wkflw-ntfy/core/executable_wkflw-ntfy-decide-strategy
```

**Step 5: Run test to verify it passes**

```bash
bats test/wkflw-ntfy/unit/test_decide_strategy.bats
```

Expected: All tests PASS.

**Step 6: Commit**

```bash
git add private_dot_local/lib/wkflw-ntfy/core/executable_wkflw-ntfy-decide-strategy test/wkflw-ntfy/unit/test_decide_strategy.bats
git commit -m "feat(wkflw-ntfy): add strategy decision logic

- Choose progressive/desktop-only/push-only based on environment
- Special handling for permission prompts (no escalation)
- Add comprehensive unit tests

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: Implement marker operations

**Files:**
- Create: `private_dot_local/lib/wkflw-ntfy/marker/executable_wkflw-ntfy-marker-create`
- Create: `private_dot_local/lib/wkflw-ntfy/marker/executable_wkflw-ntfy-marker-check`
- Create: `private_dot_local/lib/wkflw-ntfy/marker/executable_wkflw-ntfy-marker-delete`
- Create: `test/wkflw-ntfy/unit/test_marker.bats`

**Step 1: Write failing test**

File: `test/wkflw-ntfy/unit/test_marker.bats`

```bash
#!/usr/bin/env bats

setup() {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR/markers"
    export WKFLW_NTFY_DEBUG=0
    export PATH="$PWD/private_dot_local/lib/wkflw-ntfy/marker:$PWD/private_dot_local/lib/wkflw-ntfy/core:$PATH"
}

@test "marker-create creates file with correct name pattern" {
    marker_path=$(wkflw-ntfy-marker-create "claude-stop" "/test/dir")

    [ -f "$marker_path" ]
    [[ "$marker_path" == *"claude-stop-"* ]]
    [[ "$marker_path" == *"-$$" ]]
}

@test "marker-create writes JSON payload" {
    marker_path=$(wkflw-ntfy-marker-create "nushell" "/home/user/project")

    grep -q '"event_type": "nushell"' "$marker_path"
    grep -q '"cwd": "/home/user/project"' "$marker_path"
    grep -q '"pid": ' "$marker_path"
}

@test "marker-check returns 0 for existing marker" {
    marker_path=$(wkflw-ntfy-marker-create "test" "/test")
    wkflw-ntfy-marker-check "$marker_path"
}

@test "marker-check returns 1 for missing marker" {
    run wkflw-ntfy-marker-check "/nonexistent/marker"
    [ "$status" -eq 1 ]
}

@test "marker-delete removes marker file" {
    marker_path=$(wkflw-ntfy-marker-create "test" "/test")
    [ -f "$marker_path" ]

    wkflw-ntfy-marker-delete "$marker_path"
    [ ! -f "$marker_path" ]
}

@test "marker-delete is idempotent" {
    marker_path="$WKFLW_NTFY_STATE_DIR/markers/test-marker"
    touch "$marker_path"

    wkflw-ntfy-marker-delete "$marker_path"
    wkflw-ntfy-marker-delete "$marker_path"  # Should not error
}
```

**Step 2: Run test to verify it fails**

```bash
bats test/wkflw-ntfy/unit/test_marker.bats
```

Expected: FAIL with command not found.

**Step 3: Implement marker-create**

File: `private_dot_local/lib/wkflw-ntfy/marker/executable_wkflw-ntfy-marker-create`

```bash
#!/usr/bin/env bash
# wkflw-ntfy-marker-create: Create marker file for progressive escalation
#
# Usage: wkflw-ntfy-marker-create <event-type> <cwd>
#   event-type: claude-stop, claude-notification, nushell
#   cwd: Current working directory
#
# Outputs: Full path to created marker file

set -euo pipefail

# Load config and logging
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../core/wkflw-ntfy-config"

event_type="${1:-}"
cwd="${2:-}"

if [[ -z "$event_type" || -z "$cwd" ]]; then
    echo "Usage: wkflw-ntfy-marker-create <event-type> <cwd>" >&2
    exit 1
fi

# Create markers directory
markers_dir="$WKFLW_NTFY_STATE_DIR/markers"
mkdir -p "$markers_dir"

# Generate unique marker filename
timestamp="$(date +%s)"
marker_file="$markers_dir/${event_type}-${timestamp}-$$"

# Write JSON payload
cat > "$marker_file" <<EOF
{
  "event_type": "$event_type",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "pid": $$,
  "cwd": "$cwd"
}
EOF

"$SCRIPT_DIR/../core/wkflw-ntfy-log" debug "marker-create" "Created marker: $marker_file"
echo "$marker_file"
```

**Step 4: Implement marker-check**

File: `private_dot_local/lib/wkflw-ntfy/marker/executable_wkflw-ntfy-marker-check`

```bash
#!/usr/bin/env bash
# wkflw-ntfy-marker-check: Check if marker file exists
#
# Usage: wkflw-ntfy-marker-check <marker-file-path>
#
# Exit codes:
# - 0: Marker exists
# - 1: Marker does not exist

set -euo pipefail

marker_file="${1:-}"

if [[ -z "$marker_file" ]]; then
    echo "Usage: wkflw-ntfy-marker-check <marker-file-path>" >&2
    exit 1
fi

if [[ -f "$marker_file" ]]; then
    exit 0
else
    exit 1
fi
```

**Step 5: Implement marker-delete**

File: `private_dot_local/lib/wkflw-ntfy/marker/executable_wkflw-ntfy-marker-delete`

```bash
#!/usr/bin/env bash
# wkflw-ntfy-marker-delete: Delete marker file (atomic claim)
#
# Usage: wkflw-ntfy-marker-delete <marker-file-path>
#
# Idempotent: Succeeds even if file already deleted

set -euo pipefail

# Load config and logging
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../core/wkflw-ntfy-config"

marker_file="${1:-}"

if [[ -z "$marker_file" ]]; then
    echo "Usage: wkflw-ntfy-marker-delete <marker-file-path>" >&2
    exit 1
fi

# Delete marker (idempotent with -f)
rm -f "$marker_file"
"$SCRIPT_DIR/../core/wkflw-ntfy-log" debug "marker-delete" "Deleted marker: $marker_file"
```

**Step 6: Make executables**

```bash
chmod +x private_dot_local/lib/wkflw-ntfy/marker/executable_wkflw-ntfy-marker-*
```

**Step 7: Run test to verify it passes**

```bash
bats test/wkflw-ntfy/unit/test_marker.bats
```

Expected: All tests PASS.

**Step 8: Commit**

```bash
git add private_dot_local/lib/wkflw-ntfy/marker/ test/wkflw-ntfy/unit/test_marker.bats
git commit -m "feat(wkflw-ntfy): add marker file operations

- Create marker with JSON payload
- Check marker existence
- Delete marker (atomic, idempotent)
- Add comprehensive unit tests

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 2: macOS Platform Support

### Task 7: Create test mocks

**Files:**
- Create: `test/wkflw-ntfy/mocks/executable_terminal-notifier`
- Create: `test/wkflw-ntfy/mocks/executable_osascript`
- Create: `test/wkflw-ntfy/mocks/executable_curl`
- Create: `test/wkflw-ntfy/mocks/README.md`
- Create: `test/wkflw-ntfy/helpers/test_helpers.bash`

**Step 1: Create mock for terminal-notifier**

File: `test/wkflw-ntfy/mocks/executable_terminal-notifier`

```bash
#!/usr/bin/env bash
# Mock terminal-notifier for testing
# Logs all invocations to terminal-notifier.log

MOCK_LOG_DIR="${MOCK_LOG_DIR:-/tmp}"
MOCK_LOG="$MOCK_LOG_DIR/terminal-notifier.log"

echo "$(date +%Y-%m-%dT%H:%M:%S) $0 $*" >> "$MOCK_LOG"

# Extract -execute callback if present
for i in "$@"; do
    if [[ "$execute_next" == "1" ]]; then
        # Log the callback script path
        echo "CALLBACK: $i" >> "$MOCK_LOG"

        # Execute the callback if MOCK_EXEC_CALLBACKS is set
        if [[ "${MOCK_EXEC_CALLBACKS:-}" == "1" ]]; then
            bash "$i"
        fi
        execute_next=0
    fi

    if [[ "$i" == "-execute" ]]; then
        execute_next=1
    fi
done

exit 0
```

**Step 2: Create mock for osascript**

File: `test/wkflw-ntfy/mocks/executable_osascript`

```bash
#!/usr/bin/env bash
# Mock osascript for testing
# Logs invocations and returns fake window IDs

MOCK_LOG_DIR="${MOCK_LOG_DIR:-/tmp}"
MOCK_LOG="$MOCK_LOG_DIR/osascript.log"

echo "$(date +%Y-%m-%dT%H:%M:%S) $0 $*" >> "$MOCK_LOG"

# If getting window ID, return fake ID
if echo "$*" | grep -q "id of current window"; then
    echo "window id 12345"
fi

# If selecting window, succeed silently
if echo "$*" | grep -q "select window"; then
    exit 0
fi

exit 0
```

**Step 3: Create mock for curl**

File: `test/wkflw-ntfy/mocks/executable_curl`

```bash
#!/usr/bin/env bash
# Mock curl for testing
# Logs invocations (ntfy push simulation)

MOCK_LOG_DIR="${MOCK_LOG_DIR:-/tmp}"
MOCK_LOG="$MOCK_LOG_DIR/curl.log"

echo "$(date +%Y-%m-%dT%H:%M:%S) $0 $*" >> "$MOCK_LOG"

# Simulate successful POST
exit 0
```

**Step 4: Create mocks README**

File: `test/wkflw-ntfy/mocks/README.md`

```markdown
# Test Mocks

Mock executables for testing wkflw-ntfy without real system tools.

## Available Mocks

- `terminal-notifier` - macOS desktop notifications
- `osascript` - AppleScript (window ID, focus)
- `curl` - ntfy push notifications

## Usage

Inject mocks into PATH:

```bash
export MOCK_LOG_DIR="$BATS_TEST_TMPDIR/logs"
mkdir -p "$MOCK_LOG_DIR"
export PATH="test/wkflw-ntfy/mocks:$PATH"
```

## Verification

Check mock invocations:

```bash
cat "$MOCK_LOG_DIR/terminal-notifier.log"
grep -q "POST" "$MOCK_LOG_DIR/curl.log"
```

## Callback Execution

To test callbacks, set `MOCK_EXEC_CALLBACKS=1` before calling mocked terminal-notifier.
```

**Step 5: Create test helpers**

File: `test/wkflw-ntfy/helpers/test_helpers.bash`

```bash
#!/usr/bin/env bash
# Test helpers for wkflw-ntfy tests

# Setup mock environment
setup_mocks() {
    export MOCK_LOG_DIR="$BATS_TEST_TMPDIR/logs"
    mkdir -p "$MOCK_LOG_DIR"
    export PATH="$PWD/test/wkflw-ntfy/mocks:$PATH"

    # Clear old logs
    rm -f "$MOCK_LOG_DIR"/*.log
}

# Assertions
assert_file_exists() {
    [ -f "$1" ] || {
        echo "File not found: $1" >&2
        return 1
    }
}

assert_file_contains() {
    grep -q "$2" "$1" || {
        echo "File $1 does not contain: $2" >&2
        echo "Contents:" >&2
        cat "$1" >&2
        return 1
    }
}

assert_mock_called() {
    local mock_name="$1"
    local mock_log="$MOCK_LOG_DIR/$mock_name.log"
    [ -f "$mock_log" ] || {
        echo "Mock $mock_name was not called (no log file)" >&2
        return 1
    }
}

assert_mock_not_called() {
    local mock_name="$1"
    local mock_log="$MOCK_LOG_DIR/$mock_name.log"
    [ ! -f "$mock_log" ] || {
        echo "Mock $mock_name should not have been called" >&2
        echo "Log contents:" >&2
        cat "$mock_log" >&2
        return 1
    }
}
```

**Step 6: Make mocks executable**

```bash
chmod +x test/wkflw-ntfy/mocks/executable_*
```

**Step 7: Commit**

```bash
git add test/wkflw-ntfy/mocks/ test/wkflw-ntfy/helpers/
git commit -m "test(wkflw-ntfy): add test mocks and helpers

- Mock terminal-notifier, osascript, curl
- Test helpers for assertions
- Mock documentation

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 8: Implement macOS window operations

**Files:**
- Create: `private_dot_local/lib/wkflw-ntfy/macos/executable_wkflw-ntfy-macos-get-window`
- Create: `private_dot_local/lib/wkflw-ntfy/macos/executable_wkflw-ntfy-macos-focus`
- Create: `test/wkflw-ntfy/unit/test_macos_window.bats`

**Step 1: Write failing test**

File: `test/wkflw-ntfy/unit/test_macos_window.bats`

```bash
#!/usr/bin/env bats

load '../helpers/test_helpers'

setup() {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR"
    export WKFLW_NTFY_DEBUG=0
    setup_mocks
    export PATH="$PWD/private_dot_local/lib/wkflw-ntfy/macos:$PWD/private_dot_local/lib/wkflw-ntfy/core:$PATH"
}

@test "macos-get-window calls osascript and returns window ID" {
    result=$(wkflw-ntfy-macos-get-window)

    assert_mock_called "osascript"
    [[ "$result" == "window id 12345" ]]
}

@test "macos-focus calls osascript with window ID" {
    wkflw-ntfy-macos-focus "window id 12345"

    assert_mock_called "osascript"
    assert_file_contains "$MOCK_LOG_DIR/osascript.log" "12345"
}

@test "macos-get-window handles AppleScript failure gracefully" {
    # Remove mock to simulate failure
    export PATH="$PWD/private_dot_local/lib/wkflw-ntfy/macos:$PWD/private_dot_local/lib/wkflw-ntfy/core:$PATH"

    run wkflw-ntfy-macos-get-window
    [ "$status" -ne 0 ]
}
```

**Step 2: Run test to verify it fails**

```bash
bats test/wkflw-ntfy/unit/test_macos_window.bats
```

Expected: FAIL with command not found.

**Step 3: Implement macos-get-window**

File: `private_dot_local/lib/wkflw-ntfy/macos/executable_wkflw-ntfy-macos-get-window`

```bash
#!/usr/bin/env bash
# wkflw-ntfy-macos-get-window: Get iTerm window ID via AppleScript
#
# Usage: wkflw-ntfy-macos-get-window
#
# Outputs: window ID string (e.g., "window id 12345")
# Exit codes:
# - 0: Success
# - 1: AppleScript error or iTerm not running

set -euo pipefail

# Load config and logging
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../core/wkflw-ntfy-config"

# Query iTerm for current window ID
if ! window_id=$(osascript -e 'tell application "iTerm2" to id of current window' 2>/dev/null); then
    "$SCRIPT_DIR/../core/wkflw-ntfy-log" warning "macos-get-window" "Failed to get iTerm window ID"
    exit 1
fi

"$SCRIPT_DIR/../core/wkflw-ntfy-log" debug "macos-get-window" "Got window ID: $window_id"
echo "$window_id"
```

**Step 4: Implement macos-focus**

File: `private_dot_local/lib/wkflw-ntfy/macos/executable_wkflw-ntfy-macos-focus`

```bash
#!/usr/bin/env bash
# wkflw-ntfy-macos-focus: Focus iTerm window by ID using AppleScript
#
# Usage: wkflw-ntfy-macos-focus <window-id>
#   window-id: Window ID string from macos-get-window (e.g., "window id 12345")

set -euo pipefail

# Load config and logging
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../core/wkflw-ntfy-config"

window_id="${1:-}"

if [[ -z "$window_id" ]]; then
    echo "Usage: wkflw-ntfy-macos-focus <window-id>" >&2
    exit 1
fi

# Focus window via AppleScript
if osascript -e "tell application \"iTerm2\" to select $window_id" 2>/dev/null; then
    "$SCRIPT_DIR/../core/wkflw-ntfy-log" debug "macos-focus" "Focused window: $window_id"
else
    "$SCRIPT_DIR/../core/wkflw-ntfy-log" warning "macos-focus" "Failed to focus window: $window_id"
    exit 1
fi
```

**Step 5: Make executables**

```bash
chmod +x private_dot_local/lib/wkflw-ntfy/macos/executable_wkflw-ntfy-macos-*
```

**Step 6: Run test to verify it passes**

```bash
bats test/wkflw-ntfy/unit/test_macos_window.bats
```

Expected: All tests PASS.

**Step 7: Commit**

```bash
git add private_dot_local/lib/wkflw-ntfy/macos/ test/wkflw-ntfy/unit/test_macos_window.bats
git commit -m "feat(wkflw-ntfy): add macOS window operations

- Get iTerm window ID via AppleScript
- Focus window by ID (triggers space switching)
- Graceful fallback on AppleScript errors
- Add comprehensive unit tests

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 9: Implement ntfy push notifications

**Files:**
- Create: `private_dot_local/lib/wkflw-ntfy/push/executable_wkflw-ntfy-push`
- Create: `test/wkflw-ntfy/unit/test_push.bats`

**Step 1: Write failing test**

File: `test/wkflw-ntfy/unit/test_push.bats`

```bash
#!/usr/bin/env bats

load '../helpers/test_helpers'

setup() {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR"
    export WKFLW_NTFY_DEBUG=0
    export WKFLW_NTFY_TOPIC="test-topic-12345"
    export WKFLW_NTFY_SERVER="https://ntfy.sh"
    setup_mocks
    export PATH="$PWD/private_dot_local/lib/wkflw-ntfy/push:$PWD/private_dot_local/lib/wkflw-ntfy/core:$PATH"
}

@test "push sends notification via curl to ntfy server" {
    wkflw-ntfy-push "Test Title" "Test body message"

    assert_mock_called "curl"
    assert_file_contains "$MOCK_LOG_DIR/curl.log" "https://ntfy.sh/test-topic-12345"
    assert_file_contains "$MOCK_LOG_DIR/curl.log" "-X POST"
}

@test "push includes title and body in request" {
    wkflw-ntfy-push "My Title" "My body"

    assert_file_contains "$MOCK_LOG_DIR/curl.log" "My Title"
    assert_file_contains "$MOCK_LOG_DIR/curl.log" "My body"
}

@test "push handles missing topic gracefully" {
    unset WKFLW_NTFY_TOPIC

    run wkflw-ntfy-push "Title" "Body"
    [ "$status" -ne 0 ]
}
```

**Step 2: Run test to verify it fails**

```bash
bats test/wkflw-ntfy/unit/test_push.bats
```

Expected: FAIL with command not found.

**Step 3: Implement ntfy push**

File: `private_dot_local/lib/wkflw-ntfy/push/executable_wkflw-ntfy-push`

```bash
#!/usr/bin/env bash
# wkflw-ntfy-push: Send mobile push notification via ntfy
#
# Usage: wkflw-ntfy-push <title> <body>

set -euo pipefail

# Load config and logging
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../core/wkflw-ntfy-config"

title="${1:-}"
body="${2:-}"

if [[ -z "$title" || -z "$body" ]]; then
    echo "Usage: wkflw-ntfy-push <title> <body>" >&2
    exit 1
fi

if [[ -z "${WKFLW_NTFY_TOPIC:-}" ]]; then
    "$SCRIPT_DIR/../core/wkflw-ntfy-log" error "push" "WKFLW_NTFY_TOPIC not set"
    exit 1
fi

if ! command -v curl &>/dev/null; then
    "$SCRIPT_DIR/../core/wkflw-ntfy-log" warning "push" "curl not found, cannot send push notification"
    exit 1
fi

# Send notification via ntfy
url="$WKFLW_NTFY_SERVER/$WKFLW_NTFY_TOPIC"

if curl -X POST "$url" \
    -H "Title: $title" \
    -d "$body" \
    --silent --show-error --fail \
    >/dev/null 2>&1; then
    "$SCRIPT_DIR/../core/wkflw-ntfy-log" debug "push" "Sent push notification: $title"
else
    "$SCRIPT_DIR/../core/wkflw-ntfy-log" warning "push" "Failed to send push notification (server unreachable?)"
    exit 1
fi
```

**Step 4: Make executable**

```bash
chmod +x private_dot_local/lib/wkflw-ntfy/push/executable_wkflw-ntfy-push
```

**Step 5: Run test to verify it passes**

```bash
bats test/wkflw-ntfy/unit/test_push.bats
```

Expected: All tests PASS.

**Step 6: Commit**

```bash
git add private_dot_local/lib/wkflw-ntfy/push/ test/wkflw-ntfy/unit/test_push.bats
git commit -m "feat(wkflw-ntfy): add ntfy push notifications

- Send push notifications via curl
- Validate topic and curl availability
- Graceful fallback on failure
- Add comprehensive unit tests

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 10: Implement escalation worker

**Files:**
- Create: `private_dot_local/lib/wkflw-ntfy/escalation/executable_wkflw-ntfy-escalate-worker`
- Create: `private_dot_local/lib/wkflw-ntfy/escalation/executable_wkflw-ntfy-escalate-spawn`
- Create: `test/wkflw-ntfy/unit/test_escalate.bats`

**Step 1: Write failing test**

File: `test/wkflw-ntfy/unit/test_escalate.bats`

```bash
#!/usr/bin/env bats

load '../helpers/test_helpers'

setup() {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR/markers"
    export WKFLW_NTFY_DEBUG=0
    export WKFLW_NTFY_TOPIC="test-topic"
    export WKFLW_NTFY_ESCALATION_DELAY=0  # No delay in tests
    setup_mocks
    export PATH="$PWD/private_dot_local/lib/wkflw-ntfy/escalation:$PWD/private_dot_local/lib/wkflw-ntfy/marker:$PWD/private_dot_local/lib/wkflw-ntfy/push:$PWD/private_dot_local/lib/wkflw-ntfy/core:$PATH"
}

@test "escalate-worker sends push if marker still exists" {
    marker_path=$(wkflw-ntfy-marker-create "test" "/test")

    wkflw-ntfy-escalate-worker "$marker_path" "Test Title" "Test body"

    # Marker should be deleted
    [ ! -f "$marker_path" ]

    # Push should be sent
    assert_mock_called "curl"
}

@test "escalate-worker exits silently if marker deleted (user acknowledged)" {
    marker_path="$WKFLW_NTFY_STATE_DIR/markers/nonexistent-marker"

    wkflw-ntfy-escalate-worker "$marker_path" "Test Title" "Test body"

    # Push should NOT be sent
    assert_mock_not_called "curl"
}

@test "escalate-spawn starts background worker" {
    marker_path=$(wkflw-ntfy-marker-create "test" "/test")

    # Spawn worker (should return immediately)
    wkflw-ntfy-escalate-spawn "$marker_path" "Test Title" "Test body"

    # Give worker a moment to run (delay is 0 in tests)
    sleep 1

    # Marker should be gone (worker ran)
    [ ! -f "$marker_path" ]

    # Push should be sent
    assert_mock_called "curl"
}
```

**Step 2: Run test to verify it fails**

```bash
bats test/wkflw-ntfy/unit/test_escalate.bats
```

Expected: FAIL with command not found.

**Step 3: Implement escalate-worker**

File: `private_dot_local/lib/wkflw-ntfy/escalation/executable_wkflw-ntfy-escalate-worker`

```bash
#!/usr/bin/env bash
# wkflw-ntfy-escalate-worker: Background worker for progressive escalation
#
# Usage: wkflw-ntfy-escalate-worker <marker-file-path> <title> <body>
#
# Waits for escalation delay, then checks if marker still exists.
# If marker exists: deletes it (atomic claim) and sends push notification.
# If marker gone: user acknowledged desktop notification, exit silently.

set -euo pipefail

# Load config and logging
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../core/wkflw-ntfy-config"

marker_file="${1:-}"
title="${2:-}"
body="${3:-}"

if [[ -z "$marker_file" || -z "$title" || -z "$body" ]]; then
    echo "Usage: wkflw-ntfy-escalate-worker <marker-file-path> <title> <body>" >&2
    exit 1
fi

# Wait for escalation delay
delay="${WKFLW_NTFY_ESCALATION_DELAY:-120}"
"$SCRIPT_DIR/../core/wkflw-ntfy-log" debug "escalate-worker" "Waiting ${delay}s before checking marker"
sleep "$delay"

# Check if marker still exists
if ! "$SCRIPT_DIR/../marker/wkflw-ntfy-marker-check" "$marker_file"; then
    "$SCRIPT_DIR/../core/wkflw-ntfy-log" debug "escalate-worker" "Marker deleted, user acknowledged notification"
    exit 0
fi

# Marker still exists: delete it (atomic claim) and send push
"$SCRIPT_DIR/../marker/wkflw-ntfy-marker-delete" "$marker_file"
"$SCRIPT_DIR/../core/wkflw-ntfy-log" debug "escalate-worker" "Escalating to push notification"
"$SCRIPT_DIR/../push/wkflw-ntfy-push" "$title" "$body"
```

**Step 4: Implement escalate-spawn**

File: `private_dot_local/lib/wkflw-ntfy/escalation/executable_wkflw-ntfy-escalate-spawn`

```bash
#!/usr/bin/env bash
# wkflw-ntfy-escalate-spawn: Spawn background escalation worker
#
# Usage: wkflw-ntfy-escalate-spawn <marker-file-path> <title> <body>
#
# Spawns escalate-worker as detached background process.

set -euo pipefail

# Load config and logging
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../core/wkflw-ntfy-config"

marker_file="${1:-}"
title="${2:-}"
body="${3:-}"

if [[ -z "$marker_file" || -z "$title" || -z "$body" ]]; then
    echo "Usage: wkflw-ntfy-escalate-spawn <marker-file-path> <title> <body>" >&2
    exit 1
fi

# Spawn worker in background (detached)
nohup "$SCRIPT_DIR/wkflw-ntfy-escalate-worker" "$marker_file" "$title" "$body" \
    >/dev/null 2>&1 &

"$SCRIPT_DIR/../core/wkflw-ntfy-log" debug "escalate-spawn" "Spawned escalation worker (PID: $!)"
```

**Step 5: Make executables**

```bash
chmod +x private_dot_local/lib/wkflw-ntfy/escalation/executable_wkflw-ntfy-escalate-*
```

**Step 6: Run test to verify it passes**

```bash
bats test/wkflw-ntfy/unit/test_escalate.bats
```

Expected: All tests PASS.

**Step 7: Commit**

```bash
git add private_dot_local/lib/wkflw-ntfy/escalation/ test/wkflw-ntfy/unit/test_escalate.bats
git commit -m "feat(wkflw-ntfy): add progressive escalation worker

- Background worker waits for delay, checks marker
- Atomic marker deletion prevents race conditions
- Spawn detached background process
- Add comprehensive unit tests

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 11: Implement macOS notification sending and callback

**Files:**
- Create: `private_dot_local/lib/wkflw-ntfy/macos/executable_wkflw-ntfy-macos-send`
- Create: `private_dot_local/lib/wkflw-ntfy/macos/executable_wkflw-ntfy-macos-callback`
- Create: `test/wkflw-ntfy/unit/test_macos_send.bats`

**Step 1: Write failing test**

File: `test/wkflw-ntfy/unit/test_macos_send.bats`

```bash
#!/usr/bin/env bats

load '../helpers/test_helpers'

setup() {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR"
    export WKFLW_NTFY_DEBUG=0
    setup_mocks
    export PATH="$PWD/private_dot_local/lib/wkflw-ntfy/macos:$PWD/private_dot_local/lib/wkflw-ntfy/marker:$PWD/private_dot_local/lib/wkflw-ntfy/core:$PATH"
}

@test "macos-send calls terminal-notifier with title and body" {
    wkflw-ntfy-macos-send "Test Title" "Test body"

    assert_mock_called "terminal-notifier"
    assert_file_contains "$MOCK_LOG_DIR/terminal-notifier.log" "Test Title"
    assert_file_contains "$MOCK_LOG_DIR/terminal-notifier.log" "Test body"
}

@test "macos-send includes callback when provided" {
    callback_script="$BATS_TEST_TMPDIR/callback.sh"
    touch "$callback_script"

    wkflw-ntfy-macos-send "Title" "Body" "$callback_script"

    assert_file_contains "$MOCK_LOG_DIR/terminal-notifier.log" "-execute"
    assert_file_contains "$MOCK_LOG_DIR/terminal-notifier.log" "callback.sh"
}

@test "macos-callback deletes marker and focuses window" {
    marker_path=$(wkflw-ntfy-marker-create "test" "/test")
    [ -f "$marker_path" ]

    wkflw-ntfy-macos-callback "$marker_path" "window id 12345"

    # Marker should be deleted
    [ ! -f "$marker_path" ]

    # Window focus should be called
    assert_mock_called "osascript"
    assert_file_contains "$MOCK_LOG_DIR/osascript.log" "12345"
}
```

**Step 2: Run test to verify it fails**

```bash
bats test/wkflw-ntfy/unit/test_macos_send.bats
```

Expected: FAIL with command not found.

**Step 3: Implement macos-send**

File: `private_dot_local/lib/wkflw-ntfy/macos/executable_wkflw-ntfy-macos-send`

```bash
#!/usr/bin/env bash
# wkflw-ntfy-macos-send: Send desktop notification via terminal-notifier
#
# Usage: wkflw-ntfy-macos-send <title> <body> [callback-script]

set -euo pipefail

# Load config and logging
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../core/wkflw-ntfy-config"

title="${1:-}"
body="${2:-}"
callback_script="${3:-}"

if [[ -z "$title" || -z "$body" ]]; then
    echo "Usage: wkflw-ntfy-macos-send <title> <body> [callback-script]" >&2
    exit 1
fi

if ! command -v terminal-notifier &>/dev/null; then
    "$SCRIPT_DIR/../core/wkflw-ntfy-log" warning "macos-send" "terminal-notifier not found, falling back to push"
    "$SCRIPT_DIR/../push/wkflw-ntfy-push" "$title" "$body"
    exit 0
fi

# Build terminal-notifier command
cmd=(terminal-notifier -title "$title" -message "$body")

# Add callback if provided
if [[ -n "$callback_script" ]]; then
    cmd+=(-execute "bash '$callback_script'")
fi

# Send notification
"${cmd[@]}"
"$SCRIPT_DIR/../core/wkflw-ntfy-log" debug "macos-send" "Sent desktop notification: $title"
```

**Step 4: Implement macos-callback**

File: `private_dot_local/lib/wkflw-ntfy/macos/executable_wkflw-ntfy-macos-callback`

```bash
#!/usr/bin/env bash
# wkflw-ntfy-macos-callback: Callback invoked when notification clicked
#
# Usage: wkflw-ntfy-macos-callback <marker-file-path> [window-id]

set -euo pipefail

# Load config and logging
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../core/wkflw-ntfy-config"

marker_file="${1:-}"
window_id="${2:-}"

if [[ -z "$marker_file" ]]; then
    echo "Usage: wkflw-ntfy-macos-callback <marker-file-path> [window-id]" >&2
    exit 1
fi

# Delete marker (atomic claim - prevents escalation worker from sending push)
"$SCRIPT_DIR/../marker/wkflw-ntfy-marker-delete" "$marker_file"
"$SCRIPT_DIR/../core/wkflw-ntfy-log" debug "macos-callback" "User acknowledged notification"

# Focus window if ID provided
if [[ -n "$window_id" ]]; then
    "$SCRIPT_DIR/wkflw-ntfy-macos-focus" "$window_id"
fi
```

**Step 5: Make executables**

```bash
chmod +x private_dot_local/lib/wkflw-ntfy/macos/executable_wkflw-ntfy-macos-send
chmod +x private_dot_local/lib/wkflw-ntfy/macos/executable_wkflw-ntfy-macos-callback
```

**Step 6: Run test to verify it passes**

```bash
bats test/wkflw-ntfy/unit/test_macos_send.bats
```

Expected: All tests PASS.

**Step 7: Commit**

```bash
git add private_dot_local/lib/wkflw-ntfy/macos/ test/wkflw-ntfy/unit/test_macos_send.bats
git commit -m "feat(wkflw-ntfy): add macOS notification sending and callback

- Send desktop notifications via terminal-notifier
- Click callback deletes marker and focuses window
- Graceful fallback to push if terminal-notifier missing
- Add comprehensive unit tests

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 12: Implement Linux notification sending

**Files:**
- Create: `private_dot_local/lib/wkflw-ntfy/linux/executable_wkflw-ntfy-linux-send`
- Create: `test/wkflw-ntfy/mocks/executable_notify-send`
- Create: `test/wkflw-ntfy/unit/test_linux_send.bats`

**Step 1: Create mock for notify-send**

File: `test/wkflw-ntfy/mocks/executable_notify-send`

```bash
#!/usr/bin/env bash
# Mock notify-send for testing
# Logs invocations

MOCK_LOG_DIR="${MOCK_LOG_DIR:-/tmp}"
MOCK_LOG="$MOCK_LOG_DIR/notify-send.log"

echo "$(date +%Y-%m-%dT%H:%M:%S) $0 $*" >> "$MOCK_LOG"

exit 0
```

**Step 2: Make mock executable**

```bash
chmod +x test/wkflw-ntfy/mocks/executable_notify-send
```

**Step 3: Write failing test**

File: `test/wkflw-ntfy/unit/test_linux_send.bats`

```bash
#!/usr/bin/env bats

load '../helpers/test_helpers'

setup() {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR"
    export WKFLW_NTFY_DEBUG=0
    setup_mocks
    export PATH="$PWD/private_dot_local/lib/wkflw-ntfy/linux:$PWD/private_dot_local/lib/wkflw-ntfy/push:$PWD/private_dot_local/lib/wkflw-ntfy/core:$PATH"
}

@test "linux-send calls notify-send with title and body" {
    wkflw-ntfy-linux-send "Test Title" "Test body"

    assert_mock_called "notify-send"
    assert_file_contains "$MOCK_LOG_DIR/notify-send.log" "Test Title"
    assert_file_contains "$MOCK_LOG_DIR/notify-send.log" "Test body"
}

@test "linux-send falls back to push if notify-send missing" {
    export WKFLW_NTFY_TOPIC="test-topic"
    # Remove mock from PATH
    export PATH="$PWD/private_dot_local/lib/wkflw-ntfy/linux:$PWD/private_dot_local/lib/wkflw-ntfy/push:$PWD/private_dot_local/lib/wkflw-ntfy/core:$PATH"

    wkflw-ntfy-linux-send "Title" "Body"

    # Should call curl (push) as fallback
    assert_mock_called "curl"
}
```

**Step 4: Run test to verify it fails**

```bash
bats test/wkflw-ntfy/unit/test_linux_send.bats
```

Expected: FAIL with command not found.

**Step 5: Implement linux-send**

File: `private_dot_local/lib/wkflw-ntfy/linux/executable_wkflw-ntfy-linux-send`

```bash
#!/usr/bin/env bash
# wkflw-ntfy-linux-send: Send desktop notification via notify-send
#
# Usage: wkflw-ntfy-linux-send <title> <body>

set -euo pipefail

# Load config and logging
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../core/wkflw-ntfy-config"

title="${1:-}"
body="${2:-}"

if [[ -z "$title" || -z "$body" ]]; then
    echo "Usage: wkflw-ntfy-linux-send <title> <body>" >&2
    exit 1
fi

if ! command -v notify-send &>/dev/null; then
    "$SCRIPT_DIR/../core/wkflw-ntfy-log" warning "linux-send" "notify-send not found, falling back to push"
    "$SCRIPT_DIR/../push/wkflw-ntfy-push" "$title" "$body"
    exit 0
fi

# Send notification
notify-send "$title" "$body"
"$SCRIPT_DIR/../core/wkflw-ntfy-log" debug "linux-send" "Sent desktop notification: $title"
```

**Step 6: Make executable**

```bash
chmod +x private_dot_local/lib/wkflw-ntfy/linux/executable_wkflw-ntfy-linux-send
```

**Step 7: Run test to verify it passes**

```bash
bats test/wkflw-ntfy/unit/test_linux_send.bats
```

Expected: All tests PASS.

**Step 8: Commit**

```bash
git add private_dot_local/lib/wkflw-ntfy/linux/ test/wkflw-ntfy/mocks/executable_notify-send test/wkflw-ntfy/unit/test_linux_send.bats
git commit -m "feat(wkflw-ntfy): add Linux notification sending

- Send desktop notifications via notify-send
- Graceful fallback to push if notify-send missing
- Add mock for notify-send
- Add comprehensive unit tests

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 3: Hook Integration

### Task 13: Implement Claude Code Stop hook

**Files:**
- Create: `private_dot_local/lib/wkflw-ntfy/hooks/executable_claude-stop.sh`
- Create: `test/wkflw-ntfy/integration/test_claude_stop_flow.bats`

**Step 1: Write failing integration test**

File: `test/wkflw-ntfy/integration/test_claude_stop_flow.bats`

```bash
#!/usr/bin/env bats

load '../helpers/test_helpers'

setup() {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR/markers"
    export WKFLW_NTFY_DEBUG=0
    export WKFLW_NTFY_ESCALATION_DELAY=0  # No delay in tests
    export WKFLW_NTFY_TOPIC="test-topic"
    export TERM_PROGRAM="iTerm.app"  # Simulate iTerm
    setup_mocks
    export PATH="$PWD/private_dot_local/lib/wkflw-ntfy/hooks:$PWD/private_dot_local/lib/wkflw-ntfy/macos:$PWD/private_dot_local/lib/wkflw-ntfy/escalation:$PWD/private_dot_local/lib/wkflw-ntfy/marker:$PWD/private_dot_local/lib/wkflw-ntfy/push:$PWD/private_dot_local/lib/wkflw-ntfy/core:$PATH"
}

@test "Claude Stop in iTerm triggers progressive escalation" {
    # Create mock hook JSON
    hook_json='{"hook_event_name":"Stop","cwd":"/test/project","transcript_path":"/tmp/transcript"}'

    echo "$hook_json" | claude-stop.sh

    # Desktop notification should be sent
    assert_mock_called "terminal-notifier"

    # Give worker time to run (delay=0, but need a moment)
    sleep 1

    # Push should be sent (escalation)
    assert_mock_called "curl"
}

@test "Claude Stop in no-GUI session sends push only" {
    unset TERM_PROGRAM
    unset DISPLAY

    hook_json='{"hook_event_name":"Stop","cwd":"/test/project","transcript_path":"/tmp/transcript"}'

    echo "$hook_json" | claude-stop.sh

    # No desktop notification
    assert_mock_not_called "terminal-notifier"

    # Push should be sent
    assert_mock_called "curl"
}
```

**Step 2: Run test to verify it fails**

```bash
bats test/wkflw-ntfy/integration/test_claude_stop_flow.bats
```

Expected: FAIL with command not found.

**Step 3: Implement Claude Stop hook**

File: `private_dot_local/lib/wkflw-ntfy/hooks/executable_claude-stop.sh`

```bash
#!/usr/bin/env bash
# Claude Code Stop hook: Notify when Claude finishes a task
#
# Receives JSON via stdin with fields:
# - hook_event_name: "Stop"
# - cwd: Current working directory
# - transcript_path: Path to transcript file

set -euo pipefail

# Load config and logging
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../core/wkflw-ntfy-config"

# Read hook JSON from stdin
hook_data=$(cat)

if ! command -v jq &>/dev/null; then
    "$SCRIPT_DIR/../core/wkflw-ntfy-log" error "claude-stop" "jq not found, cannot parse hook data"
    exit 1
fi

# Extract fields
cwd=$(echo "$hook_data" | jq -r '.cwd // "unknown"')
dir_name=$(basename "$cwd")

# Notification content
title="Claude Code - Finished"
body="$dir_name: Task completed"

# Detect environment and choose strategy
env=$("$SCRIPT_DIR/../core/wkflw-ntfy-detect-env")
strategy=$("$SCRIPT_DIR/../core/wkflw-ntfy-decide-strategy" "$env" "claude-stop" "")

"$SCRIPT_DIR/../core/wkflw-ntfy-log" debug "claude-stop" "Environment: $env, Strategy: $strategy"

case "$strategy" in
    progressive)
        # Create marker for progressive escalation
        marker=$("$SCRIPT_DIR/../marker/wkflw-ntfy-marker-create" "claude-stop" "$cwd")

        # Get window ID (if iTerm)
        window_id=""
        if [[ "$env" == "iterm" ]]; then
            window_id=$("$SCRIPT_DIR/../macos/wkflw-ntfy-macos-get-window" || echo "")
        fi

        # Create callback script
        callback_script="$WKFLW_NTFY_STATE_DIR/callback-$$"
        cat > "$callback_script" <<EOF
#!/usr/bin/env bash
"$SCRIPT_DIR/../macos/wkflw-ntfy-macos-callback" "$marker" "$window_id"
EOF
        chmod +x "$callback_script"

        # Send desktop notification with callback
        "$SCRIPT_DIR/../macos/wkflw-ntfy-macos-send" "$title" "$body" "$callback_script"

        # Spawn escalation worker
        "$SCRIPT_DIR/../escalation/wkflw-ntfy-escalate-spawn" "$marker" "$title" "$body"
        ;;

    desktop-only)
        # Send desktop notification (no escalation)
        if [[ "$env" == "linux-gui" ]]; then
            "$SCRIPT_DIR/../linux/wkflw-ntfy-linux-send" "$title" "$body"
        else
            "$SCRIPT_DIR/../macos/wkflw-ntfy-macos-send" "$title" "$body"
        fi
        ;;

    push-only)
        # Send push notification
        "$SCRIPT_DIR/../push/wkflw-ntfy-push" "$title" "$body"
        ;;

    *)
        "$SCRIPT_DIR/../core/wkflw-ntfy-log" error "claude-stop" "Unknown strategy: $strategy"
        exit 1
        ;;
esac
```

**Step 4: Make executable**

```bash
chmod +x private_dot_local/lib/wkflw-ntfy/hooks/executable_claude-stop.sh
```

**Step 5: Run test to verify it passes**

```bash
bats test/wkflw-ntfy/integration/test_claude_stop_flow.bats
```

Expected: All tests PASS.

**Step 6: Commit**

```bash
git add private_dot_local/lib/wkflw-ntfy/hooks/executable_claude-stop.sh test/wkflw-ntfy/integration/test_claude_stop_flow.bats
git commit -m "feat(wkflw-ntfy): add Claude Code Stop hook integration

- Parse hook JSON with jq
- Detect environment and choose strategy
- Progressive escalation for iTerm
- Desktop-only for macOS/Linux GUI
- Push-only for no-GUI sessions
- Add integration tests

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 14: Implement Claude Code Notification hook

**Files:**
- Create: `private_dot_local/lib/wkflw-ntfy/hooks/executable_claude-notification.sh`
- Create: `test/wkflw-ntfy/integration/test_claude_notification_flow.bats`

**Step 1: Write failing integration test**

File: `test/wkflw-ntfy/integration/test_claude_notification_flow.bats`

```bash
#!/usr/bin/env bats

load '../helpers/test_helpers'

setup() {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR/markers"
    export WKFLW_NTFY_DEBUG=0
    export WKFLW_NTFY_ESCALATION_DELAY=0
    export WKFLW_NTFY_TOPIC="test-topic"
    export TERM_PROGRAM="iTerm.app"
    setup_mocks
    export PATH="$PWD/private_dot_local/lib/wkflw-ntfy/hooks:$PWD/private_dot_local/lib/wkflw-ntfy/macos:$PWD/private_dot_local/lib/wkflw-ntfy/escalation:$PWD/private_dot_local/lib/wkflw-ntfy/marker:$PWD/private_dot_local/lib/wkflw-ntfy/push:$PWD/private_dot_local/lib/wkflw-ntfy/core:$PATH"
}

@test "Claude Notification permission_prompt in iTerm sends desktop only" {
    hook_json='{"hook_event_name":"Notification","notification_type":"permission_prompt","message":"Claude needs permission","cwd":"/test"}'

    echo "$hook_json" | claude-notification.sh

    # Desktop notification should be sent
    assert_mock_called "terminal-notifier"

    # Give worker time (should NOT run for permission prompts)
    sleep 1

    # Push should NOT be sent (no escalation for permission prompts)
    assert_mock_not_called "curl"
}

@test "Claude Notification idle_input in iTerm triggers progressive escalation" {
    hook_json='{"hook_event_name":"Notification","notification_type":"idle_input","message":"Waiting for input","cwd":"/test"}'

    echo "$hook_json" | claude-notification.sh

    # Desktop notification should be sent
    assert_mock_called "terminal-notifier"

    # Give worker time
    sleep 1

    # Push should be sent (escalation for input needed)
    assert_mock_called "curl"
}
```

**Step 2: Run test to verify it fails**

```bash
bats test/wkflw-ntfy/integration/test_claude_notification_flow.bats
```

Expected: FAIL with command not found.

**Step 3: Implement Claude Notification hook**

File: `private_dot_local/lib/wkflw-ntfy/hooks/executable_claude-notification.sh`

```bash
#!/usr/bin/env bash
# Claude Code Notification hook: Notify when Claude needs attention
#
# Receives JSON via stdin with fields:
# - hook_event_name: "Notification"
# - notification_type: "permission_prompt" or "idle_input"
# - message: Notification message
# - cwd: Current working directory

set -euo pipefail

# Load config and logging
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../core/wkflw-ntfy-config"

# Read hook JSON from stdin
hook_data=$(cat)

if ! command -v jq &>/dev/null; then
    "$SCRIPT_DIR/../core/wkflw-ntfy-log" error "claude-notification" "jq not found, cannot parse hook data"
    exit 1
fi

# Extract fields
notification_type=$(echo "$hook_data" | jq -r '.notification_type // "unknown"')
message=$(echo "$hook_data" | jq -r '.message // "Claude needs attention"')
cwd=$(echo "$hook_data" | jq -r '.cwd // "unknown"')
dir_name=$(basename "$cwd")

# Notification content based on type
case "$notification_type" in
    permission_prompt)
        title="Claude Code - Permission Needed"
        body="$message"
        ;;
    idle_input|*)
        title="Claude Code - Input Needed"
        body="$dir_name: $message"
        ;;
esac

# Detect environment and choose strategy
env=$("$SCRIPT_DIR/../core/wkflw-ntfy-detect-env")
strategy=$("$SCRIPT_DIR/../core/wkflw-ntfy-decide-strategy" "$env" "claude-notification" "$notification_type")

"$SCRIPT_DIR/../core/wkflw-ntfy-log" debug "claude-notification" "Type: $notification_type, Environment: $env, Strategy: $strategy"

case "$strategy" in
    progressive)
        # Create marker for progressive escalation
        marker=$("$SCRIPT_DIR/../marker/wkflw-ntfy-marker-create" "claude-notification" "$cwd")

        # Get window ID (if iTerm)
        window_id=""
        if [[ "$env" == "iterm" ]]; then
            window_id=$("$SCRIPT_DIR/../macos/wkflw-ntfy-macos-get-window" || echo "")
        fi

        # Create callback script
        callback_script="$WKFLW_NTFY_STATE_DIR/callback-$$"
        cat > "$callback_script" <<EOF
#!/usr/bin/env bash
"$SCRIPT_DIR/../macos/wkflw-ntfy-macos-callback" "$marker" "$window_id"
EOF
        chmod +x "$callback_script"

        # Send desktop notification with callback
        "$SCRIPT_DIR/../macos/wkflw-ntfy-macos-send" "$title" "$body" "$callback_script"

        # Spawn escalation worker
        "$SCRIPT_DIR/../escalation/wkflw-ntfy-escalate-spawn" "$marker" "$title" "$body"
        ;;

    desktop-only)
        # Send desktop notification (no escalation)
        if [[ "$env" == "linux-gui" ]]; then
            "$SCRIPT_DIR/../linux/wkflw-ntfy-linux-send" "$title" "$body"
        else
            "$SCRIPT_DIR/../macos/wkflw-ntfy-macos-send" "$title" "$body"
        fi
        ;;

    push-only)
        # Send push notification
        "$SCRIPT_DIR/../push/wkflw-ntfy-push" "$title" "$body"
        ;;

    *)
        "$SCRIPT_DIR/../core/wkflw-ntfy-log" error "claude-notification" "Unknown strategy: $strategy"
        exit 1
        ;;
esac
```

**Step 4: Make executable**

```bash
chmod +x private_dot_local/lib/wkflw-ntfy/hooks/executable_claude-notification.sh
```

**Step 5: Run test to verify it passes**

```bash
bats test/wkflw-ntfy/integration/test_claude_notification_flow.bats
```

Expected: All tests PASS.

**Step 6: Commit**

```bash
git add private_dot_local/lib/wkflw-ntfy/hooks/executable_claude-notification.sh test/wkflw-ntfy/integration/test_claude_notification_flow.bats
git commit -m "feat(wkflw-ntfy): add Claude Code Notification hook integration

- Handle permission_prompt (desktop-only) vs idle_input (progressive)
- Parse notification type from hook JSON
- Different titles based on notification type
- Add integration tests

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 15: Implement nushell hooks

**Files:**
- Create: `private_dot_local/lib/wkflw-ntfy/hooks/nushell.nu`
- Create: `test/wkflw-ntfy/integration/test_nushell_flow.bats`

**Step 1: Write failing integration test**

File: `test/wkflw-ntfy/integration/test_nushell_flow.bats`

```bash
#!/usr/bin/env bats

load '../helpers/test_helpers'

setup() {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR/markers"
    export WKFLW_NTFY_DEBUG=0
    export WKFLW_NTFY_ESCALATION_DELAY=0
    export WKFLW_NTFY_NUSHELL_THRESHOLD=90
    export WKFLW_NTFY_TOPIC="test-topic"
    export TERM_PROGRAM="iTerm.app"
    setup_mocks
}

@test "nushell command over threshold triggers notification" {
    # Simulate nushell calling the hook script
    bash private_dot_local/lib/wkflw-ntfy/hooks/nushell-handler.sh "npm test" "120" "0" "/test/project"

    # Desktop notification should be sent
    assert_mock_called "terminal-notifier"

    sleep 1

    # Push should be sent (escalation)
    assert_mock_called "curl"
}

@test "nushell command under threshold does not notify" {
    bash private_dot_local/lib/wkflw-ntfy/hooks/nushell-handler.sh "npm test" "60" "0" "/test/project"

    # No notifications
    assert_mock_not_called "terminal-notifier"
    assert_mock_not_called "curl"
}

@test "nushell filtered command does not notify" {
    bash private_dot_local/lib/wkflw-ntfy/hooks/nushell-handler.sh "hx file.txt" "120" "0" "/test/project"

    # No notifications (hx is filtered)
    assert_mock_not_called "terminal-notifier"
    assert_mock_not_called "curl"
}
```

**Step 2: Run test to verify it fails**

```bash
bats test/wkflw-ntfy/integration/test_nushell_flow.bats
```

Expected: FAIL with file not found.

**Step 3: Implement nushell hook handler (bash script called by nushell)**

File: `private_dot_local/lib/wkflw-ntfy/hooks/executable_nushell-handler.sh`

```bash
#!/usr/bin/env bash
# Nushell hook handler: Notify when long-running command completes
#
# Called by nushell with args:
# $1: command
# $2: duration (seconds)
# $3: exit code
# $4: cwd

set -euo pipefail

# Load config and logging
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../core/wkflw-ntfy-config"

cmd="${1:-}"
duration="${2:-0}"
exit_code="${3:-0}"
cwd="${4:-unknown}"

# Check threshold
threshold="${WKFLW_NTFY_NUSHELL_THRESHOLD:-90}"
if (( duration < threshold )); then
    "$SCRIPT_DIR/../core/wkflw-ntfy-log" debug "nushell" "Command duration ${duration}s below threshold ${threshold}s"
    exit 0
fi

# Filter interactive commands
filtered_cmds=("hx" "vim" "nvim" "nano" "emacs" "bash" "zsh" "fish" "nu" "htop" "top" "less" "more")
cmd_base=$(echo "$cmd" | awk '{print $1}')
for filtered in "${filtered_cmds[@]}"; do
    if [[ "$cmd_base" == "$filtered" ]]; then
        "$SCRIPT_DIR/../core/wkflw-ntfy-log" debug "nushell" "Command $cmd_base is filtered"
        exit 0
    fi
done

# Notification content
dir_name=$(basename "$cwd")
duration_min=$((duration / 60))
status="succeeded"
if [[ "$exit_code" != "0" ]]; then
    status="failed"
fi

title="Command Complete"
body="$dir_name: $cmd ($duration_min min, $status)"

# Detect environment and choose strategy
env=$("$SCRIPT_DIR/../core/wkflw-ntfy-detect-env")
strategy=$("$SCRIPT_DIR/../core/wkflw-ntfy-decide-strategy" "$env" "nushell" "")

"$SCRIPT_DIR/../core/wkflw-ntfy-log" debug "nushell" "Command: $cmd, Duration: ${duration}s, Environment: $env, Strategy: $strategy"

case "$strategy" in
    progressive)
        # Create marker for progressive escalation
        marker=$("$SCRIPT_DIR/../marker/wkflw-ntfy-marker-create" "nushell" "$cwd")

        # Get window ID (if iTerm)
        window_id=""
        if [[ "$env" == "iterm" ]]; then
            window_id=$("$SCRIPT_DIR/../macos/wkflw-ntfy-macos-get-window" || echo "")
        fi

        # Create callback script
        callback_script="$WKFLW_NTFY_STATE_DIR/callback-$$"
        cat > "$callback_script" <<EOF
#!/usr/bin/env bash
"$SCRIPT_DIR/../macos/wkflw-ntfy-macos-callback" "$marker" "$window_id"
EOF
        chmod +x "$callback_script"

        # Send desktop notification with callback
        "$SCRIPT_DIR/../macos/wkflw-ntfy-macos-send" "$title" "$body" "$callback_script"

        # Spawn escalation worker
        "$SCRIPT_DIR/../escalation/wkflw-ntfy-escalate-spawn" "$marker" "$title" "$body"
        ;;

    desktop-only)
        # Send desktop notification (no escalation)
        if [[ "$env" == "linux-gui" ]]; then
            "$SCRIPT_DIR/../linux/wkflw-ntfy-linux-send" "$title" "$body"
        else
            "$SCRIPT_DIR/../macos/wkflw-ntfy-macos-send" "$title" "$body"
        fi
        ;;

    push-only)
        # Send push notification
        "$SCRIPT_DIR/../push/wkflw-ntfy-push" "$title" "$body"
        ;;

    *)
        "$SCRIPT_DIR/../core/wkflw-ntfy-log" error "nushell" "Unknown strategy: $strategy"
        exit 1
        ;;
esac
```

**Step 4: Implement nushell hook functions**

File: `private_dot_local/lib/wkflw-ntfy/hooks/nushell.nu`

```nushell
# Nushell hooks for workflow notifications
# Source this file in config.nu or env.nu

# Pre-execution hook: capture command start time
export def --env ntfy-pre-execution-hook [] {
    $env.NTFY_CMD_START = (date now | format date "%s" | into int)
    $env.NTFY_CMD = (commandline)
    $env.NTFY_CWD = (pwd)
}

# Pre-prompt hook: check command duration and notify
export def --env ntfy-pre-prompt-hook [] {
    # Check if command tracking vars exist
    if ($env.NTFY_CMD_START? | is-empty) {
        return
    }

    let end_time = (date now | format date "%s" | into int)
    let duration = ($end_time - $env.NTFY_CMD_START)
    let exit_code = $env.LAST_EXIT_CODE
    let cmd = $env.NTFY_CMD
    let cwd = $env.NTFY_CWD

    # Call bash handler script
    let handler_path = ($env.HOME | path join ".local" "lib" "wkflw-ntfy" "hooks" "nushell-handler.sh")
    if ($handler_path | path exists) {
        ^bash $handler_path $cmd $"($duration)" $"($exit_code)" $cwd | complete | ignore
    }

    # Clear tracking vars
    hide-env NTFY_CMD_START
    hide-env NTFY_CMD
    hide-env NTFY_CWD
}
```

**Step 5: Make executable**

```bash
chmod +x private_dot_local/lib/wkflw-ntfy/hooks/executable_nushell-handler.sh
```

**Step 6: Run test to verify it passes**

```bash
bats test/wkflw-ntfy/integration/test_nushell_flow.bats
```

Expected: All tests PASS.

**Step 7: Commit**

```bash
git add private_dot_local/lib/wkflw-ntfy/hooks/ test/wkflw-ntfy/integration/test_nushell_flow.bats
git commit -m "feat(wkflw-ntfy): add nushell hook integration

- Bash handler script for notification logic
- Nushell hook functions (pre-execution, pre-prompt)
- Command duration tracking and filtering
- Add integration tests

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 4: Configuration Integration

### Task 16: Create chezmoi templates for hook configuration

**Files:**
- Modify: `dot_claude/settings.json.tmpl` (add hooks)
- Create: `run_once_after_wkflw-ntfy-generate-topic.sh.tmpl`

**Step 1: Draft hook configuration for Claude Code settings**

This task will add hook configuration to the existing `dot_claude/settings.json.tmpl` file.

Add to hooks section:

```json
{
  "hooks": {
    "Stop": [
      {
        "type": "command",
        "command": "~/.local/lib/wkflw-ntfy/hooks/claude-stop.sh"
      }
    ],
    "Notification": [
      {
        "type": "command",
        "command": "~/.local/lib/wkflw-ntfy/hooks/claude-notification.sh"
      }
    ]
  }
}
```

**Step 2: Create ntfy topic generator script**

File: `run_once_after_wkflw-ntfy-generate-topic.sh.tmpl`

```bash
#!/usr/bin/env bash
# Generate unique ntfy topic for this machine

set -euo pipefail

state_dir="$HOME/.local/state/wkflw-ntfy"
config_file="$state_dir/config"

# Skip if already generated
if [[ -f "$config_file" ]]; then
    echo "wkflw-ntfy topic already generated"
    exit 0
fi

# Generate unique topic
hostname="{{ .chezmoi.hostname }}"
username="{{ .chezmoi.username }}"
random="{{ randInt 10000000 99999999 }}"
topic="${hostname}-${username}-${random}"

# Write config
mkdir -p "$state_dir"
echo "WKFLW_NTFY_TOPIC=$topic" > "$config_file"

echo "Generated wkflw-ntfy topic: $topic"
```

**Step 3: Document nushell hook integration**

Add to nushell config documentation explaining how to source the hooks.

**Step 4: Commit**

```bash
git add run_once_after_wkflw-ntfy-generate-topic.sh.tmpl
git commit -m "feat(wkflw-ntfy): add chezmoi configuration integration

- Generate unique ntfy topic on first apply
- Document hook configuration for Claude Code
- Document nushell hook integration

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 5: Documentation and Cleanup

### Task 17: Add comprehensive README and migration guide

**Files:**
- Update: `private_dot_local/lib/wkflw-ntfy/README.md`
- Create: `docs/notes/2025-11-10-wkflw-ntfy-v2-migration.md`

**Step 1: Enhance main README**

Expand `private_dot_local/lib/wkflw-ntfy/README.md` with:
- Architecture overview
- Component list with descriptions
- Testing instructions
- Troubleshooting guide
- Links to design docs

**Step 2: Create migration guide**

File: `docs/notes/2025-11-10-wkflw-ntfy-v2-migration.md`

```markdown
# Workflow Notifications V2 Migration Guide

## Overview

V2 is a complete redesign of the workflow notification system with improved reliability, testability, and maintainability.

## Breaking Changes

### Architecture

- **V1:** Monolithic scripts with complex presence detection
- **V2:** 29 small composable scripts, environment-based strategies

### Configuration

- **V1:** Mixed env vars and hardcoded values
- **V2:** All config via env vars with sensible defaults

### Environment Detection

- **V1:** Attempted session ID capture (unreliable)
- **V2:** Window ID capture for iTerm (reliable)

## Migration Steps

### 1. Remove V1 Components

```bash
# Remove old scripts (if they exist)
rm -f ~/.local/bin/ntfy-*
```

### 2. Apply Chezmoi Configuration

```bash
chezmoi apply
```

This will:
- Create wkflw-ntfy directory structure
- Install all v2 scripts
- Generate ntfy topic
- Configure Claude Code hooks

### 3. Verify Installation

```bash
# Check scripts are installed
ls -l ~/.local/lib/wkflw-ntfy/

# Check ntfy topic generated
cat ~/.local/state/wkflw-ntfy/config

# Test a notification
~/.local/lib/wkflw-ntfy/push/wkflw-ntfy-push "Test" "Migration successful"
```

### 4. Configure Nushell Hooks

Add to `~/.config/nushell/config.nu`:

```nushell
# Load wkflw-ntfy hooks
source ~/.local/lib/wkflw-ntfy/hooks/nushell.nu

# Add hooks to config
$env.config = ($env.config | merge {
    hooks: {
        pre_execution: [{ code: "ntfy-pre-execution-hook" }]
        pre_prompt: [{ code: "ntfy-pre-prompt-hook" }]
    }
})
```

### 5. Test Notifications

**Test Claude Code notifications:**
- Start a Claude task
- Switch to another app
- Wait for notification

**Test nushell notifications:**
```bash
sleep 95  # Command over 90s threshold
# Should see notification
```

## Configuration Options

All configuration via environment variables:

```bash
# Optional overrides in ~/.config/nushell/env.nu
export WKFLW_NTFY_NUSHELL_THRESHOLD=120  # 2 minutes
export WKFLW_NTFY_ESCALATION_DELAY=300   # 5 minutes
export WKFLW_NTFY_DEBUG=1                # Enable debug logs
```

## Troubleshooting

### No Notifications

1. Check ntfy topic exists:
   ```bash
   cat ~/.local/state/wkflw-ntfy/config
   ```

2. Check logs:
   ```bash
   cat ~/.local/state/wkflw-ntfy/warnings.log
   ```

3. Enable debug logging:
   ```bash
   export WKFLW_NTFY_DEBUG=1
   ```

### Desktop Notifications Not Working

**macOS:**
```bash
which terminal-notifier
brew install terminal-notifier
```

**Linux:**
```bash
which notify-send
sudo apt install libnotify-bin
```

### Mobile Push Not Working

1. Check topic is set:
   ```bash
   echo $WKFLW_NTFY_TOPIC
   ```

2. Test push directly:
   ```bash
   curl -X POST https://ntfy.sh/$WKFLW_NTFY_TOPIC -d "Test"
   ```

3. Subscribe on mobile:
   - Install ntfy app
   - Subscribe to topic from config file

## Rollback

If you need to rollback to V1:

```bash
# This will restore V1 scripts if they were backed up
# (V2 doesn't provide rollback - it's a clean install)
```

## Support

See:
- Product design: `docs/design-product/2025-11-10-workflow-notifications.md`
- Engineering design: `docs/design-engineering/2025-11-10-workflow-notifications.md`
- Implementation plan: `docs/implementation-plans/2025-11-10-workflow-notifications.md`
```

**Step 3: Commit**

```bash
git add private_dot_local/lib/wkflw-ntfy/README.md docs/notes/2025-11-10-wkflw-ntfy-v2-migration.md
git commit -m "docs(wkflw-ntfy): add comprehensive README and migration guide

- Enhanced architecture documentation
- Step-by-step migration instructions
- Troubleshooting guide
- Configuration examples

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Execution Handoff

Plan complete and saved to `docs/implementation-plans/2025-11-10-workflow-notifications.md`.

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration with quality gates.

**2. Parallel Session (separate)** - Open new session with executing-plans skill, batch execution with checkpoints.

**Which approach would you like?**
