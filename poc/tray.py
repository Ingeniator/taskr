import sys
import platform
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QGuiApplication, QCursor, QAction
from PyQt6.QtCore import Qt, QPoint

# macOS activation
if platform.system() == "Darwin":
    from AppKit import NSApplication
    NSApplication.sharedApplication().setActivationPolicy_(0)
    NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

app = QApplication(sys.argv)
QGuiApplication.setQuitOnLastWindowClosed(False)

icon = QIcon("icon.png")
if icon.isNull():
    print("❌ Icon not loaded")
else:
    print("✅ Icon loaded")

tray = QSystemTrayIcon()
tray.setIcon(icon)
tray.setToolTip("Jira Quick Task")

menu = QMenu()
menu.addAction(QAction("Quit", triggered=app.quit))
tray.setContextMenu(menu)

def on_tray_activated(reason):
    if reason == QSystemTrayIcon.ActivationReason.Trigger:  # Left click
        print("👈 Tray left-clicked")

tray.activated.connect(on_tray_activated)
tray.setVisible(True)

if not tray.isVisible():
    print("❌ Tray not visible")
else:
    print("✅ Tray is visible")

sys.exit(app.exec())
