-- Keyboard-shortcut cheat-sheet HUD.
--
-- Renders the curated data in shortcuts.lua as a multi-column HTML panel inside a borderless,
-- non-activating hs.webview. (The workspace HUD uses hs.alert, which is centered plain text and
-- can't do columns/tables — a webview gives real CSS layout.) Toggled by a global hotkey wired in
-- init.lua, or by the `hammerspoon://shortcuts` URL event.

local M = {}

local sections = require("shortcuts")

local PANEL_W, PANEL_H = 1180, 820

local function escapeHtml(s)
    return (s:gsub("[&<>]", { ["&"] = "&amp;", ["<"] = "&lt;", [">"] = "&gt;" }))
end

local function buildHtml()
    local blocks = {}
    for _, section in ipairs(sections) do
        local rows = {}
        for _, item in ipairs(section.items) do
            local cls = item.todo and ' class="todo"' or ""
            rows[#rows + 1] = string.format(
                '<tr%s><td class="k"><kbd>%s</kbd></td><td class="d">%s</td></tr>',
                cls, escapeHtml(item.keys), escapeHtml(item.desc))
        end
        blocks[#blocks + 1] = string.format(
            "<section><h2>%s</h2><table>%s</table></section>",
            escapeHtml(section.title), table.concat(rows))
    end

    return [[<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body { background: transparent; }
    body {
        font-family: -apple-system, "SF Pro Text", system-ui, sans-serif;
        color: #c0caf5;
        padding: 20px;
    }
    .panel {
        background: rgba(20, 22, 30, 0.93);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 22px 26px 8px;
        box-shadow: 0 24px 70px rgba(0, 0, 0, 0.55);
        column-count: 3;
        column-gap: 30px;
    }
    .title {
        column-span: all;
        font-size: 13px; letter-spacing: 3px; text-transform: uppercase;
        color: #7aa2f7; margin-bottom: 16px;
    }
    section { break-inside: avoid; margin-bottom: 18px; }
    h2 {
        font-size: 11px; color: #9aa5ce; text-transform: uppercase; letter-spacing: 1px;
        margin-bottom: 6px; padding-bottom: 3px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.07);
    }
    table { width: 100%; border-collapse: collapse; }
    td { padding: 2px 0; vertical-align: top; font-size: 13.5px; line-height: 1.55; }
    td.k { white-space: nowrap; padding-right: 12px; }
    td.d { color: #c0caf5; }
    kbd {
        font-family: "JetBrainsMono Nerd Font", "JetBrains Mono", ui-monospace, monospace;
        font-size: 11.5px;
        background: rgba(122, 162, 247, 0.14); color: #c8d3f5;
        border: 1px solid rgba(122, 162, 247, 0.30); border-radius: 6px;
        padding: 1px 7px; white-space: nowrap;
    }
    tr.todo td.d { color: #e0af68; }
    tr.todo kbd { color: #e0af68; border-color: rgba(224, 175, 104, 0.35);
                  background: rgba(224, 175, 104, 0.12); }
    </style></head><body><div class="panel">
    <div class="title">⌨  Keyboard Shortcuts</div>
    ]] .. table.concat(blocks) .. [[</div></body></html>]]
end

local webview = nil
local escHotkey = nil
local visible = false

local function panelRect()
    local f = hs.screen.mainScreen():frame()
    return {
        x = f.x + (f.w - PANEL_W) / 2,
        y = f.y + (f.h - PANEL_H) / 2,
        w = PANEL_W,
        h = PANEL_H,
    }
end

local function hide()
    if webview then webview:hide() end
    if escHotkey then escHotkey:disable() end
    visible = false
end

local function show()
    if not webview then
        webview = hs.webview.new(panelRect())
            :windowStyle({ borderless = true, nonactivating = true })
            :level(hs.canvas.windowLevels.floating)
            :transparent(true)
            :allowTextEntry(false)
    end
    -- Recompute position (the focused screen may have changed) and rebuild the HTML so edits to
    -- shortcuts.lua show up without a manual reload once Hammerspoon has re-required it.
    webview:frame(panelRect()):html(buildHtml()):show()

    if not escHotkey then
        escHotkey = hs.hotkey.new({}, "escape", hide)
    end
    escHotkey:enable()
    visible = true
end

function M.toggle()
    if visible then hide() else show() end
end

return M
