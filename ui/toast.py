from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer

class ToastMessage(QWidget):
    def __init__(self, message: str):
        super().__init__(None)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setStyleSheet("""
            QLabel {
                padding: 12px 24px;
                font-size: 16px;
            }
        """)

        layout = QVBoxLayout(self)
        label = QLabel(message)
        label.setTextFormat(Qt.RichText)
        label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        label.setOpenExternalLinks(True)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        layout.setContentsMargins(0, 0, 0, 0)

        self.adjustSize()

    def show_at(self, x, y, timeout_ms=3000):
        self.move(x, y)
        self.show()
        QTimer.singleShot(timeout_ms, self.close)