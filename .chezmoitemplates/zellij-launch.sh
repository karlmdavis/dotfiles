##
# Interactive zellij auto-launch.
#
# Shared by ~/.bash_profile (bash) and ~/.zprofile (zsh). Launches the zellij 'welcome' chooser (whose
# panes run nushell) for REAL interactive terminals only, and never disturbs background, automation, or
# editor env-resolution shells. Opt out with NO_ZELLIJ=1; if zellij is missing, the shell continues.
##


##
# Safety guards (never disturb a non-terminal shell)
##

# Interactive shells only; scripts, `ssh host 'cmd'`, and build phases fall through untouched.
case $- in
  *i*) ;;
  *) return ;;
esac

# Require a real terminal on stdout; excludes every editor/IDE env-probe (those capture stdout to a pipe).
[ -t 1 ] || return

# Belt: explicit non-interactive remote command.
[ -n "${SSH_ORIGINAL_COMMAND:-}" ] && return

# Manual opt-out.
[ -n "${NO_ZELLIJ:-}" ] && return

# Already inside zellij — do not recurse.
[ -n "${ZELLIJ:-}" ] && return


##
# Editor / IDE integrated terminals (real ttys, so skip them by name)
##

# VS Code / Cursor: env-resolution probe and integrated terminal.
[ -n "${VSCODE_RESOLVING_ENVIRONMENT:-}" ] && return
[ -n "${VSCODE_INJECTION:-}" ] && return

# Zed integrated terminal.
[ -n "${ZED_TERM:-}" ] && return

# VS Code / Cursor / Zed by terminal-program name.
case "${TERM_PROGRAM:-}" in vscode|cursor|zed) return ;; esac

# JetBrains IDEs (IntelliJ, etc.).
[ "${TERMINAL_EMULATOR:-}" = "JetBrains-JediTerm" ] && return


##
# Launch
##

# Hand the terminal to the zellij welcome chooser (when zellij is installed).
command -v zellij >/dev/null 2>&1 && exec zellij -l welcome
