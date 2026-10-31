#!/usr/bin/env bash
# Battery level, coloured as it runs low. Hidden on a Mac with no battery.

# shellcheck source=dot_config/sketchybar/common.sh
source "$CONFIG_DIR/common.sh"

status="$(pmset -g batt)"
percent="$(grep -Eo '[0-9]+%' <<<"$status" | head -1 | tr -d '%')"

if [ -z "$percent" ]; then
  sketchybar --set "$NAME" drawing=off
  exit 0
fi

color="$FG"
if grep -q 'AC Power' <<<"$status"; then
  icon="$ICON_BATTERY_CHARGING"
else
  icon="${ICON_BATTERY[percent / 10]}"
  if [ "$percent" -le 10 ]; then
    color="$CRITICAL"
  elif [ "$percent" -le 20 ]; then
    color="$WARN"
  fi
fi

sketchybar --set "$NAME" drawing=on icon="$icon" icon.color="$color" label="${percent}%" label.color="$color"
