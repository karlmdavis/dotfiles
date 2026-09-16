#!/bin/sh
# check-mise-usage.sh — pre-tool-call hook for Hermes and Claude Code.
#
# Purpose:
#   Blocks direct `uv` invocations when a `mise.toml` exists in the current
#   directory or any parent. The agent should use `mise exec -- uv ...` instead,
#   so that mise-managed environment variables (like PYTHONPYCACHEPREFIX and
#   UV_PROJECT_ENVIRONMENT) are applied per-project, keeping Python build
#   artifacts (__pycache__/, .venv/) out of Obsidian-synced vault directories.
#
# How it's used:
#   - Hermes shell hook (pre_tool_call): configured in config.yaml under `hooks:`.
#     Hermes pipes a JSON payload on stdin with tool_name, tool_input.command, cwd.
#   - Claude Code PreToolUse hook: configured in ~/.claude/settings.json under `hooks`
#     (exec form, `"args": []`, so the path is spawned directly with no shell).
#     Claude Code pipes the same JSON shape on stdin.
#   - Both systems parse stdout JSON: {} = allow; on block the script prints ONE object
#     carrying both contracts (see the footer): top-level {"decision":"block","reason":...}
#     for Hermes (and Claude Code's deprecated PreToolUse form), plus
#     hookSpecificOutput.permissionDecision = "deny" for Claude Code's current form.
#   - Exit code 2 is set on block as well. Claude Code reads the JSON on every exit
#     code, and exit 2 is the one outcome JSON cannot override, so the block holds
#     even if a future Claude Code stops honouring either JSON shape.
#
# Tested by test/claude/check-mise-usage.bats; linted by `mise run lint`.
#
# This script must be bulletproof — it runs on every terminal/bash tool call
# across all projects. Always validate edits with Shellcheck (`shellcheck --shell sh`)
# to ensure POSIX compatibility and catch linting issues. Never use bashisms.
#
# Dependencies: jq (for JSON parsing). If jq is missing, the script exits with
# an error explaining how to install it.

set -eu

# --------------------------------------------------------------------------- #
# Read and parse the stdin payload.
# --------------------------------------------------------------------------- #

input=$(cat)

# Both Hermes and Claude Code send tool_name and tool_input.command.
# Field names are the same in both systems.
# Fail hard if jq is not installed — do not silently allow the tool call.
if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: check-mise-usage.sh requires jq, which is not installed." >&2
  echo "Install it with: brew install jq" >&2
  exit 2
fi

tool_name=$(printf '%s' "$input" | jq -r '.tool_name // empty' 2>/dev/null) || tool_name=""
command=$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null) || command=""
cwd=$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null) || cwd=""

# Only check terminal/bash commands.
if [ "$tool_name" != "terminal" ] && [ "$tool_name" != "Bash" ]; then
  printf '{}\n'
  exit 0
fi

# Only check if there's a command to inspect.
if [ -z "$command" ]; then
  printf '{}\n'
  exit 0
fi

# --------------------------------------------------------------------------- #
# Detect bare `uv` invocations.
# --------------------------------------------------------------------------- #
# We need to catch commands where `uv` is the first token (the actual command
# being run), possibly preceded by env-var assignments or `cd` prefixes.
# We do NOT want to block:
#   - `mise exec -- uv ...` (mise is wrapping uv — this is correct usage)
#   - `eval "$(mise activate bash)" && uv ...` (mise is activated — env vars are set)
#   - Commands that merely mention `uv` in a string argument
#
# Strategy: check if `uv` appears as the first word of any command segment
# (split by && or || or ;), and the segment is not part of a `mise exec` pattern.

# Normalize: trim leading whitespace.
command_stripped=$(printf '%s' "$command" | sed 's/^[[:space:]]*//')

# Quick reject: if `uv` doesn't appear at all, allow.
# Pattern uses [|] and [&] to match literal pipe/ampersand chars in ERE
# (backslash-escaping | in ERE is unreliable across implementations).
if ! printf '%s' "$command_stripped" | grep -qE '(^|[&][&][[:space:]]*|[|][|][[:space:]]*|;[[:space:]]*)uv([[:space:]]|$)'; then
  printf '{}\n'
  exit 0
fi

# Check if mise is wrapping the uv call. If `mise exec` appears before `uv`
# in the command string, we allow it.
if printf '%s' "$command_stripped" | grep -qE 'mise[[:space:]]+exec.*--[[:space:]]*uv'; then
  printf '{}\n'
  exit 0
fi

# Check if mise activate is called before uv (eval "$(mise activate ...)" && uv ...)
if printf '%s' "$command_stripped" | grep -qE 'mise[[:space:]]+activate'; then
  printf '{}\n'
  exit 0
fi

# --------------------------------------------------------------------------- #
# Check for mise.toml in cwd or parent directories.
# --------------------------------------------------------------------------- #
# If no mise.toml is found, there's nothing to enforce — allow the call.

if [ -z "$cwd" ]; then
  cwd="$PWD"
fi

has_mise_toml=false
dir="$cwd"
while [ "$dir" != "/" ] && [ -n "$dir" ]; do
  if [ -f "$dir/mise.toml" ]; then
    has_mise_toml=true
    break
  fi
  dir=$(dirname "$dir")
done

if [ "$has_mise_toml" = false ]; then
  printf '{}\n'
  exit 0
fi

# --------------------------------------------------------------------------- #
# Block: a mise.toml was found and the command uses bare `uv`.
# --------------------------------------------------------------------------- #
# Both Hermes and Claude Code parse stdout JSON to determine whether to block, but
# they read different keys, so one object carries both:
#   - Top-level {"decision": "block", "reason": ...}: Hermes translates this into its
#     canonical {"action": "block", "message": ...}. Claude Code accepted the same keys
#     for PreToolUse until they were deprecated in favour of the shape below.
#   - hookSpecificOutput {"hookEventName": "PreToolUse", "permissionDecision": "deny",
#     "permissionDecisionReason": ...}: Claude Code's current PreToolUse contract; the
#     reason becomes the permission-denied message the model sees.
# Exit code 2 is set as well: Claude Code blocks on exit 2 regardless of JSON, using
# the JSON reason when it parses and stderr otherwise, so stderr also carries the reason.

if command -v mise >/dev/null 2>&1; then
  reason="This project uses mise (mise.toml found). Direct \`uv\` invocations bypass mise-managed environment variables, which can cause Python build artifacts (__pycache__/, .venv/) to be written into the project directory and synced via Obsidian Sync. Instead of running \`uv\` directly, use: mise exec -- uv sync, mise exec -- uv run pytest, mise exec -- uv run python scripts/<name>.py. Or activate mise for the current shell first: eval \"\$(mise activate bash)\""
else
  reason="This project has a mise.toml file, but mise is not installed on this system. Direct \`uv\` invocations bypass mise-managed environment variables, which can cause Python build artifacts (__pycache__/, .venv/) to be written into the project directory and synced via Obsidian Sync. Install mise first: curl https://mise.run | sh (or: brew install mise). Then use mise to run uv: mise exec -- uv sync, mise exec -- uv run pytest"
fi

# Print the block directive as JSON to stdout (jq handles the escaping), then the
# reason on stderr for the exit-code-2 fallback path.
jq -c -n --arg reason "$reason" '{
  "decision": "block",
  "reason": $reason,
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": $reason
  }
}'
printf '%s\n' "$reason" >&2

exit 2
