#!/usr/bin/env bash
# Output volume. A click toggles mute.

# shellcheck source=dot_config/sketchybar/common.sh
source "$CONFIG_DIR/common.sh"

if [ "${SENDER:-}" = mouse.clicked ]; then
  osascript -e 'set volume output muted not (output muted of (get volume settings))'
fi

# "output volume:31, input volume:76, alert volume:100, output muted:false". An output device
# with no software volume (some displays and audio interfaces) reports "missing value" instead.
settings="$(osascript -e 'get volume settings')"
volume="$(sed -En 's/^output volume:([0-9]+),.*/\1/p' <<<"$settings")"

color="$FG"
if [ -z "$volume" ]; then
  icon="$ICON_VOLUME_HIGH"
  label="--"
elif [[ "$settings" == *"output muted:true"* ]] || [ "$volume" -eq 0 ]; then
  icon="$ICON_VOLUME_MUTED"
  label="${volume}%"
  color="$DIM"
else
  label="${volume}%"
  if [ "$volume" -lt 34 ]; then
    icon="$ICON_VOLUME_LOW"
  elif [ "$volume" -lt 67 ]; then
    icon="$ICON_VOLUME_MEDIUM"
  else
    icon="$ICON_VOLUME_HIGH"
  fi
fi

sketchybar --set "$NAME" icon="$icon" icon.color="$color" label="$label" label.color="$color"
