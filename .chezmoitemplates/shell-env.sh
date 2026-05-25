##
# Shared PATH / utility / environment setup.
#
# Included by ~/.bash_profile (bash) and ~/.zprofile (zsh); the nushell equivalent lives in
# .chezmoitemplates/config.nu and is kept in sync with this list. Placed in the login files so it runs
# after macOS path_helper (correct precedence) and stays silent (scp/rsync safe). POSIX sh — the same
# text works in bash and zsh.
#
# Scope: ONLY tools installed on every system (see .chezmoidata/system_packages_autoinstall.yaml, plus
# Rust via run_onchange_install_rustup.sh). Machine-specific tools go in ~/.config/shell/env.local.sh
# (sourced near the end) — not here.
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
{{ $brew := "/home/linuxbrew/.linuxbrew" -}}
{{ if eq .chezmoi.os "darwin" -}}
{{ $brew = "/opt/homebrew" -}}
{{ end -}}
[ -x "{{ $brew }}/bin/brew" ] && eval "$({{ $brew }}/bin/brew shellenv)"


##
# Languages / toolchains
##

# Rust toolchain (rustup / cargo) — installed on every system via run_onchange_install_rustup.sh.
export CARGO_HOME="$HOME/.cargo"
_pp "$CARGO_HOME/bin"


##
# Node
##

# Volta: Node toolchain manager and shims (installed via the package manifest).
export VOLTA_HOME="$HOME/.volta"
_pp "$VOLTA_HOME/bin"


##
# Apps / extras
##

# pipx / pip --user installs.
_pp "$HOME/.local/bin"


##
# Environment variables
##

{{- if .isCMS }}
# CMS: username for ctkey (AWS CLI token retrieval).
export CTKEY_USERNAME="d6lu"

# CMS: trust the corporate (Zscaler) root CA for Node TLS.
export NODE_EXTRA_CA_CERTS="$HOME/ZscalerRootCertificate-2048-SHA256.crt"

{{ end -}}
# Use Helix as the default editor (matches nushell), when present.
if command -v hx >/dev/null 2>&1; then
  export EDITOR="hx"
  export VISUAL="hx"
fi


##
# Machine-local overrides
##

# Source machine-specific PATH/env (tools NOT installed on every system — e.g. SDKMAN, Docker, GUI apps).
# Created once by chezmoi, then maintained per machine; the _pp helper above is available to it.
[ -r "$HOME/.config/shell/env.local.sh" ] && . "$HOME/.config/shell/env.local.sh"


##
# Finalize
##

# Export the assembled PATH and drop the helper.
export PATH
unset -f _pp
