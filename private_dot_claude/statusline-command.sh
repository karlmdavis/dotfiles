#!/usr/bin/env bash
# Claude Code status line — mirrors Tokyo Night Starship prompt style.
# Receives JSON via stdin; outputs a single status line string.

input=$(cat)

# --- Extract fields ---
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // empty')
model=$(echo "$input" | jq -r '.model.display_name // empty')
repo=$(echo "$input" | jq -r '.workspace.repo | if . then .owner + "/" + .name else empty end')
branch=$(echo "$input" | jq -r '.worktree.branch // empty')
git_worktree=$(echo "$input" | jq -r '.workspace.git_worktree // empty')
pr_number=$(echo "$input" | jq -r '.pr.number // empty')
pr_state=$(echo "$input" | jq -r '.pr.review_state // empty')
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
session_name=$(echo "$input" | jq -r '.session_name // empty')
# Absent when the model has no effort parameter; reflects live /effort changes.
effort=$(echo "$input" | jq -r '.effort.level // empty')
fast_mode=$(echo "$input" | jq -r '.fast_mode // false')
# Absent until the first API response, and only on claude.ai Pro/Max subscriptions.
five_hour_pct=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')

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

# Directory
parts+=("$(printf '\033[34m\033[0m\033[44;97m %s \033[0m\033[34m\033[0m' "$short_dir")")

# Repo / git info
git_info=""
if [ -n "$repo" ]; then
  git_info="$repo"
  [ -n "$branch" ] && git_info="$git_info  $branch"
elif [ -n "$branch" ]; then
  git_info=" $branch"
fi
[ -n "$git_worktree" ] && git_info="${git_info:+$git_info }[wt:$git_worktree]"
if [ -n "$git_info" ]; then
  parts+=("$(printf '\033[90m%s\033[0m' "$git_info")")
fi

# PR badge
if [ -n "$pr_number" ]; then
  case "$pr_state" in
    approved)          pr_label="PR #$pr_number ✓" ;;
    changes_requested) pr_label="PR #$pr_number ✗" ;;
    draft)             pr_label="PR #$pr_number (draft)" ;;
    *)                 pr_label="PR #$pr_number" ;;
  esac
  parts+=("$(printf '\033[33m%s\033[0m' "$pr_label")")
fi

# Session name
[ -n "$session_name" ] && parts+=("$(printf '\033[35m%s\033[0m' "$session_name")")

# Model, with the live reasoning effort when the model has one
if [ -n "$model" ]; then
  model_label="$model"
  [ -n "$effort" ] && model_label="$model_label ($effort)"
  parts+=("$(printf '\033[36m%s\033[0m' "$model_label")")
fi

# Fast mode badge
[ "$fast_mode" = "true" ] && parts+=("$(printf '\033[33m⚡fast\033[0m')")

# Context usage
if [ -n "$used_pct" ]; then
  parts+=("$(colored_pct ctx "$(printf '%.0f' "$used_pct")")")
fi

# Subscription 5-hour window usage
if [ -n "$five_hour_pct" ]; then
  parts+=("$(colored_pct 5h "$(printf '%.0f' "$five_hour_pct")")")
fi

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
