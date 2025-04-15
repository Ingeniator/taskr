import sys
import os
import socket

import threading
import random
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLineEdit, QComboBox, QTextEdit, 
    QStyledItemDelegate, QStyleOptionViewItem, QStyle,
    QVBoxLayout, QHBoxLayout, QLabel, QGraphicsDropShadowEffect, QDesktopWidget
)
from PyQt5.QtCore import Qt, QTimer, QPoint, QMetaObject, Q_ARG, QPropertyAnimation
from PyQt5.QtGui import QFont, QColor, QCursor, QTextCharFormat, QTextCursor
from pynput import keyboard
from PyQt5.QtCore import pyqtSlot

class NoCheckmarkBoldSelectedDelegate(QStyledItemDelegate):
    def initStyleOption(self, option: QStyleOptionViewItem, index):
        super().initStyleOption(option, index)
        option.features &= ~QStyleOptionViewItem.HasCheckIndicator
        if option.state & QStyle.State_Selected:
            option.palette.setColor(option.palette.Text, QColor("#222"))
            option.palette.setColor(option.palette.HighlightedText, QColor("#222"))  # selected+hover
            option.font.setBold(True)

class ToastMessage(QWidget):
    def __init__(self, message: str):
        super().__init__(None)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setStyleSheet("""
            QLabel {
                color: #111;
                padding: 12px 24px;
                font-size: 16px;
                background-color: white;
            
            }
        """)

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
        self.setFixedSize(600, 180)

        self.step = 0
        self.toast = None

        self.init_ui()

    def eventFilter(self, obj, event):
        if event.type() == event.KeyPress:
            if event.key() == Qt.Key_Escape:
                self.input.clear()
                self.textarea.clear()
                self.details_section.hide()
                self.input.show()
                self.setFixedHeight(180)
                self.input.setFocus()
                self.step = 0
                self.hide()
                return True
            elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if obj == self.input:
                    self.handle_enter()
                    return True
                elif obj == self.textarea and event.modifiers() & Qt.ShiftModifier:
                    self.handle_enter()
                    return True
                # Otherwise: allow Enter to insert newline in textarea
        return super().eventFilter(obj, event)

    def init_ui(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(0)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.setLayout(self.layout)

        # STEP 1: Input field for task summary
        self.input = QLineEdit()
        self.input.setGraphicsEffect(shadow)
        self.input.setPlaceholderText("Create a JIRA task...")
        self.input.setFont(QFont("Helvetica Neue", 22, QFont.Medium))
        self.input.setStyleSheet("""
            QLineEdit {
                padding: 14px 24px;
                border-radius: 14px;
                background-color: white;
                border: 1px solid #ccc;
                color: black;
            }
        """)
        self.input.returnPressed.connect(self.handle_enter)
        self.input.installEventFilter(self)

        # STEP 2: Details section
        self.details_section = QWidget()
        self.details_layout = QVBoxLayout(self.details_section)
        self.details_layout.setContentsMargins(0, 0, 0, 0)
        self.details_layout.setSpacing(8)

        self.details_section.setStyleSheet("""
            #DetailsSection {
                background-color: white;
                border-radius: 14px;
                border: 1px solid #ccc;
            }
        """)
        self.details_section.setObjectName("DetailsSection")

        # hint
        hint = QLabel("Press Ctrl+Enter to submit")
        hint.setStyleSheet("color: #888; font-size: 11px; padding-top: 10px; padding-left: 20px;")
        self.details_layout.addWidget(hint)

        # Description
        self.textarea = QTextEdit()
        self.textarea.setFont(QFont("Helvetica Neue", 14))
        self.textarea.setPlaceholderText("# Summary\n\nDescription here...")
        self.textarea.setStyleSheet("""
            QTextEdit {
                padding: 14px 24px;
                color: black;
                border: none;
            }
        """)
        self.textarea.installEventFilter(self)
        self.details_layout.addWidget(self.textarea)

        # Component line
        self.component_line = QWidget()
        self.component_line.setFixedHeight(32)
        self.component_layout = QHBoxLayout(self.component_line)
        self.component_layout.setContentsMargins(20, 0, 20, 0)
        self.component_layout.setSpacing(6)

        # Issue Type line
        type_label = QLabel("Type:")
        type_label.setFont(QFont("Helvetica Neue", 13))
        self.type_dropdown = QComboBox()
        self.type_dropdown.addItems(["Task", "Bug", "Story", "Spike"])
        self.type_dropdown.setItemDelegate(NoCheckmarkBoldSelectedDelegate(self.type_dropdown))
        self.type_dropdown.setStyleSheet("""
            QComboBox {
                border: none;
                border-radius: 0px;
                background: transparent;
                font-size: 13px;
                padding: 0px;
                padding: 2px 16px 2px 6px;
                color: #444;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                outline: none;
                selection-background-color: transparent;
                font-weight: normal;
            }
        """)
        self.component_layout.addWidget(type_label)
        self.component_layout.addWidget(self.type_dropdown)


        label = QLabel("Component:")
        label.setFont(QFont("Helvetica Neue", 13))

        # Component dropdown
        self.component_dropdown = QComboBox()
        self.component_dropdown.addItems(["Core", "UI", "API Integration Layer", "Machine Learning Pipeline"])
        self.component_dropdown.setItemDelegate(NoCheckmarkBoldSelectedDelegate(self.component_dropdown))
        self.component_dropdown.setStyleSheet(self.type_dropdown.styleSheet())
        
        self.component_layout.addWidget(label)
        self.component_layout.addWidget(self.component_dropdown)
        self.component_layout.addStretch()

        self.details_layout.addWidget(self.component_line)

        self.details_section.hide()

        # Add widgets to main layout
        self.layout.addWidget(self.input)
        self.layout.addWidget(self.details_section)
        self.details_section.setLayout(self.details_layout)

    def handle_enter(self):
        if self.step == 0:
            self.prepare_task_preview()
        elif self.step == 1:
            self.submit_task()

    def prepare_task_preview(self):
        text = self.input.text().strip()
        if not text:
            self.show_toast("Please enter a task summary")
            return

        # Mocked task data
        self.task_data = {
            "type": "Task",
            "key": f"MOCK-{random.randint(100, 999)}",
            "summary": text,
            "description": "Describe this task...",
            "component": "Core"
        }

        self.input.hide()

        # Show step 2 fields
        self.details_section.show()

        cursor = self.textarea.textCursor()

        summary_text = self.task_data["summary"] or ""
        summary_format = QTextCharFormat()
        summary_format.setFont(QFont("Helvetica Neue", 22, QFont.Bold))
        cursor.insertText(summary_text + "\n\n", summary_format)

        description_text = self.task_data["description"] or ""
        default_format = QTextCharFormat()
        default_format.setFont(QFont("Helvetica Neue", 16))
        cursor.insertText(description_text, default_format)

        self.textarea.setTextCursor(cursor)
        self.textarea.setFocus()
        self.setFixedHeight(260)

        type_index = self.type_dropdown.findText(self.task_data["type"])
        if type_index >= 0:
            self.type_dropdown.setCurrentIndex(type_index)

        index = self.component_dropdown.findText(self.task_data["component"])
        if index >= 0:
            self.component_dropdown.setCurrentIndex(index)
        
        self.step = 1

    def submit_task(self):
        full_text = self.textarea.toPlainText()
        lines = full_text.strip().split("\n")
        summary = lines[0].lstrip("# ").strip() if lines else ""
        description = "\n".join(lines[2:]) if len(lines) > 2 else ""
        issue_type = self.type_dropdown.currentText()
        component = self.component_dropdown.currentText()
        task_key = self.task_data["key"]

        # Simulate task creation
        # (Replace with real API later)

        # 📋 Copy key to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(task_key)

        jira_url = f"https://jira.yourcompany.com/browse/{task_key}"
        self.show_toast(f'✅ Task <a href="{jira_url}">{task_key}</a> created (copied)')

        self.textarea.clear()
        self.input.clear()
        self.details_section.hide()
        self.input.show()
        self.setFixedHeight(180)
        self.input.setFocus()
        self.step = 0
        self.hide()

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

def already_running():
    s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        s.bind('\0jira_quick_task_pyqt_singleton_launcher')
        return False
    except socket.error:
        return False

def main():
    if already_running():
        print("Another instance is already running.")
        sys.exit(0)

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
