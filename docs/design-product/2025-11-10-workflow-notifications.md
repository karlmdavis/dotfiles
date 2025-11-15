# Workflow Notifications - Product Design

**Status:** V2 Design
**Version:** 2.0
**Replaces:** Unspecced v1 implementation from PR #9

## Overview

The Workflow Notification System provides awareness of long-running terminal workflows by sending desktop and mobile notifications when tasks complete or need attention.
It integrates with Claude Code hooks and nushell command tracking to notify users when:
- Claude Code finishes a task or needs permission
- Long-running shell commands complete

The system uses progressive escalation on macOS: desktop notifications appear immediately, and if not acknowledged within 2 minutes, a mobile push notification (via ntfy) is sent.
On Linux, basic desktop notifications are provided without escalation.

## Goals

- **Awareness:** Users know when Claude or commands finish, even when context-switched to other work.
- **Reliability:** Predictable behavior across macOS and Linux without complex heuristics.
- **Testability:** System is designed for automated testing without requiring GUI interaction.
- **Maintainability:** Clear component boundaries and naming make the system easy to understand and modify.

## Non-Goals

- Complex presence detection (idle time heuristics, focus tracking beyond basic terminal detection).
- Session-specific notification filtering (all qualifying events trigger notifications).
- Custom notification sounds or per-project thresholds (v2 uses global defaults).
- Supporting abandoned or unmaintained notification tools.

## User Scenarios

### Scenario 1: Claude Code Completes Work

**User context:** Working in Claude Code, starts a complex task, switches to browser while Claude works.

**System behavior:**
1. Claude completes response (Stop hook fires).
2. Desktop notification appears: "Claude finished in project-name: Fixed authentication bug...".
3. If notification not clicked within 2 minutes (macOS, iTerm only): mobile push notification sent.
4. User clicks notification: iTerm window that fired the notification comes to focus.

**Notification content:**
- Title: "Claude Code - Finished"
- Body: "{directory-name}: {message-preview}"
- Action: Focus iTerm window (macOS iTerm only)

### Scenario 2: Claude Code Needs Permission

**User context:** Claude attempts to use a tool requiring permission, user is away from terminal.

**System behavior:**
1. Permission prompt triggers Notification hook (notification_type: "permission_prompt").
2. Desktop notification appears immediately: "{message}" (e.g., "Claude needs your permission to use Bash").
3. No mobile escalation (user must respond via desktop to unblock Claude).
4. User clicks notification: Returns to terminal to approve/deny.

**Notification content:**
- Title: "Claude Code - Permission Needed"
- Body: "{message}" (passed through from hook)
- Action: Focus terminal window if possible

### Scenario 3: Claude Code Asks for Input

**User context:** Claude is working and needs user's decision to proceed, user has context-switched to another app.

**System behavior:**
1. Claude asks a question and waits for user response.
2. After 60+ seconds idle, Notification hook fires (notification_type: "idle_input" or similar).
3. Desktop notification appears: "{message}" (e.g., "Waiting for input").
4. If notification not clicked within 2 minutes (macOS, iTerm only): mobile push notification sent.
5. User clicks notification: iTerm window comes to focus, user can provide input.

**Notification content:**
- Title: "Claude Code - Input Needed"
- Body: "{directory-name}: {message}"
- Action: Focus iTerm window (macOS iTerm only)

**Example messages:**
- "Waiting for input (60s idle)"
- "Claude is waiting for your response"

### Scenario 4: Long-Running Command Completes

**User context:** Runs `npm test` (takes 2+ minutes), switches to Slack while tests run.

**System behavior:**
1. Command completes after 125 seconds (exceeds 90s threshold).
2. Desktop notification appears: "Command completed in project-name: npm test (2 min, succeeded)".
3. If notification not clicked within 2 minutes (macOS, iTerm only): mobile push sent.
4. User clicks notification: Terminal window comes to focus.

**Notification content:**
- Title: "Command Complete"
- Body: "{directory-name}: {command} ({duration} min, {status})"
- Status: "succeeded" or "failed"
- Action: Focus terminal window if possible

### Scenario 5: Non-GUI Session (SSH, API)

**User context:** Claude Code running in SSH session or via API (no GUI).

**System behavior:**
1. Desktop notification cannot be sent (no GUI environment detected).
2. Mobile push notification sent immediately via ntfy.
3. User sees notification on phone/watch, can remote in to check status.

**Notification content:** Same as desktop, but via ntfy push.

## Notification Strategies by Environment

The system adapts notification behavior based on the terminal environment:

### macOS iTerm2 Sessions

**Strategy:** Progressive escalation with window focusing.

**Behavior:**
1. Desktop notification appears immediately (via terminal-notifier).
2. Notification captures iTerm window ID at time of event.
3. If notification clicked: Focus the specific iTerm window that triggered the event.
4. If notification not clicked within 2 minutes: Send mobile push via ntfy.

**Why:** iTerm2 provides AppleScript access to window IDs, enabling reliable window focusing across macOS Spaces.

### macOS Non-iTerm GUI Sessions (VS Code, Terminal.app, etc.)

**Strategy:** Desktop notification only, no escalation.

**Behavior:**
1. Desktop notification appears immediately (via terminal-notifier).
2. If notification clicked: Activate the terminal application (all windows come to front).
3. No mobile escalation (to reduce false positives).

**Why:** These terminals don't expose window IDs, so we can only activate the app.
Without reliable window focusing, mobile escalation would create noise.

### Linux GUI Sessions (X11/Wayland with zellij/alacritty)

**Strategy:** Basic desktop notification only.

**Behavior:**
1. Desktop notification appears (via notify-send).
2. No click actions (not yet tested/proven).
3. No mobile escalation (not yet tested/proven).

**Why:** Cross-platform testing burden. V2 prioritizes proven functionality.
Future versions may add progressive escalation after testing on actual Linux systems.

### Non-GUI Sessions (SSH, API, headless)

**Strategy:** Mobile push only.

**Behavior:**
1. No desktop notification (no GUI environment).
2. Immediate mobile push via ntfy.

**Why:** Only viable notification channel for remote/headless workflows.

## Configuration

All configuration uses environment variables for testability and 12-factor compliance.

### Required Configuration

**`WKFLW_NTFY_TOPIC`** (auto-generated by chezmoi)
- ntfy topic for mobile push notifications.
- Format: `{hostname}-{username}-{random-number}`.
- Stored in `~/.local/state/wkflw-ntfy/config` and exported by shell initialization.
- Generated once during `chezmoi apply` via template random number generation.

### Optional Configuration

**`WKFLW_NTFY_SERVER`** (default: `https://ntfy.sh`)
- ntfy server URL for mobile push notifications.

**`WKFLW_NTFY_NUSHELL_THRESHOLD`** (default: `90`)
- Minimum command duration (seconds) to trigger nushell notifications.
- Only commands ≥ threshold generate notifications.

**`WKFLW_NTFY_ESCALATION_DELAY`** (default: `120`)
- Seconds to wait before escalating desktop notification to mobile push.
- Only applies to macOS iTerm sessions.

**`WKFLW_NTFY_DEBUG`** (default: unset)
- Set to `1` to enable debug logging to `~/.local/state/wkflw-ntfy/debug-{pid}.log`.
- Logs include timestamps, component names, and decision paths.

### Example Configuration

In `~/.config/nushell/env.nu` or equivalent:

```nushell
# Auto-generated by chezmoi
$env.WKFLW_NTFY_TOPIC = "macbook-karl-1a2b3c4d"

# Optional overrides
$env.WKFLW_NTFY_NUSHELL_THRESHOLD = "120"  # 2 minutes instead of 90s
$env.WKFLW_NTFY_ESCALATION_DELAY = "300"   # 5 minutes instead of 2
```

## Command Filtering (Nushell)

Not all commands trigger notifications, even if they exceed the duration threshold.

**Filtered commands** (no notification):
- Interactive editors: `hx`, `vim`, `nvim`, `nano`, `emacs`
- Interactive shells: `bash`, `zsh`, `fish`, `nu`
- TUI applications: `htop`, `top`, `less`, `more`
- Long-running daemons/servers (if identified in future iterations)

**Rationale:** These commands are intentionally long-running and user-attended.
Notifications would be noise.

The filter list is extracted from the v1 implementation and maintained in the nushell hook logic.

## Notification Content Details

### Claude Code - Stop Hook

- **Title:** `Claude Code - Finished`
- **Body:** `{directory-basename}: {first-50-chars-of-last-message}`
- **Example:** `dotfiles: Fixed authentication bug in OAuth flow`

### Claude Code - Notification Hook (Permission)

- **Title:** `Claude Code - Permission Needed`
- **Body:** `{message}` (passed through from hook JSON)
- **Example:** `Claude needs your permission to use Bash`

### Claude Code - Notification Hook (Input Needed)

- **Title:** `Claude Code - Input Needed`
- **Body:** `{directory-basename}: {message}`
- **Example:** `dotfiles: Waiting for input (60s idle)`

### Nushell Long Command

- **Title:** `Command Complete`
- **Body:** `{directory-basename}: {command} ({duration-minutes} min, {status})`
- **Example:** `my-app: npm test (3 min, succeeded)`
- **Status:** `succeeded` (exit 0) or `failed` (non-zero exit)

## Behavioral Details

### Progressive Escalation Flow (macOS iTerm only)

```
Event occurs (Claude finishes, command completes)
  ↓
Create marker file: ~/.local/state/wkflw-ntfy/markers/{unique-id}
  ↓
Show desktop notification with click handler
  ↓
Spawn background worker (2-minute timer)
  ↓
┌─ User clicks notification ────────┐
│  - Delete marker file             │
│  - Focus iTerm window              │
│  - Background worker sees no       │
│    marker, exits silently          │
└────────────────────────────────────┘
  OR
┌─ User ignores notification ───────┐
│  - 2 minutes elapse                │
│  - Background worker checks marker │
│  - If marker exists:               │
│    * Delete marker (atomic claim)  │
│    * Send ntfy push                │
│  - Worker exits                    │
└────────────────────────────────────┘
```

### Marker File Format

- **Location:** `~/.local/state/wkflw-ntfy/markers/`
- **Filename:** `{event-type}-{timestamp}-{pid}`
- **Content:** JSON with event details (for potential future use)
- **Lifecycle:** Created on event, deleted on acknowledgement or escalation

### Race Condition Prevention

Both the click handler and background worker may attempt to act on the same marker file.
To prevent duplicate actions (both focusing window AND sending push):
1. Delete the marker file (`rm -f`) **before** performing slow operations (window focusing, ntfy push).
2. Whichever process deletes the marker first "wins" and performs the action.
3. The second process finds no marker file and exits without action.

This works because `rm -f` is idempotent (doesn't error if file already deleted).

## Error Handling

### Missing Tools

**macOS - terminal-notifier missing:**
- Log warning to `~/.local/state/wkflw-ntfy/warnings.log`.
- Fall back to ntfy push only (same as non-GUI session).

**Linux - notify-send missing:**
- Log warning.
- Fall back to ntfy push only.

**ntfy unreachable or missing curl:**
- Log warning.
- Continue without mobile push (desktop notification still works).

### Hook Failures

**AppleScript failure (iTerm window ID capture):**
- Log warning.
- Fall back to desktop notification without click-to-focus action.

**Marker file creation failure:**
- Log error.
- Send desktop notification anyway (progressive escalation won't work).

### Debug Logging

When `WKFLW_NTFY_DEBUG=1`:
- All components log decisions to `~/.local/state/wkflw-ntfy/debug-{pid}.log`.
- Log format: `[YYYY-MM-DD HH:MM:SS] [component-name] message`.
- Logs include: environment detection, notification strategy chosen, marker operations, errors.
- Old debug logs (>7 days) are cleaned up on shell initialization.

## Success Criteria

Users should experience:
- Desktop notifications appear for qualifying events (Claude finishes, commands ≥90s).
- Mobile push notifications appear only when away (2+ min without clicking desktop notification).
- Clicking notifications focuses the relevant terminal window (macOS iTerm).
- No notifications for filtered commands (editors, shells).
- Predictable behavior: same events always trigger same notifications.
- No duplicate notifications for the same event.
- No notification storms (rapid-fire events are properly throttled/filtered).

## Changes from V1

V1 was an unspecced implementation developed in PR #9 that evolved organically through experimentation.
V2 is a complete redesign incorporating lessons learned from v1's implementation and testing:

**What changed:**
- Removed complex presence detection (idle time heuristics proved unreliable).
- Simplified to environment-based strategies (iTerm vs non-iTerm vs non-GUI).
- Changed from "session jumping" to "window focusing" (no reliable session UUID).
- Added marker file approach for progressive escalation (proven in experiments).
- Increased default nushell threshold from 3 minutes to 90 seconds (better balance).
- Changed escalation delay from 10 minutes to 2 minutes (faster feedback).
- Linux support simplified to basic notify-send (progressive escalation requires testing).
- Added explicit command filtering (interactive tools don't trigger notifications).

**What stayed the same:**
- Core goal: notify on Claude completion and long commands.
- Multi-channel approach: desktop + mobile.
- Click-to-focus behavior (where supported).

**Why the changes:**
- V1 assumptions about session IDs and focus detection proved incorrect during testing.
- Marker file approach solves progressive escalation cleanly without transcript monitoring.
- Environment-based strategies are more testable and maintainable than heuristics.
- Shorter delays provide better UX (2min vs 10min is meaningful for context-switching).

## Future Enhancements (Out of Scope for V2)

- Linux progressive escalation with click actions (requires testing on actual Linux systems).
- Per-project notification thresholds (e.g., `test/` longer threshold than `scripts/`).
- Notification grouping (multiple rapid events → single notification).
- Custom notification sounds per event type.
- Integration with system Do Not Disturb modes.
- Notification history/log viewer.
