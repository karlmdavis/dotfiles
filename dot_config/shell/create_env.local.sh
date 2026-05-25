##
# ~/.config/shell/env.local.sh — machine-LOCAL PATH/env for bash & zsh.
#
# Created once by chezmoi (never overwritten); edit freely per machine. Sourced near the end of the
# shared shell-env setup, so the `_pp` helper and the assembled $PATH are available. Put tools here
# that are NOT in .chezmoidata/system_packages_autoinstall.yaml — i.e. not installed on every system.
#
# `_pp <dir>` prepends <dir> to PATH if it exists and isn't already present. Examples:
##


##
# SDKMAN (Java / Maven) + the `sdk` command
##

# # Java home from SDKMAN's selected JDK.
# [ -d "$HOME/.sdkman/candidates/java/current" ] && export JAVA_HOME="$HOME/.sdkman/candidates/java/current"
#
# # Source sdkman-init for the `sdk` command (it appends candidates below /usr/bin, so re-prepend below).
# [ -s "$HOME/.sdkman/bin/sdkman-init.sh" ] && export SDKMAN_DIR="$HOME/.sdkman" && . "$HOME/.sdkman/bin/sdkman-init.sh"
#
# # Front-prepend java/maven so `java` beats the macOS /usr/bin/java stub.
# [ -n "${JAVA_HOME:-}" ] && PATH="$JAVA_HOME/bin:$PATH"
# [ -d "$HOME/.sdkman/candidates/maven/current/bin" ] && PATH="$HOME/.sdkman/candidates/maven/current/bin:$PATH"


##
# Docker
##

# # Docker CLI plugins / binaries (Docker Desktop).
# _pp "$HOME/.docker/bin"


##
# GUI apps
##

# # Obsidian (macOS app bundle) — lets you launch it from the shell.
# _pp "/Applications/Obsidian.app/Contents/MacOS"
