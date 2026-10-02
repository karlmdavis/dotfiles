#!/usr/bin/env bash
# Claude Code status line — mirrors Tokyo Night Starship prompt style.
# Receives JSON via stdin; outputs a single status line string.
#
# Segments are ordered most important first: Claude Code cuts the line from the right when
# it is wider than the terminal, so whatever comes last is what a narrow window loses.
# Anything Claude Code already shows itself (session name in the header, PR badge in the
# footer) is deliberately left out.

input=$(cat)

# --- Extract fields ---
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // empty')
model=$(echo "$input" | jq -r '.model.display_name // empty')
repo=$(echo "$input" | jq -r '.workspace.repo | if . then .owner + "/" + .name else empty end')
git_worktree=$(echo "$input" | jq -r '.workspace.git_worktree // empty')
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
# Absent when the model has no effort parameter; reflects live /effort changes.
effort=$(echo "$input" | jq -r '.effort.level // empty')
fast_mode=$(echo "$input" | jq -r '.fast_mode // false')
# Absent until the first API response, and only on claude.ai Pro/Max subscriptions.
five_hour_pct=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
# Lines changed over the whole session.
lines_added=$(echo "$input" | jq -r '.cost.total_lines_added // 0')
lines_removed=$(echo "$input" | jq -r '.cost.total_lines_removed // 0')

# --- Render "<label>:<pct>%" coloured by threshold, and reset the colour afterwards ---
# Green below 70, yellow below 90, red from 90 up. Every segment in this script turns its
# colour on and off itself (`\033[0m` is the reset), so nothing leaks into the next segment.
colored_pct() {
  label="$1"
  pct="$2"
  if   [ "$pct" -ge 90 ]; then color='\033[31m'   # red
  elif [ "$pct" -ge 70 ]; then color='\033[33m'   # yellow
  else                         color='\033[32m'   # green
  fi
  # %b so the escape sequence held in $color is interpreted, not printed literally.
  printf '%b%s:%d%%\033[0m' "$color" "$label" "$pct"
}

# --- Shorten cwd (truncate to last 3 segments, like Starship truncation_length=3) ---
if [ -n "$cwd" ]; then
  short_dir=$(echo "$cwd" | awk -F/ '{
    n = NF
    if (n <= 3) { print $0 }
    else { print "…/" $(n-2) "/" $(n-1) "/" $n }
  }')
else
  short_dir="~"
fi

# --- Build parts ---
parts=()

# Location: the repo (plus its linked worktree, if any), or the directory when not in a repo
if [ -n "$repo" ]; then
  location="$repo"
  [ -n "$git_worktree" ] && location="$location [wt:$git_worktree]"
  parts+=("$(printf '\033[90m%s\033[0m' "$location")")
else
  parts+=("$(printf '\033[34m\033[0m\033[44;97m %s \033[0m\033[34m\033[0m' "$short_dir")")
fi

# Context usage
if [ -n "$used_pct" ]; then
  parts+=("$(colored_pct ctx "$(printf '%.0f' "$used_pct")")")
fi

# Subscription 5-hour window usage
if [ -n "$five_hour_pct" ]; then
  parts+=("$(colored_pct 5h "$(printf '%.0f' "$five_hour_pct")")")
fi

# Lines changed, omitted until something has changed
if [ "$lines_added" -gt 0 ] || [ "$lines_removed" -gt 0 ]; then
  parts+=("$(printf '\033[32m+%d\033[0m/\033[31m-%d\033[0m' "$lines_added" "$lines_removed")")
fi

# Model, with the live reasoning effort when the model has one
if [ -n "$model" ]; then
  model_label="$model"
  [ -n "$effort" ] && model_label="$model_label ($effort)"
  parts+=("$(printf '\033[36m%s\033[0m' "$model_label")")
fi

# Fast mode badge
[ "$fast_mode" = "true" ] && parts+=("$(printf '\033[33m⚡fast\033[0m')")

# --- Join with separators ---
result=""
for part in "${parts[@]}"; do
  if [ -z "$result" ]; then
    result="$part"
  else
    result="$result  $part"
  fi
done

printf '%s\n' "$result"
