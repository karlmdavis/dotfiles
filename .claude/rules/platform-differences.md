# Platform differences

This repo manages dotfiles for macOS (`mantis`) and Ubuntu (`eddings`, `krout`).
When an app, tool, or config differs across those platforms, pick the right mechanism
  from the four scenarios below.
Companion to [`file-placement.md`](file-placement.md) — that one says **where** a file
  goes; this one says **how to gate it** when the answer depends on the OS.

## The four scenarios

### 1. App is on one OS only

Examples: iTerm2, Hammerspoon, AeroSpace (macOS-only); sway, i3 (Linux-only).

- The source file lives at the chezmoi-encoded form of the real path the app reads
    (e.g. `private_Library/private_Application Support/iTerm2/...` →
    `~/Library/Application Support/iTerm2/...`).
- Exclude it on the other OS via [`.chezmoiignore`](../../.chezmoiignore) inside
    `{{ if ne .chezmoi.os "darwin" }} ... {{ end }}` (and the symmetric linux block).
- **Prefer a blanket directory ignore** (`Library/`, `.config/sway/`) over per-leaf
    ignores.
    Future additions are auto-covered, and you avoid the **empty-parent-dir gotcha**:
      chezmoi creates parent directories for managed source entries even when every
      leaf inside is ignored.
    A per-leaf ignore of `Library/Application Support/nushell/config.nu` leaves an
      empty `~/Library/Application Support/nushell/` behind on Linux; a blanket
      `Library/` does not.
- `.chezmoiignore` patterns match the **target path** relative to `~/`, not the source
    path.
    Write `Library/...`, not `private_Library/...`.

### 2. Same app, different config path per OS

Canonical example: nushell.
macOS reads `~/Library/Application Support/nushell/config.nu`; Linux reads
  `~/.config/nushell/config.nu`.

- Create one thin source file at each OS's real path, each containing
    `{{- template "config.nu" . -}}` to pull in a shared partial from
    [`.chezmoitemplates/`](../../.chezmoitemplates/).
- Exclude each OS-specific path on the other OS in `.chezmoiignore`'s symmetric blocks.
    macOS sees only the `Library/` form; Linux sees only the `.config/` form; both
      render the same partial.
- Examples already in the repo:
    [`dot_config/nushell/config.nu.tmpl`](../../dot_config/nushell/config.nu.tmpl) and
    [`private_Library/private_Application Support/nushell/config.nu.tmpl`](../../private_Library/private_Application%20Support/nushell/config.nu.tmpl)
    both `template "config.nu"` from
    [`.chezmoitemplates/config.nu`](../../.chezmoitemplates/config.nu).
    The same pattern repeats for `local.nu`.

### 3. Same path everywhere, content differs by OS

Examples: [`dot_gitconfig.tmpl`](../../dot_gitconfig.tmpl) picks `/opt/homebrew/bin/gh`
  vs `/home/linuxbrew/.linuxbrew/bin/gh`;
  [`.chezmoitemplates/shell-env.sh`](../../.chezmoitemplates/shell-env.sh) sets the
  Homebrew prefix.

- Use a `.tmpl` file with inline conditionals:
    `{{ if eq .chezmoi.os "darwin" }} ... {{ else if eq .chezmoi.osRelease.id "ubuntu" }} ... {{ end }}`.
- No `.chezmoiignore` entry needed — the file applies everywhere; only its content
    branches.

### 4. Tool isn't on every system within a platform

Examples: SDKMAN, Docker, JetBrains tools, GUI apps that you only have on some machines.

- Use the per-machine local files: `~/.config/shell/env.local.sh` for bash/zsh, nushell
    `local.nu`.
    The shared
      [`shell-env.sh`](../../.chezmoitemplates/shell-env.sh) and
      [`config.nu`](../../.chezmoitemplates/config.nu) source these when present.
- Do **not** add such tools to
    [`.chezmoidata/system_packages_autoinstall.yaml`](../../.chezmoidata/system_packages_autoinstall.yaml)
    or to the shared shell-env templates.
    Those are for things that ship on every system of a given platform.

## Cross-cutting notes

### Cross-shell duality

PATH and tool setup lives in BOTH
  [`.chezmoitemplates/shell-env.sh`](../../.chezmoitemplates/shell-env.sh) (bash/zsh) and
  [`.chezmoitemplates/config.nu`](../../.chezmoitemplates/config.nu) (nu).
When adding a tool that ships on every system, update both files.
CLAUDE.md's "Cross-shell PATH/utility setup" section is the canonical write-up of this
  invariant.

### Per-host / per-role exclusion (beyond OS)

Sometimes a file should apply on only *some* machines of the same OS — keyed on the host
  itself, or on whether it's a personal vs CMS (work) box.
Gate these in [`.chezmoiignore`](../../.chezmoiignore) (it's a template) using the built-in
  `.chezmoi.hostname` and the repo's `.isCMS` boolean — no new init prompt is needed for
  either.
The worked example is the macOS iTerm2 block: it self-excludes the profile for the host you're
  on with `.../DynamicProfiles/karl-{{ "{{" }} .chezmoi.hostname {{ "}}" }}.json` (so mantis
  never gets a profile that SSHes into mantis), and under `{{ "{{" }} if .isCMS {{ "}}" }}` it
  excludes every personal remote-host profile so the work machine can't reach personal systems.
Reclassifying an already-applied file this way incurs cleanup debt (see below) — pair it with a
  cleanup script gated on the same condition.

### Cleanup debt

When you reclassify a file from "applied here" to "ignored here" — or move a managed
  file to a new target path — already-applied systems will keep the old file or
  directory until something removes it.
Pair the change with a dated
  `.chezmoiscripts/run_once_after_YYYY-MM-DD-cleanup-<feature>.sh.tmpl` per the
  [`file-placement.md` "Cleanup debt"](file-placement.md) convention so the next
  `chezmoi apply` on each system clears the debris.
