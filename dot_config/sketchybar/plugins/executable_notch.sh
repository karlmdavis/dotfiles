#!/usr/bin/env bash
# Size the bar on a notched built-in display to fill the band beside the notch.
#
# macOS keeps that band clear of windows even with the native menu bar hidden, so a bar exactly as
# tall as the band costs no screen space. The band's height in points depends on the display's
# scaled resolution, so ask AppKit rather than hard-code it. With no notched display attached the
# answer is 0, which SketchyBar reads as "use the bar's ordinary height".

# shellcheck source=dot_config/sketchybar/common.sh
source "$CONFIG_DIR/common.sh"

height="$(osascript -l JavaScript -e '
  ObjC.import("AppKit");
  var top = 0, screens = $.NSScreen.screens;
  for (var i = 0; i < screens.count; i++) {
    top = Math.max(top, screens.objectAtIndex(i).safeAreaInsets.top);
  }
  Math.round(top);' 2>/dev/null)"

sketchybar --bar notch_display_height="${height:-0}"
