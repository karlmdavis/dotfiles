# iTerm2 profiles and palettes

Before changing colours, themes, or palettes here, or for anything that runs inside iTerm2 (zellij,
  starship, Helix, Claude Code), read [`README.md`](./README.md) in this directory.
It explains how `.itermcolors` files reach the dynamic profiles (iTerm2 copies the colours in;
  nothing references the files), why only `zellij.json` carries colour keys, which palette is
  applied today, and which apps follow the terminal palette versus carry their own theme.
Never hand-edit colour keys in a profile JSON: apply a preset in iTerm2, then `chezmoi re-add` the
  file.
