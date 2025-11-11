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
