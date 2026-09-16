# iTerm2: profiles and colour palettes

Two directories live here, and the link between them is invisible in the files themselves.
This page explains how a palette gets into a profile, which palette is applied today, and how the
  apps that run inside iTerm2 are expected to pick up its colours.

## What is here

- `DynamicProfiles/`: iTerm2 [dynamic profiles](https://iterm2.com/documentation-dynamic-profiles.html),
    one JSON file per profile, deployed to `~/Library/Application Support/iTerm2/DynamicProfiles/` on
    macOS.
    `zellij.json` is the base profile.
    The `karl-<host>.json` and `work-wifi-longview.json` files are remote-host profiles that SSH
    somewhere; which of them deploy on a given machine is decided in
    [`.chezmoiignore`](../../../.chezmoiignore) (never the one for the host you are on, none of them
    on CMS workstations).
- `color-schemes/`: `.itermcolors` palette files (iTerm2 colour presets) fetched from
    <https://iterm2colorschemes.com/>.
    They are a stash for importing into iTerm2; nothing reads them at runtime.

## How a palette gets into a profile

iTerm2 never references a `.itermcolors` file from a profile.
Applying a preset copies its 26 colours (`Ansi 0 Color` through `Ansi 15 Color`, `Background Color`,
  `Foreground Color`, `Cursor Color`, `Selection Color`, and so on) into the profile's own keys.
The base profile has *Use separate colors for light and dark mode* on, so each colour exists three
  times in `zellij.json`:

- `<name> (Dark)`: used while macOS is in dark mode.
- `<name> (Light)`: used while macOS is in light mode.
- `<name>` with no suffix: the legacy single-mode value kept for older iTerm2 versions; it mirrors
    the light set.

To change the palette:

1. In iTerm2, open Settings → Profiles → *zellij* → Colors → Color Presets… → Import…,
    and pick a file from `color-schemes/`.
2. Set the *Editing* control to the mode you want to change (dark or light), then choose the
    imported preset from the Color Presets… menu.
    iTerm2 rewrites the `(Dark)` or `(Light)` keys in the deployed `zellij.json`.
3. Back in this repo, run
    `chezmoi re-add "$HOME/Library/Application Support/iTerm2/DynamicProfiles/zellij.json"`,
    check that the resulting diff touches only colour keys, and commit.

Only `zellij.json` should ever carry colours.
The remote-host profiles set `"Dynamic Profile Parent Name": "zellij"` and hold no colour keys, so
  they inherit whatever the base profile has (iTerm2 fills in "any attributes you don't explicitly
  specify" from the parent).
Do not apply a preset to a remote-host profile, and do not hand-edit colour keys in any profile JSON.

## What is applied today

| Mode  | Palette                          | Source                                            |
| ----- | -------------------------------- | ------------------------------------------------- |
| Dark  | Tokyo Night Storm                | `color-schemes/tokyonight-storm.itermcolors`      |
| Light | Regular (iTerm2 built-in preset) | iTerm2's bundled presets, not a file in this repo |

`tokyonight.itermcolors` and `tokyonight_moon.itermcolors` are stashed for trying out; neither is
  applied anywhere.

To check which palette the dark set currently matches, compare the 26 colours against a palette file
  (run from this directory in the repo or from the deployed one under `~/Library`):

```bash
plutil -convert json -o /tmp/pal.json color-schemes/tokyonight-storm.itermcolors
jq -n --slurpfile pal /tmp/pal.json --slurpfile prof DynamicProfiles/zellij.json '
  def hex: ((."Red Component"*255|round)*65536 + (."Green Component"*255|round)*256
            + (."Blue Component"*255|round));
  ($prof[0].Profiles[0]) as $Z
  | [ $pal[0] | to_entries[] | select((.value|hex) == ($Z[.key + " (Dark)"] | hex)) ]
  | "\(length) of 26 dark colours match"'
```

## Apps inside the terminal

The terminal palette is the single source of truth for colours.
An app that draws with the 16 ANSI colours inherits whatever iTerm2 is showing, follows a palette
  change automatically, and switches with light and dark mode for free.
An app that ships its own truecolor theme has to be kept in step by hand.
So prefer an ANSI-based theme where the app offers one, and pick the matching Tokyo Night variant
  where it does not.

| App         | Colours                                 | Config                                         |
| ----------- | --------------------------------------- | ---------------------------------------------- |
| Claude Code | ANSI, `theme: "dark-ansi"`              | `private_dot_claude/modify_settings.json.tmpl` |
| Helix       | ANSI, `theme = "base16_terminal"`       | `dot_config/helix/config.toml`                 |
| Zellij      | truecolor, `theme "tokyo-night-storm"`  | `dot_config/zellij/config.kdl.tmpl`            |
| Starship    | truecolor, hard-coded Tokyo Night hex   | `dot_config/starship*.toml`                    |

Zellij and Starship follow neither a palette change nor light mode.
If the iTerm2 palette moves away from Tokyo Night Storm, update those two by hand.
