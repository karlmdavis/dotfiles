require("hs.ipc")
hs.autoLaunch(true)

hs.urlevent.bind("workspace", function(_, params)
    hs.alert.show(params.name, { textSize = 36, strokeWidth = 0 }, nil, 0.8)
end)

-- Resolution switching (4K desk mode vs 1080p VNC mode)
local alertStyle = { textSize = 36, strokeWidth = 0 }

local function getMainDisplayID()
    local output = hs.execute("/opt/homebrew/bin/displayplacer list", true)
    local id
    for match in output:gmatch('\ndisplayplacer "id:([^%s]+)') do
        id = match
    end
    return id
end

local function switchResolution(mode)
    local displayID = getMainDisplayID()
    if not displayID then
        hs.alert.show("No display found", alertStyle, nil, 2)
        return
    end

    local label = mode == "4k" and "4K" or "1080p"
    local args
    if mode == "4k" then
        args = " res:3840x2160 hz:30 color_depth:8"
    else
        args = " res:1920x1080 hz:30 color_depth:8 scaling:on"
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
hs.hotkey.bind({"ctrl", "alt", "cmd"}, "1", function() switchResolution("1080p") end)
