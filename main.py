import sys
import threading
import random
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLineEdit, QVBoxLayout, QLabel, QGraphicsDropShadowEffect, QDesktopWidget
)
from PyQt5.QtCore import Qt, QTimer, QPoint, QMetaObject, Q_ARG, QPropertyAnimation
from PyQt5.QtGui import QFont, QColor, QCursor
from pynput import keyboard
from PyQt5.QtCore import pyqtSlot

class ToastMessage(QWidget):
    def __init__(self, message: str):
        super().__init__(None)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 14px;
                border: 1px solid #ccc;
            }
            QLabel {
                color: #111;
                padding: 12px 24px;
                font-size: 16px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(5)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        label = QLabel()
        label.setTextFormat(Qt.RichText)
        label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        label.setOpenExternalLinks(True)
        label.setAlignment(Qt.AlignCenter)
        label.setText(message)
        layout.addWidget(label)
        layout.setContentsMargins(0, 0, 0, 0)

        self.adjustSize()

    def show_at(self, x, y, timeout_ms=3000):
        self.move(x, y)
        self.show()
        QTimer.singleShot(timeout_ms, self.close)


class JiraQuickTask(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(600, 100)
        self.init_ui()

    def eventFilter(self, obj, event):
        if obj == self.input and event.type() == event.KeyPress:
            if event.key() == Qt.Key_Escape:
                self.input.clear()
                self.hide()
                return True
        return super().eventFilter(obj, event)

    def init_ui(self):
        self.input = QLineEdit()
        self.input.installEventFilter(self)
        self.input.setPlaceholderText("Create a JIRA task...")
        self.input.setFont(QFont("San Francisco", 22, QFont.Medium))
        self.input.setStyleSheet("""
            QLineEdit {
                padding: 14px 24px;
                border-radius: 14px;
                background-color: white;
                border: 1px solid #ccc;
                color: black;
            }
        """)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.input.setGraphicsEffect(shadow)

        layout = QVBoxLayout()
        layout.addWidget(self.input)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)

        self.input.returnPressed.connect(self.create_task)

    def create_task(self):
        summary = self.input.text().strip()
        if summary:
            task_id = f"MOCK-{random.randint(100, 999)}"
            jira_url = f"https://jira.yourcompany.com/browse/{task_id}"
            message = f'✅ Task <a href="{jira_url}">{task_id}</a> created (copied)'
            self.input.clear()
            self.hide()

            # 📋 Copy to clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(task_id)

            self.show_toast(message)
        else:
            self.show_toast("Please enter a task summary")

    def show_toast(self, message: str):

        toast = ToastMessage(message)
        x = self.x() + (self.width() - toast.width()) // 2
        y = self.y() + self.height() + 10

        print("Showing toast at", x, y)
        toast.show_at(x, y)

        self.toast = toast  # Keep reference alive!


    @pyqtSlot()
    def show_launcher(self):
        screen = QDesktopWidget().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = int(screen.height() * 0.2)  # top 20% of screen
        self.move(x, y)
        self.show()
        self.activateWindow()
        self.raise_()
        self.input.setFocus()


def main():
    app = QApplication(sys.argv)
    launcher = JiraQuickTask()

    def trigger_launcher():
        # Run GUI method from non-GUI thread safely
        QMetaObject.invokeMethod(launcher, "show_launcher", Qt.QueuedConnection)

    # Start hotkey listener in thread
    def listener():
        with keyboard.GlobalHotKeys({
            '<cmd>+<shift>+j': trigger_launcher
        }) as h:
            h.join()

    threading.Thread(target=listener, daemon=True).start()

    print("✅ Hotkey is ready: Cmd + Shift + J")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
