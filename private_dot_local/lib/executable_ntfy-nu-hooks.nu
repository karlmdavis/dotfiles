#!/usr/bin/env nu
# Ntfy notification hooks for long-running commands
# Sourced by config.nu to enable testability

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
export def ntfy-pre-execution-hook [] {
    $env.__NOTIF_CMD_START_TIME = (date now | into int)
    $env.__NOTIF_CMD_START_TTY = (tty e>| complete | get stdout | str trim)
    $env.__NOTIF_LAST_CMD = (commandline)
}

# Pre-prompt hook: Check duration and send notification if needed
export def ntfy-pre-prompt-hook [] {
    # Only check if we have a recorded start time
    if '__NOTIF_CMD_START_TIME' in $env {
        # Get command duration (in nanoseconds)
        let duration_ns = if 'CMD_DURATION_MS' in $env {
            ($env.CMD_DURATION_MS * 1_000_000)  # Convert ms to ns
        } else {
            0
        }

        let duration_sec = ($duration_ns / 1_000_000_000)

        # Configuration defaults
        let duration_threshold = ($env.NTFY_NU_DURATION_THRESHOLD? | default 30)

        # Duration threshold (configurable via NTFY_NU_DURATION_THRESHOLD)
        if $duration_sec >= $duration_threshold {
            # Get the command that ran
            let cmd = if '__NOTIF_LAST_CMD' in $env {
                $env.__NOTIF_LAST_CMD | str trim
            } else {
                "unknown command"
            }

            # Filter out interactive editors and other noisy commands
            let noisy_commands = ['hx', 'vim', 'nvim', 'emacs', 'nano', 'less', 'more', 'man', 'top', 'htop']
            let is_noisy = ($noisy_commands | any {|noise| $cmd starts-with $noise})

            if not $is_noisy {
                # Get TTY path
                let tty_path = if '__NOTIF_CMD_START_TTY' in $env {
                    $env.__NOTIF_CMD_START_TTY
                } else {
                    "unknown"
                }

                # Format duration
                let duration_formatted = (format-duration $duration_sec)

                # Get project name (current directory basename)
                let project_name = ($env.PWD | path basename)

                # Spawn background notification check (detached)
                # Using bash to properly detach the process
                let notify_cmd = $"nohup '($env.HOME)/.local/bin/ntfy-alert-if-unfocused.sh' '($tty_path)' 'Command completed' '($cmd)' '($duration_formatted)' '($project_name)' </dev/null >/dev/null 2>&1 &"
                bash -c $notify_cmd
            }
        }
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
