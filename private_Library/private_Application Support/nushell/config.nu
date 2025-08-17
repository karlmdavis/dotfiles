# Disable nu's default startup banner.
$env.config.show_banner = false

# Prep setup for the [Starship](https://starship.rs) prompt.
# Note: This `init.nu` file will be used by the section right after this.
mkdir ~/.cache/starship
/opt/homebrew/bin/starship init nu | save -f ~/.cache/starship/init.nu

# Enable the [Starship](https://starship.rs) prompt.
# Note: This `init.nu` file is created via the Starship section right before this.
use ~/.cache/starship/init.nu

# Set vim as default editor.
$env.config.buffer_editor = '/usr/bin/vim'
$env.EDITOR = '/usr/bin/vim'

# Override defaults here for fancier history handling.
$env.config.history = {
  # Disable the max history size. We will remember EVERYTHING!!
  #max_size: 100_000 # Session has to be reloaded for this to take effect

  # Save the history after every command (which could also allow history to be shared between sessions if isolation is disabled).
  sync_on_enter: true

  # "sqlite" or "plaintext"
  file_format: 'sqlite'

  # only available with sqlite file_format.
  # true enables history isolation, false disables it.
  # true will allow the history to be isolated to the current session using up/down arrows.
  # false will allow the history to be shared across all sessions.
  isolation: true
}

##
# Environment Variables and Path Additions
#
# Note: `++=` appends entries, while `path add` prepends entries.
##
use std/util 'path add'

# Set username for ctkey, which is used to get AWS CLI tokens.
$env.CTKEY_USERNAME = 'd6lu'

# Add /usr/local/bin to my path.
path add '/usr/local/bin'

# Add Homebrew to my path.
$env.PATH ++= ['/opt/homebrew/bin']

# Add Java (from SDKMAN!) to my path.
$env.JAVA_HOME = ($env.HOME | path join ".sdkman/candidates/java/current")
path add ($env.JAVA_HOME | path join "bin")

# Add Rust toolchain to my path.
$env.CARGO_HOME = "~/.cargo"
path add ($env.CARGO_HOME | path join "bin")

# Add Docker CLI tools to my path.
$env.PATH ++= ["~/.docker/bin"]

# Add nvm and NodeJS to the path.
fnm env --json | from json | load-env
path add ($env.FNM_MULTISHELL_PATH | path join "bin")
$env.NODE_EXTRA_CA_CERTS = ($env.HOME | path join "ZscalerRootCertificate-2048-SHA256.crt")

# Add basictex/pdflatex to the path.
path add '/usr/local/texlive/2025basic/bin/universal-darwin/'
