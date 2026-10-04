-- Curated keyboard-shortcut cheat sheet — the single source of truth for the HUD panel
-- (rendered by shortcuts_hud.lua, toggled with ⌥⇧/). Edit this file when bindings change;
-- a fresh `chezmoi apply` reloads Hammerspoon automatically.
--
-- Each entry is a section { title, items }; each item is { keys, desc, todo? }. `keys` is shown
-- as a monospace chip verbatim. Set `todo = true` for values that live in an app's GUI (not in
-- this repo) and still need to be confirmed — they render highlighted so they're obviously unverified.
--
-- Sources: AeroSpace from ~/.aerospace.toml (dot_aerospace.toml.tmpl); display hotkeys from
-- init.lua; Zellij from the v0.44 defaults (config.kdl only unbinds Alt+Left/Right); readline set
-- is the emacs-mode bindings shared by zsh/bash/nushell and macOS text fields, except word
-- movement: ⌥←/⌥→ is what survives AeroSpace (which owns ⌥+letter) and is bound explicitly in
-- dot_zshrc.tmpl, dot_bashrc.tmpl, and helix/config.toml (nushell and Claude Code have it built
-- in). Helix from the 25.07 default keymap; its keys are case-sensitive, so ⇧ marks a capital.

return {
    {
        title = "AeroSpace · Windows",
        items = {
            { keys = "⌥ H J K L", desc = "Focus pane: left / down / up / right" },
            { keys = "⌥⇧ H J K L", desc = "Move window" },
            { keys = "⌃⌥⇧ H J K L", desc = "Join with neighbor" },
            { keys = "⌥ /", desc = "Toggle tiles (horizontal/vertical)" },
            { keys = "⌥ ,", desc = "Accordion layout" },
            { keys = "⌥ -  ⌥ =", desc = "Shrink / grow pane" },
            { keys = "⌥ 0", desc = "Toggle fullscreen" },
        },
    },
    {
        title = "AeroSpace · Workspaces",
        items = {
            { keys = "⌥ 1–9 / A–Z", desc = "Go to workspace" },
            { keys = "⌥⇧ 1–9 / A–Z", desc = "Move window to workspace" },
            { keys = "⌥ Tab", desc = "Previous workspace (back-and-forth)" },
            { keys = "⌥⇧ Tab", desc = "Move workspace to next monitor" },
        },
    },
    {
        title = "AeroSpace · Service (⌥⇧ ; first)",
        items = {
            { keys = "R", desc = "Reset / flatten layout" },
            { keys = "F", desc = "Toggle floating / tiling" },
            { keys = "⌫", desc = "Close all windows but current" },
            { keys = "Esc", desc = "Reload config & exit service mode" },
        },
    },
    {
        title = "Display & this panel",
        items = {
            { keys = "⌃⌥⌘ 4", desc = "4K desk mode" },
            { keys = "⌃⌥⌘ 1", desc = "Screen-Sharing windowed mode" },
            { keys = "⌃⌥⌘⇧ P", desc = "Toggle remote-keyboard passthrough (auto on Screen Sharing)" },
            { keys = "⌥⇧ /", desc = "Toggle this shortcut panel · Esc closes" },
        },
    },
    {
        title = "Global app hotkeys",
        items = {
            { keys = "⌥ Space", desc = "Todoist · Quick Add task" },
            { keys = "⌥⇧ Space", desc = "Todoist · Quick Ramble" },
            { keys = "⌃⇧ Space", desc = "ChatGPT · Chat Bar" },
            { keys = "⌥ ⌥", desc = "Claude · Quick Access (tap ⌥ twice)" },
            { keys = "⌘⇧ Space", desc = "1Password · Quick Access" },
        },
    },
    {
        title = "Zellij (mode → keys)",
        items = {
            { keys = "⌃ P", desc = "Pane: N new · D/R split · X close · F full · W float" },
            { keys = "⌃ T", desc = "Tab: N new · X close · 1–9 jump · Tab toggle" },
            { keys = "⌃ N", desc = "Resize: H J K L grow · ⇧+HJKL shrink" },
            { keys = "⌃ S", desc = "Scroll: S search · E edit scrollback" },
            { keys = "⌃ O", desc = "Session: D detach · W manager" },
            { keys = "⌃ G", desc = "Lock toggle · ⌃ Q quit" },
        },
    },
    {
        title = "Line editing (shell & text fields)",
        items = {
            { keys = "⌃ A  ⌃ E", desc = "Start / end of line" },
            { keys = "⌃ B  ⌃ F", desc = "Back / forward one char" },
            { keys = "⌥ ←  ⌥ →", desc = "Back / forward one word" },
            { keys = "⌃ W", desc = "Delete word before cursor" },
            { keys = "⌃ U", desc = "Delete to start of line" },
            { keys = "⌃ K", desc = "Delete to end of line" },
            { keys = "⌃ Y", desc = "Paste last deletion (yank)" },
            { keys = "⌃ D", desc = "Delete char under cursor / EOF" },
            { keys = "⌃ R", desc = "Reverse history search" },
            { keys = "⌃ P  ⌃ N", desc = "Previous / next history" },
            { keys = "⌃ T", desc = "Transpose characters" },
            { keys = "⌃ L", desc = "Clear screen" },
        },
    },
    {
        title = "Helix · Modes & motions",
        items = {
            { keys = "Esc", desc = "Normal mode" },
            { keys = "I  A", desc = "Insert before / after selection" },
            { keys = "⇧I  ⇧A", desc = "Insert at line start / end" },
            { keys = "O  ⇧O", desc = "Open line below / above" },
            { keys = "V", desc = "Select (extend) mode" },
            { keys = ":", desc = "Command mode · :w write · :q quit" },
            { keys = "H J K L", desc = "Left / down / up / right" },
            { keys = "W  B  E", desc = "Next word / previous word / word end" },
            { keys = "⌥ ←  ⌥ →", desc = "Back / forward one word (insert mode)" },
            { keys = "F  T + char", desc = "Jump to / until char" },
            { keys = "G G  G E", desc = "Start / end of file" },
            { keys = "G H  G L", desc = "Start / end of line" },
            { keys = "⌃ D  ⌃ U", desc = "Half page down / up" },
        },
    },
    {
        title = "Helix · Select & edit",
        items = {
            { keys = "X", desc = "Select line (repeat to extend)" },
            { keys = "%", desc = "Select whole file" },
            { keys = "M I  M A + obj", desc = "Select inside / around: W word · ( parens · F function" },
            { keys = ";", desc = "Collapse selection to cursor" },
            { keys = "⇧C  ,", desc = "Add cursor below / keep only primary" },
            { keys = "D  C", desc = "Delete / change selection" },
            { keys = "Y  P  ⇧P", desc = "Yank / paste after / paste before" },
            { keys = "U  ⇧U", desc = "Undo / redo" },
            { keys = ">  <", desc = "Indent / unindent" },
            { keys = "/  N  ⇧N", desc = "Search / next / previous" },
        },
    },
    {
        title = "Helix · Space & goto",
        items = {
            { keys = "Space F  Space B", desc = "File picker / buffer picker" },
            { keys = "Space /", desc = "Search across workspace" },
            { keys = "Space Y  Space P", desc = "Yank to / paste from system clipboard" },
            { keys = "Space K", desc = "Show docs for symbol (LSP hover)" },
            { keys = "Space ?", desc = "Command palette" },
            { keys = "G D  G R", desc = "Go to definition / references" },
            { keys = "⌃ W", desc = "Window: V S split · H J K L focus · Q close" },
        },
    },
}
