# config.nu
#
# Installed by:
# version = "0.106.1"
#
# This file is used to override default Nushell settings, define
# (or import) custom commands, or run any other startup tasks.
# See https://www.nushell.sh/book/configuration.html
#
# Nushell sets "sensible defaults" for most configuration settings, 
# so your `config.nu` only needs to override these defaults if desired.
#
# You can open the chezmoi-rendered version of this file in your default editor using:
#     config nu
#
# To edit the source chezmoi template, run:
#     chezmoi edit $nu.config-path
#
# You can also pretty-print and page through the documentation for configuration
# options using:
#     config nu --doc | nu-highlight | less -R


##
# Environment Variables and Path Additions
#
# Note: `++=` appends entries, while `path add` prepends entries.
##
use std/util 'path add'

{{- if .isCMS }}
# Set username for ctkey, which is used to get AWS CLI tokens.
$env.CTKEY_USERNAME = 'd6lu'
{{- end }}

# Add /usr/local/bin to my path.
path add '/usr/local/bin'

# Configure Homebrew.
{{ if eq .chezmoi.os "darwin" -}}
let homebrew_prefix = '/opt/homebrew'
{{ else if eq .chezmoi.osRelease.id "ubuntu" -}}
let homebrew_prefix = '/home/linuxbrew/.linuxbrew'
{{ end -}}
if ($homebrew_prefix | path exists) {
    $env.HOMEBREW_PREFIX = $homebrew_prefix
    $env.HOMEBREW_CELLAR = ($env.HOMEBREW_PREFIX | path join 'Cellar')
    $env.HOMEBREW_REPOSITORY = $env.HOMEBREW_PREFIX
    path add ($env.HOMEBREW_PREFIX | path join 'bin')
    path add ($env.HOMEBREW_PREFIX | path join 'sbin')
    let man_dir = ($env.HOMEBREW_PREFIX | path join 'share' | path join 'man')
    $env.MANPATH = if "MANPATH" in $env {
        $env.MANPATH
        | split row ":"
        | prepend $man_dir
        | str join ":"
    } else {
        $"($man_dir):"
    }
    let info_dir = ($env.HOMEBREW_PREFIX | path join 'share' | path join 'info')
    $env.INFOPATH = if "INFOPATH" in $env {
        $env.INFOPATH
        | split row ":"
        | prepend $info_dir
        | str join ":"
    } else {
        $"($info_dir):"
    }
}

# Add Java (from SDKMAN!) to my path if present.
let sdkman_java = ($env.HOME | path join ".sdkman/candidates/java/current")
if ($sdkman_java | path exists) {
    $env.JAVA_HOME = $sdkman_java
    path add ($env.JAVA_HOME | path join "bin")
}

# Add Rust toolchain to my path.
$env.CARGO_HOME = ($nu.home-path | path join '.cargo')
path add ($env.CARGO_HOME | path join "bin")

# Add Docker CLI tools to my path.
let docker_bin = ([$nu.home-path, '.docker', 'bin'] | path join)
if ($docker_bin | path exists) {
    path add $docker_bin
}

# Configure Volta.
$env.VOLTA_HOME = ($env.HOME | path join '.volta')
path add ($env.VOLTA_HOME | path join 'bin')

# Enable fnm, to add nvm and NodeJS to the path.
if (which fnm | is-not-empty) {
    fnm env --json | from json | load-env
    path add ($env.FNM_MULTISHELL_PATH | path join "bin")
    {{- if .isCMS }}
    $env.NODE_EXTRA_CA_CERTS = ($env.HOME | path join "ZscalerRootCertificate-2048-SHA256.crt")
    {{- end }}
}

# Configure pipx.
path add ($env.HOME | path join '.local' | path join 'bin')

# Add basictex/pdflatex to the path (macOS only, if present).
let texlive_bin = '/usr/local/texlive/2025basic/bin/universal-darwin/'
if ($texlive_bin | path exists) {
    path add $texlive_bin
}


##
# Aliases.
##

alias claude = volta run --node=22 --bundled-npm npx @anthropic-ai/claude-code


##
# Other Configuration
#
# Note: Some of this requires the above path, etc. setup, so this needs to be after it.
##

# Disable nu's default startup banner.
$env.config.show_banner = false

# Save shell command history more or less permanently.
$env.config.history.max_size = 5_000_000_000
$env.config.history.sync_on_enter = true
$env.config.history.file_format = 'sqlite'
$env.config.history.isolation = true

# Enable the [Starship](https://starship.rs) prompt (lite vs full).
mkdir ($nu.data-dir | path join "vendor/autoload")

# Linux console sessions (e.g. Ubuntu Server with a physical monitor) do not support fancy fonts.
# Decide which starship config to use: lite for TERM=linux or when NO_NERD_FONT set.
let starship_config_full = ($env.HOME | path join ".config" | path join "starship.toml")
let starship_config_lite = ($env.HOME | path join ".config" | path join "starship-lite.toml")
if ( ("TERM" in $env) and ($env.TERM == 'linux') ) or ("NO_NERD_FONT" in $env) {
    if ($starship_config_lite | path exists) {
        $env.STARSHIP_CONFIG = $starship_config_lite
    }
} else if ($starship_config_full | path exists) {
    $env.STARSHIP_CONFIG = $starship_config_full
}

if (which starship | is-not-empty) {
    starship init nu | save -f ($nu.data-dir | path join "vendor/autoload/starship.nu")
}

# Set helix as default editor.
let helix_bin = ($homebrew_prefix | path join 'bin' | path join 'hx')
if ($helix_bin | path exists) {
    $env.config.buffer_editor = $helix_bin
    $env.EDITOR = $helix_bin
}

# Make the `dirs` command available.
use std/dirs


##
# Long Command Notifications
#
# Notify when commands take longer than 30 seconds to complete.
# Uses hybrid focus detection to avoid spam when terminal is active.
# Implementation in ~/.local/lib/ntfy-nu-hooks.nu
##

# Source ntfy notification hooks
let ntfy_hooks = ($env.HOME | path join '.local' 'lib' 'ntfy-nu-hooks.nu')
if ($ntfy_hooks | path exists) {
    source $ntfy_hooks

    # Configure hooks for command duration tracking
    $env.config.hooks = {
        pre_execution: [{ code: {|| ntfy-pre-execution-hook } }]
        pre_prompt: [{ code: {|| ntfy-pre-prompt-hook } }]
    }
}
