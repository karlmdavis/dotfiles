# Workflow Notifications V2 Migration Guide

## Overview

V2 is a complete redesign of the workflow notification system with improved reliability,
  testability, and maintainability.

## Breaking Changes

### Architecture

- **V1:** Monolithic scripts with complex presence detection.
- **V2:** 29 small composable scripts, environment-based strategies.

### Configuration

- **V1:** Mixed env vars and hardcoded values.
- **V2:** All config via env vars with sensible defaults.

### Environment Detection

- **V1:** Attempted session ID capture (unreliable).
- **V2:** Window ID capture for iTerm (reliable).

### File Locations

- **V1:** Scripts in `~/.local/bin/ntfy-*`.
- **V2:** Scripts in `~/.local/lib/wkflw-ntfy/` (organized by component).

### Hook Integration

- **V1:** Separate `.nu` file for nushell hooks.
- **V2:** Hooks integrated directly in nushell config, calling bash handler.

## Migration Steps

### 1. Remove V1 Components

V1 scripts have already been removed from the chezmoi repository.
No manual cleanup needed.

### 2. Apply Chezmoi Configuration

```bash
chezmoi apply
```

This will:
- Create wkflw-ntfy directory structure.
- Install all v2 scripts (29 executables).
- Generate unique ntfy topic.
- Update Claude Code hooks configuration.
- Update nushell configuration with new hooks.

### 3. Verify Installation

```bash
# Check scripts are installed
ls -l ~/.local/lib/wkflw-ntfy/

# Check ntfy topic generated
cat ~/.local/state/wkflw-ntfy/config

# Test a notification
~/.local/lib/wkflw-ntfy/push/wkflw-ntfy-push "Test" "Migration successful"
```

### 4. Subscribe to ntfy Topic

Install ntfy app on your mobile device:
- **iOS:** Download from App Store.
- **Android:** Download from Play Store or F-Droid.

Subscribe to your topic:
```bash
# Get your topic
cat ~/.local/state/wkflw-ntfy/config
# Example output: WKFLW_NTFY_TOPIC=macbook-karl-12345678

# In ntfy app, subscribe to: macbook-karl-12345678
# Or via web: https://ntfy.sh/macbook-karl-12345678
```

### 5. Test Notifications

**Test Claude Code notifications:**
1. Start a Claude Code session.
2. Ask Claude to perform a task.
3. Switch to another application (unfocus terminal).
4. Wait for Claude to need input.
5. You should receive a desktop notification (and mobile push after 2 minutes if not acknowledged).

**Test nushell notifications:**
```bash
# Run a command over threshold (default 90 seconds)
sleep 95
# Should see notification when complete
```

## Configuration Options

All configuration via environment variables in `~/.config/nushell/env.nu`:

```bash
# Optional overrides
$env.WKFLW_NTFY_NUSHELL_THRESHOLD = 120  # 2 minutes (default: 90)
$env.WKFLW_NTFY_ESCALATION_DELAY = 300   # 5 minutes (default: 120)
$env.WKFLW_NTFY_DEBUG = 1                # Enable debug logs (default: 0)
$env.WKFLW_NTFY_SERVER = "https://ntfy.sh"  # Custom ntfy server
```

## New Features in V2

### Progressive Escalation

Desktop notifications escalate to mobile push after delay (default 2 minutes) if not acknowledged.
Clicking desktop notification cancels escalation.

### Environment-Based Strategies

System automatically chooses notification strategy based on environment:

| Environment | Strategy | Behavior |
|-------------|----------|----------|
| iTerm | Progressive | Desktop → mobile push if ignored |
| macOS GUI | Desktop-only | Desktop notification only |
| Linux GUI | Desktop-only | Desktop notification only |
| No GUI (SSH) | Push-only | Mobile push only |

### Comprehensive Testing

V2 includes comprehensive unit test coverage with mock-based isolation.

Run tests:
```bash
# Run all tests
mise run test

# Complete CI (lint + test in parallel)
mise run ci
```

### Improved Logging

V2 separates debug and warning logs:

```bash
# Debug logs (when WKFLW_NTFY_DEBUG=1)
ls ~/.local/state/wkflw-ntfy/debug-*.log

# Warning/error logs (always on)
cat ~/.local/state/wkflw-ntfy/warnings.log
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
   # Then trigger a notification and check:
   cat ~/.local/state/wkflw-ntfy/debug-*.log
   ```

### Desktop Notifications Not Working

**macOS:**
```bash
# Check if terminal-notifier is installed
which terminal-notifier

# Install if missing
brew install terminal-notifier
```

**Linux:**
```bash
# Check if notify-send is installed
which notify-send

# Install if missing (Ubuntu/Debian)
sudo apt install libnotify-bin
```

### Mobile Push Not Working

1. Verify topic is configured:
   ```bash
   cat ~/.local/state/wkflw-ntfy/config
   ```

2. Test push directly:
   ```bash
   source ~/.local/lib/wkflw-ntfy/core/wkflw-ntfy-config
   curl -X POST "$WKFLW_NTFY_SERVER/$WKFLW_NTFY_TOPIC" \
     -H "Title: Test" \
     -d "Manual test notification"
   ```

3. Verify mobile app subscription:
   - Open ntfy app.
   - Check topic from config file is subscribed.
   - Test sending from web interface.

### Escalation Not Working

1. Check delay setting:
   ```bash
   echo $WKFLW_NTFY_ESCALATION_DELAY  # Default: 120
   ```

2. Check marker files:
   ```bash
   ls ~/.local/state/wkflw-ntfy/markers/
   # Markers should be created for progressive notifications
   # Markers should be deleted when desktop notification clicked
   ```

3. Check escalation worker process:
   ```bash
   # After triggering notification, worker should spawn
   ps aux | grep wkflw-ntfy-escalate-worker
   ```

### Claude Hooks Not Firing

1. Verify hooks are configured:
   ```bash
   cat ~/.claude/settings.json | grep -A 5 hooks
   # Should show Stop and Notification hooks
   ```

2. Check script is executable:
   ```bash
   ls -l ~/.local/lib/wkflw-ntfy/hooks/claude-*.sh
   # Should show -rwxr-xr-x permissions
   ```

3. Test hook manually:
   ```bash
   # Test Stop hook
   echo '{"hook_event_name":"Stop","duration":65,"cwd":"'$(pwd)'"}' | \
     ~/.local/lib/wkflw-ntfy/hooks/claude-stop.sh

   # Test Notification hook
   echo '{"hook_event_name":"Notification","notification_type":"idle_input","message":"Test","cwd":"'$(pwd)'"}' | \
     ~/.local/lib/wkflw-ntfy/hooks/claude-notification.sh
   ```

### Nushell Hooks Not Firing

1. Verify hooks are in config:
   ```bash
   # Check nushell config has wkflw-ntfy section
   grep -A 10 "wkflw-ntfy" ~/.config/nushell/config.nu
   ```

2. Check handler is executable:
   ```bash
   ls -l ~/.local/lib/wkflw-ntfy/hooks/nushell-handler.sh
   ```

3. Test manually:
   ```bash
   ~/.local/lib/wkflw-ntfy/hooks/nushell-handler.sh \
     "sleep 95" 95 0 "$PWD"
   ```

## Architecture Reference

See detailed design documentation:
- Product design: `docs/design-product/2025-11-10-workflow-notifications.md`.
- Engineering design: `docs/design-engineering/2025-11-10-workflow-notifications.md`.
- Implementation plan: `docs/implementation-plans/2025-11-10-workflow-notifications.md`.
- System README: `~/.local/lib/wkflw-ntfy/README.md`.

## Component Structure

```
~/.local/lib/wkflw-ntfy/
├── core/               # Core utilities
│   ├── wkflw-ntfy-config
│   ├── wkflw-ntfy-log
│   ├── wkflw-ntfy-detect-env
│   └── wkflw-ntfy-decide-strategy
├── marker/             # Escalation markers
│   ├── wkflw-ntfy-marker-create
│   ├── wkflw-ntfy-marker-check
│   └── wkflw-ntfy-marker-delete
├── macos/             # macOS platform
│   ├── wkflw-ntfy-macos-get-window
│   ├── wkflw-ntfy-macos-focus
│   ├── wkflw-ntfy-macos-send
│   └── wkflw-ntfy-macos-callback
├── linux/             # Linux platform
│   └── wkflw-ntfy-linux-send
├── push/              # Mobile push
│   └── wkflw-ntfy-push
├── escalation/        # Progressive escalation
│   ├── wkflw-ntfy-escalate-worker
│   └── wkflw-ntfy-escalate-spawn
└── hooks/             # Integration hooks
    ├── claude-stop.sh
    ├── claude-notification.sh
    └── nushell-handler.sh
```

## Support

For issues or questions:
1. Check troubleshooting section above.
2. Enable debug logging and review logs.
3. Review design documentation.
4. Check test suite for expected behavior examples.
