#!/usr/bin/env bash
set -euo pipefail

# The superpowers plugin (superpowers@superpowers-marketplace) was retired on 2026-09-16: its skills
# were overtaken by Claude Code's own features and its SessionStart hook injected ~2k tokens into
# every session. Removing it from `enabledPlugins` and from the required marketplaces only stops
# chezmoi re-adding it; Claude Code keeps the installed plugin, its cache, and the marketplace
# clone until told otherwise, so uninstall them here on already-applied systems.
#
# Runs once (on first apply after this script lands); re-run by clearing its hash from
# ~/.config/chezmoi/chezmoistate.boltdb or with `chezmoi state delete-bucket --bucket=scriptState`.

if command -v claude >/dev/null 2>&1; then
    if claude plugin uninstall superpowers@superpowers-marketplace >/dev/null 2>&1; then
        echo "Uninstalled the superpowers plugin."
    fi
    if claude plugin marketplace remove superpowers-marketplace >/dev/null 2>&1; then
        echo "Removed the superpowers-marketplace marketplace."
    fi
fi

# Belt and braces: whatever the CLI left behind (or if it was not on PATH).
for dir in \
    "${HOME}/.claude/plugins/cache/superpowers-marketplace" \
    "${HOME}/.claude/plugins/marketplaces/superpowers-marketplace"; do
    if [[ -d "$dir" ]]; then
        rm -rf "$dir"
        echo "Removed leftover $dir."
    fi
done
