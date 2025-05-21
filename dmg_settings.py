# dmg_settings.py
import os

application = "JiraQuickTask"

# Files to include
files = [
    "dist/JiraQuickTask.app",
]

# Create a symbolic link to /Applications
symlinks = {
    "Applications": "/Applications"
}

# Icon locations in the DMG window
icon_locations = {
    "JiraQuickTask.app": (140, 120),
    "Applications": (380, 120)
}

# Window size and positioning
window_rect = ((200, 100), (520, 280))  # (origin), (size)
icon_size = 100

# Optional background image
# Must be PNG and exactly match window size
background = "assets/dmg_background.png"

# Volume format (you can skip this unless you need HFS+ specifically)
format = "UDZO"

# Volume name shown in Finder
volume_name = f"{application} Installer"

# Hide hidden/system files
show_status_bar = False
show_tab_view = False
show_toolbar = False
show_pathbar = False

# If true, app opens in Finder in the target window layout
use_hdiutil = True
