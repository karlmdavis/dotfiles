# File placement

When adding, moving, or renaming files in this repo, align with the "Repository Map" section
  of the top-level [`README.md`](../../README.md).

That section is the single source of truth.
It has three parts:

- An elided `ls`-tree of **repo meta and chezmoi meta** — every entry is detailed.
- A short note on the **chezmoi source-state prefixes** (`dot_`, `private_dot_`,
    `executable_`, `.tmpl`).
- A categorized **Apps / Configs Managed** list — one entry per managed app, linking to its
    primary config path with `see also:` for important secondaries.
    App-internal directory contents are NOT enumerated; `ls -R` the linked path when you need
    detail.

## What to do

1. **Skim the Repository Map first** for any addition that isn't an obvious in-place edit of
    an existing file.
    Thirty seconds spent reading saves a rewrite later when a new file lands in the wrong
    place.
2. **For app config changes**, find the app on the Apps list and place the new file alongside
    its primary path.
    `ls -R` the linked directory if you need to see what's already there.
3. **For repo-meta or chezmoi-meta changes**, follow the tree's annotations.
4. **If nothing fits, ask before inventing a new entry.**
    A new app on the Apps list, a new category, or a new top-level repo-meta directory are
    all structural decisions; an extra file under an existing entry is not.
5. **Use the chezmoi prefix grammar** (`dot_`, `private_dot_`, `executable_`, `.tmpl`) —
    described in the Repository Map.
    A wrong prefix means chezmoi installs the file in the wrong place or with the wrong
    permissions.

## When to update the Repository Map

Update the README only when:

- A new top-level directory is added or removed at the repo root.
- A new app starts being managed, or an existing app's primary config path changes.
- An existing app or embedded mini-project is removed.
- A category is added, renamed, or removed.

Do NOT update for routine file additions inside an existing app or sub-tree — that's exactly
  the churn the elisions were designed to avoid.

## Related rules

- [`chezmoi-script-placement.md`](./chezmoi-script-placement.md) — narrower rule specifically
    for run-scripts (`.chezmoiscripts/` vs `private_dot_*/` vs repo root).
