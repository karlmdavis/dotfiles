##
# This `~/.bashrc` script will be executed by Bash for non-login shells. 
# Because shells are often nested, everything executed here must be idempotent.
# 
# Most of the variables set here have special meaning to bash. Run `man 1 bash`
# for explanations.
##

# If not running interactively, don't do anything.
case $- in
  *i*) ;;
    *) return;;
esac

# Don't put duplicate lines or lines starting with space in the history.
HISTCONTROL=ignoreboth

# Append to the history file, don't overwrite it
shopt -s histappend

# Don't automatically cap ~/.bash_history; let it grow forever. I've had a 
# history file that's 25K lines, and it wasn't a problem.
if [[ "$OSTYPE" == "darwin"* ]]; then
  # MacOS doesn't seem to like the `-1` variants of this.
  HISTSIZE=9999999999
  HISTFILESIZE=999999999
else
  # Seems to work on Linux.
  HISTSIZE=-1
  HISTFILESIZE=-1
fi

# Record timestamps in the Bash history, as well.
# See `man strftime` for format options, but this is the ISO 8601 datetime 
# format, e.g. "2007-04-05T12:30-02:00".
HISTTIMEFORMAT='%FT%T%z '

# Check the window size after each command and, if necessary, update the values
# of LINES and COLUMNS.
shopt -s checkwinsize

# Configure options that are only available in newer versions of Bash.
setBash4Options() {
  # If set, the pattern "**" used in a pathname expansion context will match all 
  # files and zero or more directories and subdirectories.
  shopt -s globstar
}

# On MacOS, the default Bash is a POSIX-compliant-only v3.2.
if [ "${BASH_VERSION}" == "${BASH_VERSION/3.2/}" ]; then
  setBash4Options
fi

# Make less more friendly for non-text input files, see lesspipe(1).
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# Base16 Shell
BASE16_SHELL="$HOME/workspaces/tools/base16-shell.git"
[ -n "$PS1" ] && \
    [ -s "$BASE16_SHELL/profile_helper.sh" ] && \
        eval "$("$BASE16_SHELL/profile_helper.sh")"

# Set a fancy prompt (non-color, unless we know we "want" color).
case "$TERM" in
  xterm-color|*-256color) color_prompt=yes;;
esac

# Uncomment for a colored prompt, if the terminal has the capability; turned
# off by default to not distract the user: the focus in a terminal window
# should be on the output of commands, not on the prompt.
force_color_prompt=yes

if [ -n "$force_color_prompt" ]; then
  if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
    # We have color support; assume it's compliant with Ecma-48 
    # (ISO/IEC-6429). (Lack of such support is extremely rare, and such a 
    # case would tend to support setf rather than setaf.)
    color_prompt=yes
  else
    color_prompt=
  fi
fi

# ANSI color code constants.
# Reference: https://help.ubuntu.com/community/CustomizingBashPrompt
RS="\[\033[0m\]"    # reset
HC="\[\033[1m\]"    # hicolor
UL="\[\033[4m\]"    # underline
INV="\[\033[7m\]"   # inverse background and foreground
FBLK="\[\033[30m\]" # foreground black
FRED="\[\033[31m\]" # foreground red
FGRN="\[\033[32m\]" # foreground green
FYEL="\[\033[33m\]" # foreground yellow
FBLE="\[\033[34m\]" # foreground blue
FMAG="\[\033[35m\]" # foreground magenta
FCYN="\[\033[36m\]" # foreground cyan
FWHT="\[\033[37m\]" # foreground white
BBLK="\[\033[40m\]" # background black
BRED="\[\033[41m\]" # background red
BGRN="\[\033[42m\]" # background green
BYEL="\[\033[43m\]" # background yellow
BBLE="\[\033[44m\]" # background blue
BMAG="\[\033[45m\]" # background magenta
BCYN="\[\033[46m\]" # background cyan
BWHT="\[\033[47m\]" # background white

promptCommand() {
  # Append to history immediately, rather than at shell exit.
  # Note: If there are concurrent Bash sessions, their history will get mixed
  # in file. But this is worth the cost, as we no longer lose history when
  # shells exit abnormally.
  history -a
}

PROMPT_COMMAND=promptCommand

if [ "$color_prompt" = yes ]; then
  # Ubuntu 14.04's default prompt was:
  # PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '

  # The custom prompt set here will look like the following:
  # 
  #     2016-05-02 09:45:04, last command took 42s
  #     user@hostname:~/somedir
  #     $ 
  PS1="${FMAG}\n\D{%F %T}, last command took \${timer_show}${RS}\n${FGRN}\u@\h${RS}:${FBLE}\w\n${RS}\$ "
else
  PS1='\u@\h:\w\$ '
fi
unset color_prompt force_color_prompt

# If this is an xterm set the title to `user@host:dir`.
case "$TERM" in
xterm*|rxvt*)
  PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]$PS1"
  ;;
*)
  ;;
esac

# Enable color support of ls and also add handy aliases.
if [ -x /usr/bin/dircolors ]; then
  test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
  alias ls='ls --color=auto'
  #alias dir='dir --color=auto'
  #alias vdir='vdir --color=auto'

  alias grep='grep --color=auto'
  alias fgrep='fgrep --color=auto'
  alias egrep='egrep --color=auto'
fi

# Some more ls aliases.
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

# Add an "alert" alias for long running commands.  Use like so:
#   sleep 10; alert
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'

# Alias definitions.
# You may want to put all your additions into a separate file like
# ~/.bash_aliases, instead of adding them here directly.
# See /usr/share/doc/bash-doc/examples in the bash-doc package.

if [ -f ~/.bash_aliases ]; then
    . ~/.bash_aliases
fi

# Enable programmable completion features (you don't need to enable this, if 
# it's already enabled in /etc/bash.bashrc and /etc/profile sources 
# /etc/bash.bashrc).
if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
    . /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
  elif [ -r /usr/local/etc/profile.d/bash_completion.sh ]; then
    . /usr/local/etc/profile.d/bash_completion.sh
  fi
fi

# This function can be called to prepend things to the path. Taken from here:
# https://unix.stackexchange.com/a/124447.
# 
# Sample usage:
# 
#     path_prepend ~/foo/bin
#     export PATH
path_prepend() { case ":${PATH:=$1}:" in *:$1:*) ;; *) PATH="$1:$PATH" ;; esac; }

# Allow user binaries to override system ones (e.g. used for updated tmux).
[ -d "${HOME}/bin" ] && path_prepend "${HOME}/bin" && export PATH

# Set default editor that will be used by most terminal programs (e.g. git).
export EDITOR=/usr/bin/vim

# Use Gnome Keyring as an SSH agent, etc.
# Taken from:
# <https://wiki.archlinux.org/index.php/GNOME/Keyring#With_a_display_manager>.
if [ -n "$DESKTOP_SESSION" ];then
    eval $(gnome-keyring-daemon --start)
    export SSH_AUTH_SOCK
fi

# This `~/.bashrc` file is shared across many systems, but some things need to 
# be set per-system. Import any local settings, if they exist.
if [[ -f ~/.bashrc_local ]]; then
  . ~/.bashrc_local
fi

# jabba manages JDK/JRE installs/versions.
[ -s "${HOME}/.jabba/jabba.sh" ] && source "${HOME}/.jabba/jabba.sh"

# nvm manages Node installs/versions. Recommend going with a "Manual Install", per:
# https://github.com/creationix/nvm#manual-install
export NVM_DIR="$HOME/workspaces/tools/nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" # This loads nvm

# Yarn manages Node/JS packages. Recommend going with a "Manual Install via tarball", per:
# https://yarnpkg.com/lang/en/docs/install/#alternatives-stable
export YARN_DIR="$HOME/workspaces/tools/yarn-v1.6.0/bin"
[ -d "$YARN_DIR" ] && path_prepend "$YARN_DIR" && export PATH

# RVM manages Ruby installations.
export RVM_DIR="$HOME/.rvm"
[ -d "$RVM_DIR" ] && source "${RVM_DIR}/scripts/rvm"

# Go install, which is installed manually via tarball per <https://golang.org/doc/install>.
export GO_DIR="$HOME/workspaces/tools/go1.11.5.linux-amd64/bin"
[ -d "$GO_DIR" ] && path_prepend "$GO_DIR" && export PATH

# Setup the Cargo environment, which is used for Rust development.
[ -f "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"

# pyenv manages multiple Python installations.
export PYENV_ROOT="${HOME}/.pyenv"
if [ -d "${PYENV_ROOT}" ]; then
  path_prepend "${PYENV_ROOT}"
  export PATH
  eval "$(pyenv init --path)"
  eval "$(pyenv init -)"
fi

# <https://python-poetry.org/> and perhaps other tools install to this path.
[ -d "${HOME}/.local/bin" ] && path_prepend "${HOME}/.local/bin" && export PATH

# Enable key bindings and fuzzy completions for <https://github.com/junegunn/fzf>.
[ -f ~/.fzf.bash ] && source ~/.fzf.bash

# <https://sdkman.io/> manages the installation and versioning of various dev tooling, e.g. Maven.
export SDKMAN_DIR="${HOME}/.sdkman"
[[ -s "${SDKMAN_DIR}/bin/sdkman-init.sh" ]] && source "${SDKMAN_DIR}/bin/sdkman-init.sh"

# Enable the Starship prompt.
hash starship 2> /dev/null  && eval "$(starship init bash)"
