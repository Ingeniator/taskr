#!/usr/bin/env python3
import sys
import os
import platform
import fcntl
import atexit
import signal
import logging
import threading
from pynput import keyboard

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMessageBox, QMenu
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtCore import QMetaObject, Qt

from services.config import setup_logging, load_config, get_resource_path
from ui.launcher import CtrlLord

import subprocess
from ApplicationServices import AXIsProcessTrustedWithOptions

logger = logging.getLogger(__name__)

LOCK_FILE = '/tmp/ctrllord.lock'
lock_fp = None


def show_permission_dialog():
    app = QApplication.instance() or QApplication(sys.argv)

    QMessageBox.critical(
        None,
        "Accessibility Required",
        "This app needs Accessibility permissions to function properly.\n\n"
        "Please open System Settings > Privacy & Security > Accessibility and allow access.",
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
            logger.warning("Could not open Accessibility settings: %s", e)


def acquire_lock():
    """Acquire process lock file. Returns True if lock acquired, False if another instance running."""
    global lock_fp
    try:
        lock_fp = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        atexit.register(release_lock)
        return True
    except IOError:
        return False


def release_lock():
    """Release and remove lock file on exit."""
    global lock_fp
    if lock_fp:
        try:
            fcntl.flock(lock_fp, fcntl.LOCK_UN)
            lock_fp.close()
        except Exception:
            pass
    try:
        os.remove(LOCK_FILE)
    except OSError:
        pass


def main():
    setup_logging()

    if not acquire_lock():
        logger.info("Another instance is already running.")
        sys.exit(0)

    if not is_process_trusted():
        logger.warning("Accessibility permissions not granted.")
        show_permission_dialog()
        open_accessibility_settings()
        sys.exit(1)
    else:
        logger.info("Accessibility permission granted.")

    signal.signal(signal.SIGTSTP, signal.SIG_IGN)

    # Read hotkey from config (default: <cmd>+l)
    try:
        config = load_config()
        hotkey = config.get("ui", {}).get("hotkey", "<cmd>+l")
    except Exception as e:
        logger.warning("Failed to load config for hotkey, using default: %s", e)
        hotkey = "<cmd>+l"

    # macOS activation
    if platform.system() == "Darwin":
        from AppKit import NSApplication
        NSApplication.sharedApplication().setActivationPolicy_(0)
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(get_resource_path("resources/icon.png")))
    QGuiApplication.setQuitOnLastWindowClosed(False)
    launcher = CtrlLord()

    def trigger_launcher():
        # Run GUI method from non-GUI thread safely
        QMetaObject.invokeMethod(launcher, "show_launcher", Qt.QueuedConnection)

    # Start hotkey listener in thread
    def listener():
        with keyboard.GlobalHotKeys({
            hotkey: trigger_launcher
        }) as h:
            h.join()

    threading.Thread(target=listener, daemon=True).start()

    logger.info("Hotkey is ready: %s", hotkey)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
