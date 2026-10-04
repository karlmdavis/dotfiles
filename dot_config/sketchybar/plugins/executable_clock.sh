#!/usr/bin/env bash
# Date and time, following the system's 12- or 24-hour setting.

# shellcheck source=dot_config/sketchybar/common.sh
source "$CONFIG_DIR/common.sh"

if [ "$(defaults read -g AppleICUForce24HourTime 2>/dev/null)" = 1 ]; then
  format='%a %b %-d  %H:%M'
else
  format='%a %b %-d  %-I:%M %p'
fi

sketchybar --set "$NAME" label="$(date "+$format")"
