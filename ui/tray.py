from PyQt5.QtWidgets import QSystemTrayIcon
from PyQt5.QtGui import QIcon, QGuiApplication

def create_tray(icon_path, launcher):
    QGuiApplication.setQuitOnLastWindowClosed(False)
    tray = QSystemTrayIcon(QIcon(icon_path))
    tray.setToolTip("Jira Quick Task")
    tray.activated.connect(lambda r: launcher.show_launcher() if r == QSystemTrayIcon.Trigger else None)
    tray.setVisible(True)
    return tray
