-- Focused-window border.
--
-- Draws a thin frame just inside the edges of whichever window has focus, so it is obvious at a
-- glance where keystrokes will go. Started from init.lua.
--
-- The frame is four hs.canvas strips, one per edge, rather than one canvas the size of the
-- window: a canvas costs memory for its whole area, and the strips cover almost none. They float
-- above ordinary windows and ignore the mouse, so clicks pass straight through to the window.
--
-- It is drawn INSIDE the window's frame, over the outermost couple of points of the window, not
-- around the outside. That way it needs no gaps between tiled windows and is never clipped at a
-- screen edge. The corners are square; macOS gives no public way to read a window's corner
-- radius, and a square frame is at least the same on every app.
--
-- Everything is event-driven. An application watcher follows which app is frontmost; a watcher on
-- that app follows which of its windows has focus; a watcher on that window follows it as it
-- moves and resizes. Only one app and one window are ever being watched.

local M = {}

-- Thickness of the frame, in points.
local WIDTH = 2
-- Tokyo Night Storm blue, hard-coded from the terminal palette (see the iTerm2 README in the
-- chezmoi source); update it by hand if the palette moves.
local COLOR = { hex = "#7aa2f7", alpha = 1.0 }
-- A window with less than this fraction of its area on screen gets no frame. AeroSpace hides the
-- windows of other workspaces by parking them almost entirely off the corner of the screen, and a
-- parked window can still be the focused one (after switching to an empty workspace); without
-- this the frame would follow it and light up the sliver that remains visible.
local MIN_VISIBLE_FRACTION = 0.5

local strips        -- the four canvases, created on first use
local appWatcher    -- hs.application.watcher: which app is frontmost
local appElementWatcher     -- hs.uielement watcher on the frontmost app: its focused window
local windowWatcher         -- hs.uielement watcher on the focused window: moves and resizes
local watchedWindowId       -- id of the window windowWatcher is on

local events = hs.uielement.watcher

-- The four strips for a window frame, as rects: top, bottom, left, right. The left and right
-- strips stop short of the top and bottom ones so the corners are not drawn twice.
function M.stripRects(frame, width)
    local sideHeight = math.max(frame.h - 2 * width, 0)
    return {
        { x = frame.x, y = frame.y, w = frame.w, h = width },
        { x = frame.x, y = frame.y + frame.h - width, w = frame.w, h = width },
        { x = frame.x, y = frame.y + width, w = width, h = sideHeight },
        { x = frame.x + frame.w - width, y = frame.y + width, w = width, h = sideHeight },
    }
end

-- Fraction of a window frame's area that lies on any screen.
local function visibleFraction(frame)
    local area = frame.w * frame.h
    if area <= 0 then return 0 end
    local visible = 0
    for _, screen in ipairs(hs.screen.allScreens()) do
        local overlap = frame:intersect(screen:fullFrame())
        visible = visible + overlap.w * overlap.h
    end
    return visible / area
end

local function hide()
    if not strips then return end
    for _, strip in ipairs(strips) do strip:hide() end
end

local function draw(frame)
    if not strips then
        strips = {}
        for i = 1, 4 do
            strips[i] = hs.canvas.new({ x = 0, y = 0, w = 1, h = 1 })
                :level(hs.canvas.windowLevels.floating)
                :behavior({ "canJoinAllSpaces", "stationary" })
                :appendElements({ type = "rectangle", action = "fill", fillColor = COLOR })
        end
    end
    for i, rect in ipairs(M.stripRects(frame, WIDTH)) do
        strips[i]:frame(rect):show()
    end
end

-- Whether a focused "window" should get a frame. Finder's desktop reports itself as the focused
-- window when Finder is frontmost with nothing open, and a window in a native full-screen space
-- has no neighbours to be told apart from.
local function wantsBorder(window)
    return window:role() == "AXWindow"
        and not window:isFullScreen()
        and visibleFraction(window:frame()) >= MIN_VISIBLE_FRACTION
end

local function stopWatcher(watcher)
    if watcher then watcher:stop() end
    return nil
end

-- Redraw for the current focused window, and follow that window from here on. This is also the
-- callback for every watcher, so it runs repeatedly while a window is dragged; the window watcher
-- is only replaced when focus has actually moved to a different window.
local function refresh()
    local window = hs.window.focusedWindow()
    if not window then
        windowWatcher = stopWatcher(windowWatcher)
        watchedWindowId = nil
        hide()
        return
    end

    if window:id() ~= watchedWindowId then
        stopWatcher(windowWatcher)
        windowWatcher = window:newWatcher(refresh)
        windowWatcher:start({
            events.windowMoved,
            events.windowResized,
            events.windowMinimized,
            events.elementDestroyed,
        })
        watchedWindowId = window:id()
    end

    if wantsBorder(window) then draw(window:frame()) else hide() end
end

-- Follow the focused window of `app`, the frontmost application.
local function watchApp(app)
    appElementWatcher = stopWatcher(appElementWatcher)
    if app then
        appElementWatcher = app:newWatcher(refresh)
        appElementWatcher:start({ events.focusedWindowChanged, events.mainWindowChanged })
    end
    refresh()
end

function M.start()
    appWatcher = hs.application.watcher.new(function(_, event, app)
        if event == hs.application.watcher.activated then
            watchApp(app)
        elseif event == hs.application.watcher.terminated then
            refresh()
        end
    end)
    appWatcher:start()
    watchApp(hs.application.frontmostApplication())
end

function M.stop()
    appWatcher = stopWatcher(appWatcher)
    appElementWatcher = stopWatcher(appElementWatcher)
    windowWatcher = stopWatcher(windowWatcher)
    watchedWindowId = nil
    if strips then
        for _, strip in ipairs(strips) do strip:delete() end
        strips = nil
    end
end

return M
