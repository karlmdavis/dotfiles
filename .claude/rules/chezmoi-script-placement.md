# Where to put chezmoi scripts

This repo has three places a script can live, and each has distinct semantics.
Pick the right one when adding a new script.

## `.chezmoiscripts/<name>` — execution-only

Use for scripts that should RUN on `chezmoi apply` but should NOT exist as files in the target
  home directory afterwards.
Examples in this repo:

- Cleanup of state left by removed features (e.g. removing `~/.local/state/foo/` after the `foo`
    feature is torn down).
- Package-bundle installers (`brew bundle`, `apt install`).
- Toolchain installers (`rustup-init`).

Naming conventions still apply: `run_`, `run_once_`, `run_onchange_`, with optional `_before_` /
  `_after_` apply modifiers and optional `.tmpl` suffix.
Use date prefixes (`run_once_after_YYYY-MM-DD-name.sh`) for one-time cleanup scripts so the
  ordering and provenance are obvious at a glance.

## `private_dot_local/bin/executable_<name>` or `private_dot_*/...` — installed artifact

Use for scripts and configs that the user (or a shell hook, or another script) calls by path at
  runtime.
The file IS supposed to exist on the target system.

## Repo root `run_*` — discouraged

Repo root is for top-level config (`.chezmoi.toml.tmpl`, `.chezmoiignore`, `.chezmoidata/`,
  `.chezmoitemplates/`, `dot_*` mappings).
Prefer `.chezmoiscripts/` for run-only scripts so the root stays scannable.

## When in doubt

Ask: "does this leave a file on the target that something else uses?"

- Yes → `private_dot_*/...`.
- No → `.chezmoiscripts/`.

## Cleanup debt: pair feature removal with a cleanup script

When removing a feature that wrote state, logs, caches, or generated files OUTSIDE chezmoi's
  tracked tree, add a dated
  `.chezmoiscripts/run_once_after_YYYY-MM-DD-cleanup-<feature>.sh` in the same commit
  so already-applied systems get cleaned up on next `chezmoi apply`.

Chezmoi-tracked files (anything originally installed from `private_dot_*/...` or `dot_*`) are
  removed automatically when the source goes away.
Anything else — state dirs, generated certs, caches, logs — is not.
