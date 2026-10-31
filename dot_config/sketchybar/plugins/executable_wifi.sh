#!/usr/bin/env bash
# Wi-Fi state for the `wifi` item and the rows of its popup.
#
# Run by SketchyBar to refresh, and with the argument `toggle` (from the popup's power row) to
# switch Wi-Fi off or on.

# shellcheck source=dot_config/sketchybar/common.sh
source "$CONFIG_DIR/common.sh"

if [ "${SENDER:-}" = mouse.exited.global ]; then
  sketchybar --set wifi popup.drawing=off
  exit 0
fi

device="$(networksetup -listallhardwareports | awk '/Hardware Port: Wi-Fi/ { getline; print $2 }')"

wifi_is_on() {
  [[ "$(networksetup -getairportpower "$device")" == *": On" ]]
}

if [ "${1:-}" = toggle ]; then
  if wifi_is_on; then
    networksetup -setairportpower "$device" off
  else
    networksetup -setairportpower "$device" on
  fi
  sketchybar --set wifi popup.drawing=off
fi

address="$(ipconfig getifaddr "$device" 2>/dev/null)"

if ! wifi_is_on; then
  icon="$ICON_WIFI_OFF"
  color="$DIM"
  power_label="Turn Wi-Fi On"
  address_label="Wi-Fi is off"
elif [ -n "$address" ]; then
  icon="$ICON_WIFI"
  color="$FG"
  power_label="Turn Wi-Fi Off"
  address_label="$address"
else
  icon="$ICON_WIFI"
  color="$WARN"
  power_label="Turn Wi-Fi Off"
  address_label="Not connected"
fi

sketchybar --set wifi icon="$icon" icon.color="$color" \
           --set wifi.power label="$power_label" \
           --set wifi.address label="$address_label"
