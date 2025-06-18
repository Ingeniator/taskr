#!/usr/bin/env python3
import sys
import os
import platform
import fcntl
import signal
import threading
from pynput import keyboard

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMessageBox, QMenu
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtCore import QMetaObject, Qt

from ui.launcher import CtrlLord

import subprocess
from ApplicationServices import AXIsProcessTrustedWithOptions

def show_permission_dialog():
    app = QApplication.instance() or QApplication(sys.argv)

    QMessageBox.critical(
        None,
        "Accessibility Required",
        "This app needs Accessibility permissions to function properly.\n\n"
        "Please open System Settings → Privacy & Security → Accessibility and allow access.",
        QMessageBox.Ok
    )

def is_process_trusted(prompt=False):
    options = { "AXTrustedCheckOptionPrompt": prompt }
    return AXIsProcessTrustedWithOptions(options)

def open_accessibility_settings():
    if platform.system() == "Darwin":
        try:
            subprocess.run([
                "open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
            ])
        except Exception as e:
            print("⚠️ Could not open Accessibility settings:", e)

def already_running():
    lockfile = '/tmp/ctrllord.lock'
    try:
        global lock_fp
        lock_fp = open(lockfile, 'w')
        fcntl.flock(lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return False
    except IOError:
        return True

def main():
    if already_running():
        print("Another instance is already running.")
        sys.exit(0)

    if not is_process_trusted():
        print("🔒 Accessibility permissions not granted.")
        show_permission_dialog()
        open_accessibility_settings()
        sys.exit(1)
    else:
        print("✅ Accessibility permission granted.")

    signal.signal(signal.SIGTSTP, signal.SIG_IGN)

    # macOS activation
    if platform.system() == "Darwin":
        from AppKit import NSApplication
        NSApplication.sharedApplication().setActivationPolicy_(0)
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("resources/icon.png"))
    QGuiApplication.setQuitOnLastWindowClosed(False)
    launcher = CtrlLord()

    def trigger_launcher():
        # Run GUI method from non-GUI thread safely
        QMetaObject.invokeMethod(launcher, "show_launcher", Qt.QueuedConnection)

    # Start hotkey listener in thread
    def listener():
        with keyboard.GlobalHotKeys({
            '<cmd>+l': trigger_launcher
        }) as h:
            h.join()

    threading.Thread(target=listener, daemon=True).start()

    print("✅ Hotkey is ready: Cmd + L")
    sys.exit(app.exec())

sys.stderr = open("/tmp/ctrllord.err", "w")
sys.stdout = open("/tmp/ctrllord.out", "w")

if __name__ == "__main__":
    main()