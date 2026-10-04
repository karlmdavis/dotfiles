#!/usr/bin/env bash
# Tailscale state for the `tailscale` item and the rows of its popup.
#
# Run by SketchyBar to refresh, and from the popup's rows with an action:
#   tailscale.sh up | down            connect or disconnect
#   tailscale.sh exit-node [<ip>]     route through that exit node, or through none

# shellcheck source=dot_config/sketchybar/common.sh
source "$CONFIG_DIR/common.sh"

SELF="$CONFIG_DIR/plugins/tailscale.sh"

# The standalone app installs a `tailscale` CLI on request; the App Store build has only the app
# binary, which acts as a CLI when told to (it otherwise decides by looking for a terminal).
tailscale_cli() {
  if command -v tailscale >/dev/null; then
    tailscale "$@"
  else
    TAILSCALE_BE_CLI=1 /Applications/Tailscale.app/Contents/MacOS/Tailscale "$@"
  fi
}

if [ "${SENDER:-}" = mouse.exited.global ]; then
  sketchybar --set tailscale popup.drawing=off
  exit 0
fi

case "${1:-}" in
  up) tailscale_cli up ;;
  down) tailscale_cli down ;;
  exit-node) tailscale_cli set --exit-node="${2:-}" ;;
esac
if [ -n "${1:-}" ]; then
  sketchybar --set tailscale popup.drawing=off
fi

# The app's CLI can print an error and still exit 0, so trust the output only once it parses and
# has a state in it.
status="$(tailscale_cli status --json 2>/dev/null)"
if ! state="$(jq -er '.BackendState' <<<"$status" 2>/dev/null)"; then
  state=Unavailable
fi

# The exit-node rows are rebuilt from scratch each time. Removing them is a separate call because
# it fails, harmlessly, when there are none yet.
sketchybar --remove '/tailscale\.exit\..*/' 2>/dev/null

if [ "$state" != Running ]; then
  sketchybar --set tailscale icon.color="$DIM" label.drawing=off \
             --set tailscale.toggle label="Connect" click_script="$SELF up"
  exit 0
fi

exit_node="$(jq -r '[.Peer[]? | select(.ExitNode) | .HostName][0] // empty' <<<"$status")"

args=(--set tailscale.toggle label="Disconnect" click_script="$SELF down")
if [ -n "$exit_node" ]; then
  args+=(--set tailscale icon.color="$ACCENT" label="$exit_node" label.color="$ACCENT" label.drawing=on)
  none_tick="$TRANSPARENT"
else
  args+=(--set tailscale icon.color="$FG" label.drawing=off)
  none_tick="$FG"
fi

# One row per machine that offers itself as an exit node, plus "none"; the row in use is ticked.
args+=(--add item tailscale.exit.none popup.tailscale
       --set tailscale.exit.none icon="$ICON_CHECK" icon.color="$none_tick" label="No exit node"
         click_script="$SELF exit-node")
row=0
while IFS=$'\t' read -r host address selected online; do
  row=$((row + 1))
  tick="$TRANSPARENT"
  [ "$selected" = true ] && tick="$FG"
  [ "$online" = true ] || host="$host (offline)"
  args+=(--add item "tailscale.exit.$row" popup.tailscale
         --set "tailscale.exit.$row" icon="$ICON_CHECK" icon.color="$tick" label="$host"
           click_script="$SELF exit-node $address")
done < <(jq -r '[.Peer[]? | select(.ExitNodeOption)] | sort_by(.HostName)[]
                | [.HostName, .TailscaleIPs[0], .ExitNode, .Online] | @tsv' <<<"$status")

sketchybar "${args[@]}"
