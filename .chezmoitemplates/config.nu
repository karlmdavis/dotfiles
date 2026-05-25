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

# Trust the corporate (Zscaler) root CA for Node TLS.
$env.NODE_EXTRA_CA_CERTS = ($env.HOME | path join "ZscalerRootCertificate-2048-SHA256.crt")
{{- end }}

# Personal scripts kept under version control or as scratch tooling.
path add ($env.HOME | path join 'bin')

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

# Add Rust toolchain to my path.
$env.CARGO_HOME = ($nu.home-path | path join '.cargo')
path add ($env.CARGO_HOME | path join "bin")

# Configure Volta.
$env.VOLTA_HOME = ($env.HOME | path join '.volta')
path add ($env.VOLTA_HOME | path join 'bin')

# Configure pipx.
path add ($env.HOME | path join '.local' | path join 'bin')

# Source machine-local PATH/env (tools not installed on every system — e.g. SDKMAN, Docker, GUI apps).
# Edit local.nu in this config dir (created once by chezmoi, never overwritten); `path add` is available.
source local.nu


##
# Aliases.
##

# `td` — Todoist CLI via pinned npx fetch (no global install).
alias td = npx --package=@doist/todoist-cli@1.60.0 -- td


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

# Set helix as default editor (EDITOR + VISUAL, matching bash/zsh).
let helix_bin = ($homebrew_prefix | path join 'bin' | path join 'hx')
if ($helix_bin | path exists) {
    $env.config.buffer_editor = $helix_bin
    $env.EDITOR = $helix_bin
    $env.VISUAL = $helix_bin
}

# Make the `dirs` command available.
use std/dirs


##
# Workflow Notifications (wkflw-ntfy V2)
#
# Notify when long-running commands complete.
# Uses progressive escalation: desktop → mobile push if not acknowledged.
# Implementation in ~/.local/lib/wkflw-ntfy/
##

const wkflw_ntfy_handler = '{{ .chezmoi.homeDir }}/.local/lib/wkflw-ntfy/hooks/nushell-handler.sh'
if ($wkflw_ntfy_handler | path exists) {
    # Track command start time and command text
    $env.config.hooks = {
        pre_execution: [{
            code: {||
                $env.__WKFLW_NTFY_START = (date now | format date '%s')
                $env.__WKFLW_NTFY_CMD = (commandline)
            }
        }]
        pre_prompt: [{
            code: {||
                if '__WKFLW_NTFY_START' in $env {
                    let duration = ((date now | format date '%s') | into int) - ($env.__WKFLW_NTFY_START | into int)
                    let cmd = $env.__WKFLW_NTFY_CMD
                    let exit_code = $env.LAST_EXIT_CODE
                    let cwd = (pwd)

                    # Call bash handler with command details
                    bash $wkflw_ntfy_handler $cmd $duration $exit_code $cwd

                    # Clean up
                    hide-env __WKFLW_NTFY_START
                    hide-env __WKFLW_NTFY_CMD
                }
            }
        }]
    }
}
