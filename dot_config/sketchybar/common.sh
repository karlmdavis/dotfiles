# shellcheck shell=bash disable=SC2034
# Shared by sketchybarrc and every plugin: PATH, colours, and icon glyphs. Sourced, never run.

# SketchyBar is started by AeroSpace, so it and the plugins it runs see launchd's minimal PATH plus
# whatever AeroSpace adds. Name the two prefixes the plugins need rather than rely on that.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# Colours are 0xAARRGGBB, hard-coded from the terminal palette (Tokyo Night Storm; see the iTerm2
# README in the chezmoi source). Update them by hand if the palette moves.
BAR_COLOR=0xff1f2335    # bg_dark, the theme's colour for chrome around the editor
POPUP_COLOR=0xff24283b  # bg, the terminal background
POPUP_BORDER=0xff414868 # bright black
FG=0xffc0caf5
DIM=0xff565f89          # comment
ACCENT=0xff7aa2f7       # blue
WARN=0xffe0af68         # yellow
CRITICAL=0xfff7768e     # red
TRANSPARENT=0x00000000

FONT="JetBrainsMono Nerd Font"

# Icons are Material Design glyphs from the Nerd Font, which sit in a private-use block and so
# show as blanks or boxes in an editor without that font. Each is named by its Nerd Font id.
# md-battery_10 (twice: below 10% and 10-19%), _20 ... _90, md-battery (full); indexed by percent / 10.
ICON_BATTERY=(󰁺 󰁺 󰁻 󰁼 󰁽 󰁾 󰁿 󰂀 󰂁 󰂂 󰁹)
ICON_BATTERY_CHARGING=󰂄 # md-battery_charging
ICON_VOLUME_HIGH=󰕾      # md-volume_high
ICON_VOLUME_MEDIUM=󰖀    # md-volume_medium
ICON_VOLUME_LOW=󰕿       # md-volume_low
ICON_VOLUME_MUTED=󰖁     # md-volume_off
ICON_CPU=󰘚              # md-chip
ICON_RAM=󰍛              # md-memory
ICON_WIFI=󰖩             # md-wifi
ICON_WIFI_OFF=󰖪         # md-wifi_off
ICON_TAILSCALE=󰖂        # md-vpn
ICON_1PASSWORD=󰢁        # md-onepassword
ICON_CHECK=󰄬            # md-check
