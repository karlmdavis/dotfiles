require("hs.ipc")
hs.autoLaunch(true)

-- Auto-reload this config whenever a .lua file in the config dir changes on disk (e.g. after
-- `chezmoi apply`), so edits take effect without a manual reload. A long-running Hammerspoon
-- otherwise keeps executing the config it loaded at startup — which is exactly why the
-- workspace-hint handler didn't take effect after it was added.
configWatcher = hs.pathwatcher.new(hs.configdir, function(paths)
    for _, p in ipairs(paths) do
        if p:sub(-4) == ".lua" then
            hs.reload()
            return
        end
    end
end):start()

hs.urlevent.bind("workspace", function(_, params)
    -- `name` already arrives with its emoji prepended (see hud-display-workspace-name.py). When a
    -- `hint` is present, show it as a smaller, dimmer second line below the name (and linger a bit
    -- longer so it's readable); otherwise keep the original single-line flash.
    local name = params.name or ""
    if params.hint and params.hint ~= "" then
        local text = hs.styledtext.new(name, { font = { size = 36 }, color = { white = 1 } })
            .. hs.styledtext.new("\n" .. params.hint, { font = { size = 20 }, color = { white = 0.6 } })
        hs.alert.show(text, { strokeWidth = 0 }, nil, 1.5)
    else
        hs.alert.show(name, { textSize = 36, strokeWidth = 0 }, nil, 0.8)
    end
end)

-- Resolution switching: 4K desk mode vs windowed Screen-Sharing mode.
local alertStyle = { textSize = 36, strokeWidth = 0 }

-- The 14" MacBook Pro M3 ("More Space" = 1800x1169 logical) Screen Sharing client,
-- showing the remote screen at ACTUAL SIZE (1:1, for sharpest text and least overhead),
-- leaves ~1800 x 1117 logical pts of usable window after the menu bar (~24) + title bar
-- (~28). Any "looks like" mode that fits inside that box displays 1:1 with room for the
-- client chrome. This window budget is the only fixed constraint; the actual resolution
-- is chosen dynamically from whatever the active display offers (see pickFittingScaledMode).
local CLIENT_MAX_W, CLIENT_MAX_H = 1800, 1117

-- Returns (displayID, rawOutput) from a single `displayplacer list` call. The displayID
-- is the combined `id1+id2` apply string when mirrored, or the lone built-in id when not.
local function getDisplayInfo()
    local output = hs.execute("/opt/homebrew/bin/displayplacer list", true)
    local id
    for match in output:gmatch('\ndisplayplacer "id:([^%s]+)') do
        id = match  -- last match = the "apply current arrangement" command at the end
    end
    return id, output
end

-- From the MAIN display's block, pick the largest scaling:on ("looks like") mode that
-- fits the client window. Scoped to the main block (found by splitting per-display and
-- locating the "main display" marker, order-independent) so mirrored setups don't mix
-- the built-in (16:10) and external (16:9) mode lists. For scaling:on modes, res:WxH IS
-- the logical "looks like" size. Returns a "WxH" string, or nil if nothing fits.
local function pickFittingScaledMode(output)
    local mainBlock
    for block in (output .. "\nPersistent screen id:"):gmatch("(Persistent screen id:.-)\nPersistent screen id:") do
        if block:find("main display", 1, true) then
            mainBlock = block
        end
    end
    if not mainBlock then return nil end

    local bestW, bestH, bestArea
    for w, h in mainBlock:gmatch("res:(%d+)x(%d+)[^\n]-scaling:on") do
        w, h = tonumber(w), tonumber(h)
        if w <= CLIENT_MAX_W and h <= CLIENT_MAX_H and (not bestArea or w * h > bestArea) then
            bestW, bestH, bestArea = w, h, w * h
        end
    end
    if bestW then return bestW .. "x" .. bestH end
    return nil
end

local function switchResolution(mode)
    local displayID, output = getDisplayInfo()
    if not displayID then
        hs.alert.show("No display found", alertStyle, nil, 2)
        return
    end

    local label, args
    if mode == "4k" then
        label = "4K"
        args = " res:3840x2160 hz:30 color_depth:8"
    else
        -- Largest scaled mode that fits the 14" Screen Sharing window (1:1). Falls back to
        -- 1280x800 if parsing ever finds nothing. hz is omitted on purpose: displayplacer
        -- auto-applies the highest supported rate, so this stays valid across the built-in
        -- panel and any docked monitor regardless of their available refresh rates.
        local res = pickFittingScaledMode(output) or "1280x800"
        label = 'Screen Sharing (windowed, from 14" Macbook Pro M3) — ' .. res
        args = " res:" .. res .. " color_depth:8 scaling:on"
    end

    hs.alert.show("Switching to " .. label .. "…", alertStyle, nil, 2)

    hs.timer.doAfter(0.5, function()
        local cmd = '/opt/homebrew/bin/displayplacer "id:' .. displayID .. args .. '"'
        local ok = os.execute(cmd)
        hs.timer.doAfter(2, function()
            if ok then
                hs.alert.show(label, alertStyle, nil, 10)
            else
                hs.alert.show(label .. " unavailable", alertStyle, nil, 10)
            end
        end)
    end)
end

hs.hotkey.bind({"ctrl", "alt", "cmd"}, "4", function() switchResolution("4k") end)
hs.hotkey.bind({"ctrl", "alt", "cmd"}, "1", function() switchResolution("screenshare") end)
