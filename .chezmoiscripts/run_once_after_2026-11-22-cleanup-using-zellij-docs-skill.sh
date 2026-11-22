#!/usr/bin/env bash
set -euo pipefail

# The `using-zellij-docs` Claude Code skill was replaced by `using-zellij` (2026-11-22). chezmoi does
# NOT remove a target directory when its source is renamed, so already-applied systems would keep
# the old skill beside the new one, and Claude Code would offer both; remove it here.
#
# Runs once (on first apply after this script lands); re-run by clearing its hash from
# ~/.config/chezmoi/chezmoistate.boltdb or with `chezmoi state delete-bucket --bucket=scriptState`.

OLD="${HOME}/.claude/skills/using-zellij-docs"
if [[ -d "$OLD" ]]; then
    rm -rf "$OLD"
    echo "Removed orphaned $OLD (replaced by the using-zellij skill)."
fi
