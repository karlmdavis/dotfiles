"""AeroSpace workspace helpers shared by the SwiftBar plugin and the workspace-switch HUD.

Both consumers read the same ~/.config/aerospace/workspaces.yaml (a map of single-char workspace
ids to optional {icon, name, hint} records) and present it: the SwiftBar plugin as a menu-bar
indicator (`swiftbar.main`), the HUD as a transient on-switch alert (`hud.main`). The shared
loading/labeling/sanitizing logic lives in `workspaces`.
"""
