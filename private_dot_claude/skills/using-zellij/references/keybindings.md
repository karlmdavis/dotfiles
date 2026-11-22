# Keybinding, layout, and config questions

The commands were checked on Zellij 0.46.0; if one fails, follow "When a command here fails" in
  `SKILL.md`.

- The config (`~/.config/zellij/config.kdl`) is close to default: a theme, session serialization,
    nushell as the default shell, no nested-session prompt, and one `unbind` of `Alt Left` and
    `Alt Right`.
    So the default preset applies apart from those two keys.
    Read the file (it is short) in case this has changed.
- Look a key up in the default preset with
    `zellij setup --dump-keybinds default | grep -n -i <word>`, searching for the action
    (`Lock`, `SwapLayout`, `NewPane`, `Resize`); never name a key from memory.
    In the dump, `{primary}` is `Ctrl` and `{secondary}` is `Alt`, and each binding sits inside the
    mode it applies in, so give the mode with the key.
- Swap layouts (`Alt [` and `Alt ]`) cycle through presets, not through a history of earlier
    layouts, and no preset makes a stack out of two panes.
    To stack existing panes: `zellij action stack-panes -- terminal_<a> terminal_<b>`.
- Zellij handles its own bindings before the program in the pane sees a key.
    When a key "does nothing" in nushell, Helix, or Claude Code, look for it in Zellij's bindings
    first.
    One known overlap: `Ctrl g` is both Zellij's default lock key and Claude Code's
    external-editor key; Claude Code also opens the external editor on `Ctrl e`, `Ctrl e`, which
    Zellij leaves alone.
- Edit the chezmoi source, `dot_config/zellij/config.kdl.tmpl` in the dotfiles repo, not the file in
    `~`.
    Keybinding changes have applied to running sessions without a restart.
