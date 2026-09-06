##
# Shared shell aliases.
#
# Split out from shell-env.sh because aliases are a different KIND of thing: PATH and exported vars
# are inherited by child processes, so setting them once in the login files is enough. Aliases are
# per-shell-instance state and are NOT inherited, so they have to be re-established in every shell.
#
# That is why this snippet is included from every entry point rather than the login files alone:
#   - ~/.bash_profile, ~/.zprofile -> non-interactive LOGIN shells (`bash -l -c`, agent sessions),
#                                     which never reach ~/.bashrc (it returns early for
#                                     non-interactive shells) nor ~/.zshrc (zsh skips it entirely
#                                     when non-interactive).
#   - ~/.bashrc, ~/.zshrc          -> non-login INTERACTIVE shells (a bare `zsh` or `bash` subshell),
#                                     which never read the login files.
# Defining an alias twice is idempotent, so the double include in a login+interactive shell is
# harmless.
#
# The nushell equivalents live in .chezmoitemplates/config.nu; pinned versions are shared with it via
# .chezmoidata/tool_versions.yaml. POSIX sh -- the same text works in bash and zsh.
##

# Expand aliases in non-interactive shells (e.g. agent sessions, `bash -l -c`).
# zsh expands aliases by default; bash does not without this.
if [ -n "$BASH_VERSION" ]; then
  shopt -s expand_aliases 2>/dev/null
fi

# `td` -- Todoist CLI via pinned npx fetch (no global install).
alias td='npx --package={{ .tools.todoist_cli }} -- td'
