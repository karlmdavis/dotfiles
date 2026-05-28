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

## Run-scripts: `.chezmoiscripts/` vs `private_dot_*/` vs repo root

Three places a script can live:

- **`.chezmoiscripts/<name>`** — execution-only.
    Scripts that should RUN on `chezmoi apply` but should NOT exist as files on the target
    afterwards.
    Examples in this repo: cleanup of state left by removed features, package-bundle
    installers (`brew bundle`, `apt install`), toolchain installers (`rustup-init`).
- **`private_dot_local/bin/executable_<name>`** (or `private_dot_*/...` generally) —
    installed artifact.
    Scripts and configs that the user (or a shell hook, or another script) calls by path at
    runtime.
    The file IS supposed to exist on the target system.
- **Repo root `run_*`** — discouraged.
    Root is for top-level config (`.chezmoi.toml.tmpl`, `.chezmoiignore`, `.chezmoidata/`,
    `.chezmoitemplates/`, `dot_*` mappings).
    Prefer `.chezmoiscripts/` for run-only scripts so the root stays scannable.

**Decision:** does this leave a file on the target that something else uses?
  Yes → `private_dot_*/...`.
  No → `.chezmoiscripts/`.

**Naming conventions** for `.chezmoiscripts/`: `run_`, `run_once_`, `run_onchange_`, with
  optional `_before_` / `_after_` apply modifiers and optional `.tmpl` suffix.
Use date prefixes (`run_once_after_YYYY-MM-DD-name.sh`) for one-time cleanup scripts so the
  ordering and provenance are obvious at a glance.

## Cleanup debt: pair feature removal with a cleanup script

When removing a feature that wrote state, logs, caches, or generated files at the target,
  add a dated
  `.chezmoiscripts/run_once_after_YYYY-MM-DD-cleanup-<feature>.sh.tmpl` in the same commit so
  already-applied systems get cleaned up on next `chezmoi apply`.

**Important:** chezmoi does NOT automatically remove files on the target when their source
  goes away.
Both chezmoi-installed trees (`~/.local/lib/<feature>/` and similar) AND ad-hoc state
  (`~/.local/state/<feature>/`, generated certs, caches, logs) need to be removed by the
  cleanup script.
This was confirmed empirically when removing wkflw-ntfy: deleting
  `private_dot_local/lib/wkflw-ntfy/` from source did not remove `~/.local/lib/wkflw-ntfy/`
  on the next apply.

## When to update the Repository Map

Update the README only when:

- A new top-level directory is added or removed at the repo root.
- A new app starts being managed, or an existing app's primary config path changes.
- An existing app or embedded mini-project is removed.
- A category is added, renamed, or removed.

Do NOT update for routine file additions inside an existing app or sub-tree — that's exactly
  the churn the elisions were designed to avoid.
