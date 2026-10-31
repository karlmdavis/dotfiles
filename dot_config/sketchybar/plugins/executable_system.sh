#!/usr/bin/env bash
# CPU and memory use, as percentages. Runs on the `cpu` item and updates `ram` as well.

# shellcheck source=dot_config/sketchybar/common.sh
source "$CONFIG_DIR/common.sh"

# Every process's CPU share, summed and spread over the cores. `ps` reports a decaying average
# rather than an instantaneous sample, so this lags a spike by a few seconds; in exchange it costs
# about 25ms, where sampling with `top` takes over a second of CPU itself.
cpu="$(ps -A -o %cpu | awk -v cores="$(sysctl -n hw.ncpu)" 'NR > 1 { sum += $1 } END { printf "%.0f", sum / cores }')"

# Memory in use the way the Stats app counts it: active, inactive, speculative, wired, and
# compressed pages, less the purgeable and file-backed ones the system can drop on demand.
ram="$(vm_stat | awk -v total="$(sysctl -n hw.memsize)" '
  /page size of/           { page = $8 }
  /Pages active/           { active = $3 }
  /Pages inactive/         { inactive = $3 }
  /Pages speculative/      { speculative = $3 }
  /Pages wired down/       { wired = $4 }
  /occupied by compressor/ { compressed = $5 }
  /Pages purgeable/        { purgeable = $3 }
  /File-backed pages/      { file_backed = $3 }
  END {
    used = active + inactive + speculative + wired + compressed - purgeable - file_backed
    printf "%.0f", used * page / total * 100
  }')"

# $1: the value; $2 and $3: where it turns to the warning and critical colours.
level_color() {
  if [ "$1" -ge "$3" ]; then
    echo "$CRITICAL"
  elif [ "$1" -ge "$2" ]; then
    echo "$WARN"
  else
    echo "$FG"
  fi
}

cpu_color="$(level_color "$cpu" 70 90)"
ram_color="$(level_color "$ram" 90 95)"

sketchybar --set cpu label="${cpu}%" label.color="$cpu_color" icon.color="$cpu_color" \
           --set ram label="${ram}%" label.color="$ram_color" icon.color="$ram_color"
