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
HISTSIZE=-1
HISTFILESIZE=-1

# Record timestamps in the Bash history, as well.
# See `man strftime` for format options, but this is the ISO 8601 datetime 
# format, e.g. "2007-04-05T12:30-02:00".
HISTTIMEFORMAT='%FT%T%z '

# Check the window size after each command and, if necessary, update the values
# of LINES and COLUMNS.
shopt -s checkwinsize

# If set, the pattern "**" used in a pathname expansion context will match all 
# files and zero or more directories and subdirectories.
#shopt -s globstar

# Make less more friendly for non-text input files, see lesspipe(1).
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# Set variable identifying the chroot you work in (used in the prompt below)
if [ -z "${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
  debian_chroot=$(cat /etc/debian_chroot)
fi

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

# These functions can be used to collect and display wall-clock runtime of the
# last command.
# Reference: http://stackoverflow.com/a/34812608/1851299
function timer_now {
  date +%s%N
}

function timer_start {
  timer_start=${timer_start:-$(timer_now)}
}

function timer_stop {
  local delta_us=$((($(timer_now) - $timer_start) / 1000))
  local us=$((delta_us % 1000))
  local ms=$(((delta_us / 1000) % 1000))
  local s=$(((delta_us / 1000000) % 60))
  local m=$(((delta_us / 60000000) % 60))
  local h=$((delta_us / 3600000000))
  # Goal: always show around 3 digits of accuracy
  if ((h > 0)); then timer_show=${h}h${m}m
  elif ((m > 0)); then timer_show=${m}m${s}s
  elif ((s >= 10)); then timer_show=${s}.$((ms / 100))s
  elif ((s > 0)); then timer_show=${s}.$(printf %03d $ms)s
  elif ((ms >= 100)); then timer_show=${ms}ms
  elif ((ms > 0)); then timer_show=${ms}.$((us / 100))ms
  else timer_show=${us}us
  fi
  unset timer_start
  
  # "Ding" over the speakers if a long-running (>60s) command just completed.
  if ((delta_us > (1000 * 1000 * 60))); then
    # If we're not running in SSH and we can play sounds: play a sound.
    if [ -z "$SSH_TTY" ] && [ -x /usr/bin/paplay ]; then
      /usr/bin/paplay /usr/share/sounds/freedesktop/stereo/complete.oga
      # Note: Might also consider using `spd-say "It's done!"`.
    # Otherwise, beep.
    else
      for i in {1..5}; do tput bel; sleep 0.2; done
    fi
  fi
}

trap 'timer_start' DEBUG

promptCommand() {
  timer_stop

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
  PS1="${FMAG}\n\D{%F %T}, last command took \${timer_show}${RS}\n${debian_chroot:+($debian_chroot)}${FGRN}\u@\h${RS}:${FBLE}\w\n${RS}\$ "
else
  PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w\$ '
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

# Set default editor that will be used by most terminal programs (e.g. git).
export EDITOR=/usr/bin/vim

# This `~/.bashrc` file is shared across many systems, but some things need to 
# be set per-system. Import any local settings, if they exist.
if [[ -f ~/.bashrc_local ]]; then
  . ~/.bashrc_local
fi
