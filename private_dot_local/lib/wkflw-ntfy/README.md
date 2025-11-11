# Workflow Notification System V2

## Architecture Overview

Small, composable bash scripts following Unix philosophy.
Each script does one thing well, tested in isolation.

**Key features:**
- Progressive escalation (desktop → mobile push after delay)
- Environment-based strategies (iTerm, macOS GUI, Linux GUI, no-GUI)
- Atomic marker files prevent notification spam
- Comprehensive test coverage (29 scripts, all tested)

## Components

### Core (`core/`)
- `wkflw-ntfy-config` - Load configuration from environment variables
- `wkflw-ntfy-log` - Logging utility (debug/warning/error)
- `wkflw-ntfy-detect-env` - Detect terminal environment
- `wkflw-ntfy-decide-strategy` - Choose notification strategy

### Markers (`marker/`)
- `wkflw-ntfy-marker-create` - Create marker for escalation tracking
- `wkflw-ntfy-marker-check` - Check if marker exists
- `wkflw-ntfy-marker-delete` - Delete marker (atomic claim)

### macOS Platform (`macos/`)
- `wkflw-ntfy-macos-get-window` - Get iTerm window ID
- `wkflw-ntfy-macos-focus` - Focus window by ID
- `wkflw-ntfy-macos-send` - Send desktop notification
- `wkflw-ntfy-macos-callback` - Handle notification click

### Linux Platform (`linux/`)
- `wkflw-ntfy-linux-send` - Send desktop notification via notify-send

### Escalation (`escalation/`)
- `wkflw-ntfy-escalate-worker` - Background worker (waits, checks marker, sends push)
- `wkflw-ntfy-escalate-spawn` - Spawn detached escalation worker

### Push Notifications (`push/`)
- `wkflw-ntfy-push` - Send mobile push via ntfy.sh

### Hooks (`hooks/`)
- `claude-stop.sh` - Claude Code Stop hook (task completed)
- `claude-notification.sh` - Claude Code Notification hook (needs attention)
- `nushell-handler.sh` - Nushell long-running command handler

## Configuration

Environment variables (all optional, have defaults):

```bash
# ntfy server and topic
WKFLW_NTFY_SERVER="https://ntfy.sh"  # default
WKFLW_NTFY_TOPIC="hostname-username-12345"  # auto-generated

# Thresholds
WKFLW_NTFY_NUSHELL_THRESHOLD=90  # seconds, default 90
WKFLW_NTFY_ESCALATION_DELAY=120  # seconds, default 120

# State directory
WKFLW_NTFY_STATE_DIR="$HOME/.local/state/wkflw-ntfy"  # default

# Debug logging
WKFLW_NTFY_DEBUG=0  # 0=off, 1=on
```

Configuration is stored in `~/.local/state/wkflw-ntfy/config`:
```bash
WKFLW_NTFY_TOPIC=macbook-karl-abc123
```

## Strategy Selection

The system automatically chooses the best notification strategy based on environment:

| Environment | Claude Stop | Claude Notification (permission) | Claude Notification (input) | Nushell |
|-------------|-------------|----------------------------------|----------------------------|---------|
| iTerm | progressive | desktop-only | progressive | progressive |
| macOS GUI | desktop-only | desktop-only | desktop-only | desktop-only |
| Linux GUI | desktop-only | desktop-only | desktop-only | desktop-only |
| No GUI | push-only | push-only | push-only | push-only |

**Strategies:**
- **progressive**: Desktop notification + escalation to push after delay if not acknowledged
- **desktop-only**: Desktop notification only (no escalation)
- **push-only**: Mobile push notification only

## Testing

Run all tests:
```bash
mise run test
```

Run with linting:
```bash
# Complete CI suite (lint + test)
mise run ci
```

Or run bats directly:
```bash
# All tests
bats test/wkflw-ntfy/unit/

# Specific test file
bats test/wkflw-ntfy/unit/test_config.bats
```

Test coverage:
- Unit tests: Core components (config, logging, environment, strategy, markers, push, escalation).
- Unit tests: Platform components (macOS window ops, notifications, Linux).

## Troubleshooting

### No notifications received

Check ntfy topic is configured:
```bash
cat ~/.local/state/wkflw-ntfy/config
```

Test push notification manually:
```bash
~/.local/lib/wkflw-ntfy/push/wkflw-ntfy-push "Test" "Hello"
```

Subscribe to your topic in ntfy app (iOS/Android) or web: `https://ntfy.sh/your-topic`

### Desktop notifications not appearing

**macOS:** Check terminal-notifier is installed:
```bash
which terminal-notifier
```

Install via Homebrew if missing:
```bash
brew install terminal-notifier
```

**Linux:** Check notify-send is installed:
```bash
which notify-send
```

### Debug logging

Enable debug logs to see what's happening:
```bash
export WKFLW_NTFY_DEBUG=1
```

View debug logs:
```bash
cat ~/.local/state/wkflw-ntfy/debug-*.log
```

View warnings/errors:
```bash
cat ~/.local/state/wkflw-ntfy/warnings.log
```

### Permission issues

Ensure scripts are executable:
```bash
chmod +x ~/.local/lib/wkflw-ntfy/**/*
```

### Escalation not working

Check escalation delay setting (default 120s):
```bash
echo $WKFLW_NTFY_ESCALATION_DELAY
```

Check marker files are being created:
```bash
ls ~/.local/state/wkflw-ntfy/markers/
```

## Design Documentation

See comprehensive design docs:
- Product design: `docs/design-product/2025-11-10-workflow-notifications.md`
- Engineering design: `docs/design-engineering/2025-11-10-workflow-notifications.md`
- Implementation plan: `docs/implementation-plans/2025-11-10-workflow-notifications.md`

## Architecture Principles

1. **Unix philosophy**: Small tools that do one thing well
2. **Testability**: Every component tested in isolation
3. **Environment-based**: Adapt to platform and session type
4. **Progressive escalation**: Start gentle, escalate if ignored
5. **Atomic operations**: Marker files prevent race conditions
6. **Graceful degradation**: Fall back gracefully when tools missing
