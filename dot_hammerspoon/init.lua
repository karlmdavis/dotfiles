require("hs.ipc")

hs.urlevent.bind("workspace", function(_, params)
    hs.alert.show(params.name, { textSize = 36, strokeWidth = 0 }, nil, 0.8)
end)
