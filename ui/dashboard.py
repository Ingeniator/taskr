from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QListWidget, QTextEdit, QStackedWidget,
    QGraphicsDropShadowEffect, QApplication,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QCursor


class TaskDashboard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(750, 500)

        self._tasks = []
        self._init_ui()

    def _init_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, 100))

        container = QWidget()
        container.setObjectName("DashboardContainer")
        container.setStyleSheet("""
            #DashboardContainer {
                background-color: palette(base);
                border-radius: 14px;
                border: 1px solid #ccc;
            }
        """)
        container.setGraphicsEffect(shadow)

        main_layout = QHBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Left panel ---
        left = QWidget()
        left.setFixedWidth(250)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(16, 16, 0, 16)
        left_layout.setSpacing(4)

        header = QLabel("Today's Tasks")
        header.setFont(QFont("Helvetica Neue", 16, QFont.Bold))
        left_layout.addWidget(header)

        from datetime import datetime, timezone
        self._date_label = QLabel(datetime.now(timezone.utc).strftime("%A, %B %d"))
        self._date_label.setStyleSheet("color: #888; font-size: 12px;")
        left_layout.addWidget(self._date_label)
        left_layout.addSpacing(8)

        self._list = QListWidget()
        self._list.setStyleSheet("""
            QListWidget {
                border: none;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 6px 4px;
            }
            QListWidget::item:selected {
                background-color: palette(highlight);
                color: palette(highlighted-text);
                border-radius: 6px;
            }
        """)
        left_layout.addWidget(self._list)
        main_layout.addWidget(left)

        # --- Right panel (stacked: content vs empty) ---
        self._stack = QStackedWidget()

        # Empty state
        empty = QLabel("No tasks created today")
        empty.setAlignment(Qt.AlignCenter)
        empty.setStyleSheet("color: #888; font-size: 14px;")
        self._stack.addWidget(empty)  # index 0

        # Content view
        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(16, 16, 16, 16)
        detail_layout.setSpacing(8)

        self._title_label = QLabel()
        self._title_label.setFont(QFont("Helvetica Neue", 18, QFont.Bold))
        self._title_label.setWordWrap(True)
        detail_layout.addWidget(self._title_label)

        meta_line = QHBoxLayout()
        meta_line.setContentsMargins(0, 0, 0, 0)
        meta_line.setSpacing(0)

        self._key_label = QLabel()
        self._key_label.setStyleSheet(
            "color: #555; font-size: 12px; text-decoration: underline;"
        )
        self._key_label.setCursor(QCursor(Qt.PointingHandCursor))
        self._key_label.mousePressEvent = self._copy_key
        meta_line.addWidget(self._key_label)

        self._meta_label = QLabel()
        self._meta_label.setStyleSheet("color: #888; font-size: 12px;")
        meta_line.addWidget(self._meta_label)
        meta_line.addStretch()

        detail_layout.addLayout(meta_line)

        self._description = QTextEdit()
        self._description.setReadOnly(True)
        self._description.setFont(QFont("Helvetica Neue", 14))
        self._description.setStyleSheet("""
            QTextEdit {
                border: none;
                padding: 4px 0;
            }
        """)
        detail_layout.addWidget(self._description)
        self._stack.addWidget(detail)  # index 1

        main_layout.addWidget(self._stack, 1)

        outer.addWidget(container)

        self._list.currentRowChanged.connect(self._on_row_changed)

    def load_tasks(self, tasks: list[dict]):
        self._tasks = tasks
        self._list.clear()
        self._description.clear()
        self._title_label.clear()
        self._key_label.clear()
        self._meta_label.clear()

        if not tasks:
            self._stack.setCurrentIndex(0)
            return

        self._stack.setCurrentIndex(1)
        for task in tasks:
            key = task.get("key", "")
            summary = task.get("summary", "")
            self._list.addItem(f"{key}: {summary}")

        self._list.setCurrentRow(0)

    def _on_row_changed(self, row):
        if row < 0 or row >= len(self._tasks):
            return
        task = self._tasks[row]
        self._title_label.setText(task.get("summary", ""))
        key = task.get("key", "")
        self._key_label.setText(key)
        parts = filter(None, [
            task.get("type"),
            task.get("component"),
        ])
        suffix = " | ".join(parts)
        self._meta_label.setText(f"  |  {suffix}" if suffix else "")
        self._description.setPlainText(task.get("description", ""))

    def _copy_key(self, _event=None):
        key = self._key_label.text()
        if key:
            QApplication.clipboard().setText(key)

    def show_at(self, x, y):
        self.move(x, y)
        self.show()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)
