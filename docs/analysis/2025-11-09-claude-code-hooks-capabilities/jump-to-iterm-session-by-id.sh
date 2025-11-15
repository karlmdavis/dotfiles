#!/usr/bin/env bash
# Jump to iTerm session by AppleScript session ID
set -euo pipefail

session_id="$1"

osascript <<EOF
tell application "iTerm2"
    activate
    repeat with w in windows
        repeat with t in tabs of w
            repeat with s in sessions of t
                if id of s is "$session_id" then
                    select w
                    select t
                    return
                end if
            end repeat
        end repeat
    end repeat
end tell
EOF
