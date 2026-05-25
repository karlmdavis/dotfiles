##
# Shared PATH / utility / environment setup.
#
# Included by ~/.bash_profile (bash) and ~/.zprofile (zsh); the nushell equivalent lives in
# .chezmoitemplates/config.nu and is kept in sync with this list. Placed in the login files so it runs
# after macOS path_helper (correct precedence) and stays silent (scp/rsync safe). POSIX sh — the same
# text works in bash and zsh. Add new tools to the matching section below (and mirror them in config.nu).
##


##
# Helpers
##

# Idempotent prepend: add $1 to PATH only if it is a directory and not already present.
_pp() { [ -d "$1" ] && case ":$PATH:" in *":$1:"*) ;; *) PATH="$1:$PATH" ;; esac; }


##
# Core / system paths
##

# Personal scripts kept under version control or as scratch tooling.
_pp "$HOME/bin"

# Legacy default install prefix; some manually-installed tools still land here.
_pp "/usr/local/bin"

# Homebrew: one eval adds bin+sbin to PATH and sets HOMEBREW_*, MANPATH, INFOPATH.
{{ $brew := "/home/linuxbrew/.linuxbrew" }}{{ if eq .chezmoi.os "darwin" }}{{ $brew = "/opt/homebrew" }}{{ end -}}
[ -x "{{ $brew }}/bin/brew" ] && eval "$({{ $brew }}/bin/brew shellenv)"


##
# Languages / toolchains
##

# SDKMAN: source its init first for the `sdk` manager command (bash/zsh only; nushell cannot source it).
# Note: sdkman-init appends the selected candidates to PATH at LOW priority (below /usr/bin), so the
# java/maven front-prepend below has to come after it.
[ -s "$HOME/.sdkman/bin/sdkman-init.sh" ] && export SDKMAN_DIR="$HOME/.sdkman" && . "$HOME/.sdkman/bin/sdkman-init.sh"

# Java + Maven: front-prepend the selected SDKMAN candidates so `java` beats the macOS /usr/bin/java
# stub (sdkman-init places them below /usr/bin). Unconditional front-prepend — may leave one harmless
# duplicate PATH entry, but `java`/`mvn` resolve to SDKMAN, identical to the nushell config.
if [ -d "$HOME/.sdkman/candidates/java/current" ]; then
  export JAVA_HOME="$HOME/.sdkman/candidates/java/current"
  PATH="$JAVA_HOME/bin:$PATH"
fi
[ -d "$HOME/.sdkman/candidates/maven/current/bin" ] && PATH="$HOME/.sdkman/candidates/maven/current/bin:$PATH"

# Rust toolchain (rustup / cargo).
export CARGO_HOME="$HOME/.cargo"
_pp "$CARGO_HOME/bin"


##
# Node
##

# Volta: Node toolchain manager and shims.
export VOLTA_HOME="$HOME/.volta"
_pp "$VOLTA_HOME/bin"

# fnm: Node version manager; adds the active Node to PATH (only when fnm is installed).
if command -v fnm >/dev/null 2>&1; then
  eval "$(fnm env 2>/dev/null)"
  [ -n "${FNM_MULTISHELL_PATH:-}" ] && _pp "$FNM_MULTISHELL_PATH/bin"
{{- if .isCMS }}

  # CMS: trust the corporate (Zscaler) root CA for Node TLS.
  export NODE_EXTRA_CA_CERTS="$HOME/ZscalerRootCertificate-2048-SHA256.crt"
{{- end }}
fi


##
# Apps / extras
##

# Docker CLI plugins and binaries (Docker Desktop).
_pp "$HOME/.docker/bin"

# pipx / pip --user installs.
_pp "$HOME/.local/bin"
{{ if eq .chezmoi.os "darwin" }}
# BasicTeX / pdflatex (macOS only, if installed).
_pp "/usr/local/texlive/2025basic/bin/universal-darwin"

# Obsidian CLI helper (macOS app bundle, if installed).
_pp "/Applications/Obsidian.app/Contents/MacOS"
{{- end }}


##
# Environment variables
##
{{ if .isCMS }}
# CMS: username for ctkey (AWS CLI token retrieval).
export CTKEY_USERNAME="d6lu"
{{ end }}
# Use Helix as the default editor (matches nushell), when present.
if command -v hx >/dev/null 2>&1; then
  export EDITOR="hx"
  export VISUAL="hx"
fi


##
# Finalize
##

# Export the assembled PATH and drop the helper.
export PATH
unset -f _pp
