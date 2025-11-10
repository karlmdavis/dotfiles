#!/usr/bin/env nu
# Ntfy notification hooks for long-running commands
# Sourced by config.nu to enable testability
#
# Debug logging:
#   Enable: export NU_HOOKS_DEBUG=1  (in your shell)
#   Logs:   ~/.local/state/nushell/hooks-{pid}.log
#   Note:   Disabled by default to prevent unbounded log growth

# Helper: Check if debug logging is enabled and get log file path
def get-debug-log-path [] {
    let debug_enabled = ($env.NU_HOOKS_DEBUG? | default "0") == "1"
    if $debug_enabled {
        let log_dir = $"($env.HOME)/.local/state/nushell"
        mkdir $log_dir
        $"($log_dir)/hooks-($nu.pid).log"
    } else {
        null
    }
}

# Helper: Write debug log if enabled
def debug-log [message: string] {
    let log_file = (get-debug-log-path)
    if $log_file != null {
        $message | save --append $log_file
    }
}

# Helper function to format duration in human-readable format
export def format-duration [duration_sec: int] {
    let minutes = ($duration_sec // 60)  # Integer division
    let seconds = ($duration_sec mod 60)

    if $minutes > 0 {
        $"($minutes)m ($seconds)s"
    } else {
        $"($seconds)s"
    }
}

# Pre-execution hook: Record command start details
export def --env ntfy-pre-execution-hook [] {
    debug-log $"(date now | format date '%Y-%m-%d %H:%M:%S') - pre-execution hook called\n"

    $env.__NOTIF_CMD_START_TIME = (date now | into int)
    $env.__NOTIF_CMD_START_TTY = (tty e>| complete | get stdout | str trim)
    $env.__NOTIF_LAST_CMD = (commandline)

    debug-log $"  Set START_TIME: ($env.__NOTIF_CMD_START_TIME)\n"
    debug-log $"  Set LAST_CMD: ($env.__NOTIF_LAST_CMD)\n"
}

# Pre-prompt hook: Check duration and send notification if needed
export def --env ntfy-pre-prompt-hook [] {
    debug-log $"(date now | format date '%Y-%m-%d %H:%M:%S') - pre-prompt hook called\n"

    # Only check if we have a recorded start time
    if '__NOTIF_CMD_START_TIME' in $env {
        debug-log "  Has start time: true\n"

        # Get command duration (in nanoseconds)
        let duration_ns = if 'CMD_DURATION_MS' in $env {
            (($env.CMD_DURATION_MS | into int) * 1_000_000)  # Convert ms to ns
        } else {
            0
        }

        let duration_sec = ($duration_ns / 1_000_000_000)

        # Configuration defaults
        let duration_threshold = ($env.NTFY_NU_DURATION_THRESHOLD? | default 30)

        debug-log $"  Duration: ($duration_sec)s, Threshold: ($duration_threshold)s\n"

        # Duration threshold (configurable via NTFY_NU_DURATION_THRESHOLD)
        if $duration_sec >= $duration_threshold {
            debug-log "  Duration EXCEEDS threshold - checking command\n"

            # Get the command that ran
            let cmd = if '__NOTIF_LAST_CMD' in $env {
                $env.__NOTIF_LAST_CMD | str trim
            } else {
                "unknown command"
            }

            # Filter out interactive editors and other noisy commands
            let noisy_commands = ['hx', 'vim', 'nvim', 'emacs', 'nano', 'less', 'more', 'man', 'top', 'htop']
            let is_noisy = ($noisy_commands | any {|noise| $cmd starts-with $noise})

            debug-log $"  Command: '($cmd)'\n"
            debug-log $"  Is noisy: ($is_noisy)\n"

            if not $is_noisy {
                debug-log "  SENDING NOTIFICATION\n"

                # Get TTY path
                let tty_path = if '__NOTIF_CMD_START_TTY' in $env {
                    $env.__NOTIF_CMD_START_TTY
                } else {
                    "unknown"
                }

                # Format duration
                let duration_formatted = (format-duration ($duration_sec | into int))

                # Get project name (current directory basename)
                let project_name = ($env.PWD | path basename)

                # Spawn background notification check (detached)
                # Using bash to properly detach the process
                let notify_cmd = $"nohup '($env.HOME)/.local/bin/ntfy-alert-if-unfocused.sh' '($tty_path)' 'Command completed' '($cmd)' '($duration_formatted)' '($project_name)' </dev/null >/dev/null 2>&1 &"
                bash -c $notify_cmd
            } else {
                debug-log "  Skipped: noisy command\n"
            }
        } else {
            debug-log "  Duration below threshold - no notification\n"
        }
    } else {
        debug-log "  No start time recorded\n"
    }

    # Always clean up environment variables to prevent accumulation
    if '__NOTIF_CMD_START_TIME' in $env {
        hide-env __NOTIF_CMD_START_TIME
    }
    if '__NOTIF_CMD_START_TTY' in $env {
        hide-env __NOTIF_CMD_START_TTY
    }
    if '__NOTIF_LAST_CMD' in $env {
        hide-env __NOTIF_LAST_CMD
    }
}

# Cleanup old log files (called on shell startup)
export def cleanup-old-logs [] {
    let log_dir = $"($env.HOME)/.local/state/nushell"
    if ($log_dir | path exists) {
        let cutoff_time = ((date now) - 7day)

        # Find and remove log files older than 7 days (ignore errors if no files)
        try {
            ls $"($log_dir)/hooks-*.log"
            | where modified < $cutoff_time
            | get name
            | each {|file| rm $file}
        }
    }
}
