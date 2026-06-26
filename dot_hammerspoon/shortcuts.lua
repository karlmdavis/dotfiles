-- Curated keyboard-shortcut cheat sheet — the single source of truth for the HUD panel
-- (rendered by shortcuts_hud.lua, toggled with ⌥⇧/). Edit this file when bindings change;
-- a fresh `chezmoi apply` reloads Hammerspoon automatically.
--
-- Each entry is a section { title, items }; each item is { keys, desc, todo? }. `keys` is shown
-- as a monospace chip verbatim. Set `todo = true` for values that live in an app's GUI (not in
-- this repo) and still need to be confirmed — they render highlighted so they're obviously unverified.
--
-- Sources: AeroSpace from ~/.aerospace.toml (dot_aerospace.toml.tmpl); display hotkeys from
-- init.lua; Zellij from the v0.44 defaults (config.kdl sets no custom keybinds); readline set is
-- the emacs-mode bindings shared by zsh/bash/nushell and macOS text fields.

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
            { keys = "Esc B / F", desc = "Back / forward one word" },
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
}
