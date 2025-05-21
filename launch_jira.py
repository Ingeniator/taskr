#!/usr/bin/env python3
import sys
import os
import platform
import fcntl
import signal
import threading
from pynput import keyboard

from PyQt5.QtWidgets import QApplication, QSystemTrayIcon
from PyQt5.QtGui import QGuiApplication, QIcon
from PyQt5.QtCore import QMetaObject, Qt

from ui.launcher import JiraQuickTask

def already_running():
    lockfile = '/tmp/jira_quick_task.lock'
    try:
        global lock_fp
        lock_fp = open(lockfile, 'w')
        fcntl.flock(lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return False
    except IOError:
        return True

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def create_tray(app, launcher):
    QGuiApplication.setQuitOnLastWindowClosed(False)

    # Load tray icon (fallback icon)
    tray_icon_path = resource_path("resources/icon.png")
    icon = QIcon(tray_icon_path)
    tray = QSystemTrayIcon()
    tray.setIcon(icon)
    tray.setToolTip("Jira Quick Task")
    tray.activated.connect(lambda r: launcher.show_launcher() if r == QSystemTrayIcon.Trigger else None)
    tray.setVisible(True)
    return tray

def main():
    if already_running():
        print("Another instance is already running.")
        sys.exit(0)

    signal.signal(signal.SIGTSTP, signal.SIG_IGN)

    # macOS activation
    if platform.system() == "Darwin":
        from AppKit import NSApplication
        NSApplication.sharedApplication().setActivationPolicy_(0)
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("resources/icon.png"))
    launcher = JiraQuickTask()
    tray = create_tray(app, launcher)

    def trigger_launcher():
        # Run GUI method from non-GUI thread safely
        QMetaObject.invokeMethod(launcher, "show_launcher", Qt.QueuedConnection)

    # Start hotkey listener in thread
    def listener():
        with keyboard.GlobalHotKeys({
            '<cmd>+<shift>+/': trigger_launcher
        }) as h:
            h.join()

    threading.Thread(target=listener, daemon=True).start()

    print("✅ Hotkey is ready: Cmd + Shift + /")
    sys.exit(app.exec_())

sys.stderr = open("/tmp/jiraquicktask.err", "w")
sys.stdout = open("/tmp/jiraquicktask.out", "w")

if __name__ == "__main__":
    main()