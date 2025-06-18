# ui/launcher.py

from PySide6.QtWidgets import (
    QApplication,
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox, QToolButton,
    QStyle, QStyledItemDelegate, QStyleOptionViewItem, 
    QGraphicsDropShadowEffect, QSystemTrayIcon, QMenu
)
from PySide6.QtCore import Qt, QTimer, Slot, QEvent
from PySide6.QtGui import (
    QFont, QClipboard, QColor, QIcon, QAction, QCursor,
    QTextCharFormat, QTextCursor, QGuiApplication   
)

from services.parser import parse_task_text
from services.jira_service import JiraService
from services.task_generator_service import TaskGeneratorService
from services.config import load_config

from ui.toast import ToastMessage
from ui.styles import NoCheckmarkBoldSelectedDelegate
from ui.config import ConfigEditorDialog

import os
import sys

def resource_path(rel_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, rel_path)
    return os.path.join(os.path.abspath("."), rel_path)

class CtrlLord(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(700, 180)

        self.step = 0
        self.toast = None

        self.generator = TaskGeneratorService()
        self.jira = JiraService()
        self.init_ui()
        self.create_tray()
    
    def create_tray(self):
        # Load tray icon
        tray_icon_path = resource_path("resources/icon.png")
        icon = QIcon(tray_icon_path)
        if icon.isNull():
            print("❌ Failed to load tray icon!")
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(icon)
        self.tray.setToolTip("CtrlLord")

        menu = QMenu(self)
        open_action = QAction("📝 Create Task", self)
        open_action.triggered.connect(self.show_launcher)
        menu.addAction(open_action)
        menu.addSeparator()
        settings_action = QAction("⚙️ Settings", self)
        settings_action.triggered.connect(self.show_config)
        menu.addAction(settings_action)
        menu.addSeparator()
        quit_action = QAction("❌ Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.setVisible(True)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key_Escape:
                self.reset_ui()
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

    def adjust_height_to_content(self):
        doc = self.textarea.document()
        margins = self.layout.contentsMargins()
        spacing = self.layout.spacing()

        content_height = int(doc.size().height()) + 100  # Padding for cursor, scrollbar, etc.
        component_height = self.component_line.sizeHint().height()
        base_height = self.input.height() if self.step == 0 else 0

        full_height = base_height + content_height + component_height + margins.top() + margins.bottom() + spacing * 2
        full_height = max(180, min(600, full_height))  # Clamp size if needed

        self.setFixedHeight(full_height)

    def reset_ui(self):
        self.textarea.clear()
        self.input.clear()
        self.details_section.hide()
        self.input.show()
        self.setFixedHeight(180)
        self.input.setFocus()
        self.step = 0
        self.hide()

    def refresh_from_config(self):
        config = load_config()
        self.jira.reload_config()
        issue_types = config["ui"]["issue_types"]
        components = config["ui"]["components"]
        print("🔄 UI reloading categories…")
        self.type_dropdown.clear()
        self.type_dropdown.addItems(config["ui"]["issue_types"])
        self.component_dropdown.clear()
        self.component_dropdown.addItems(config["ui"]["components"])

    def init_ui(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(0)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, 100))
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
                border: 1px solid #ccc;
            }
        """)
        self.input.returnPressed.connect(self.handle_enter)
        self.input.installEventFilter(self)

        # STEP 2: Details section
        self.details_section = QWidget()
        self.details_section.setObjectName("DetailsSection")
        self.details_layout = QVBoxLayout(self.details_section)
        self.details_layout.setContentsMargins(0, 0, 0, 0)
        self.details_layout.setSpacing(8)

        self.details_section.setStyleSheet("""
            #DetailsSection {
                background-color: palette(base);
                border-radius: 14px;
                border: 1px solid #ccc;
            }
            QLabel {
                color: #888;
            }
        """)
        self.details_section.setGraphicsEffect(shadow)

        # hint
        hint = QLabel("Press Shift+Enter to submit")
        hint.setStyleSheet("color: #888; font-size: 11px; padding-top: 10px; padding-left: 20px;")
        self.details_layout.addWidget(hint)

        # Description
        self.textarea = QTextEdit()
        self.textarea.setFont(QFont("Helvetica Neue", 14))
        self.textarea.setPlaceholderText("# Summary\n\nDescription here...")
        self.textarea.setStyleSheet("""
            QTextEdit {
                padding: 14px 24px;
                border: none;
            }
        """)
        self.textarea.installEventFilter(self)
        self.details_layout.addWidget(self.textarea)
        self.textarea.textChanged.connect(self.adjust_height_to_content)

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
        self.type_dropdown.setItemDelegate(NoCheckmarkBoldSelectedDelegate(self.type_dropdown))
        self.type_dropdown.setStyleSheet("""
            QComboBox {
                border: none;
                border-radius: 0px;
                background: transparent;
                font-size: 13px;
                padding: 0px;
                padding: 2px 16px 2px 6px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
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
        self.component_dropdown.setItemDelegate(NoCheckmarkBoldSelectedDelegate(self.component_dropdown))
        self.component_dropdown.setStyleSheet(self.type_dropdown.styleSheet())
        
        self.component_layout.addWidget(label)
        self.component_layout.addWidget(self.component_dropdown)
        self.component_layout.addStretch()
        # # ➕ Add config button (bottom-right)
        # self.config_button = QToolButton()
        # self.config_button.setText("⚙️")
        # self.config_button.setToolTip("Edit Configuration")
        # self.config_button.setCursor(Qt.PointingHandCursor)
        # self.config_button.setStyleSheet("""
        #     QToolButton {
        #         background: transparent;
        #         border: none;
        #         padding: 0px;
        #         font-size: 14px;
        #     }
        #     QToolButton:hover {
        #         color: #555;
        #     }
        # """)
        # self.config_button.clicked.connect(self.show_config)
        # self.component_layout.addWidget(self.config_button)

        self.details_layout.addWidget(self.component_line)
        self.details_section.setLayout(self.details_layout)
        self.details_section.hide()

        # Add widgets to main layout
        self.layout.addWidget(self.input)
        self.layout.addWidget(self.details_section)

        self.refresh_from_config()

    def handle_enter(self):
        if self.step == 0:
            self.prepare_task_preview()
        elif self.step == 1:
            self.submit_task()

    def prepare_task_preview(self):
        summary = self.input.text().strip()
        if not summary:
            self.show_toast("Please enter a task summary")
            return

        task_generated_data = self.generator.build_task_payload(summary)

        self.task_data = {
            "type": task_generated_data.get("type", "Task"),
            "summary": task_generated_data.get("summary", summary),
            "description": task_generated_data.get("description", ""),
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
        QTimer.singleShot(0, self.adjust_height_to_content)

        type_index = self.type_dropdown.findText(self.task_data["type"])
        if type_index >= 0:
            self.type_dropdown.setCurrentIndex(type_index)

        index = self.component_dropdown.findText(self.task_data["component"])
        if index >= 0:
            self.component_dropdown.setCurrentIndex(index)
        
        self.step = 1

    def submit_task(self):
        summary, description = parse_task_text(self.textarea.toPlainText())

        if not summary:
            self.show_toast("Please enter a task summary in the first line.")
            return

        issue_type = self.type_dropdown.currentText()
        component = self.component_dropdown.currentText()

        self.task_data = self.jira.submit_task(summary, description, issue_type, component)

        jira_url = self.task_data["url"]
        task_key = self.task_data["key"]

        toast_text = f'✅ Task <a href="{jira_url}">{task_key}</a> created (copied)'
        # 📋 Copy key to clipboard
        try:
            QApplication.clipboard().setText(task_key)
        except Exception as e:
            toast_text = ("Task created, but clipboard copy failed.")

        self.show_toast(toast_text)

        self.reset_ui()

    def show_toast(self, message: str):

        toast = ToastMessage(message)
        x = self.x() + (self.width() - toast.width()) // 2
        y = self.y() + self.height() + 10

        toast.show_at(x, y)

        self.toast = toast  # Keep reference alive!

    def fix_screen_position(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = int(screen.height() * 0.2)  # top 20% of screen
        self.move(x, y)

    @Slot()
    def show_config(self):
        self.fix_screen_position()
        dialog = ConfigEditorDialog(self)
        if dialog.exec():  # Will return True if dialog was accepted
            self.refresh_from_config()

    @Slot()
    def show_launcher(self):
        self.fix_screen_position()

        # 🔥 Pre-fill from clipboard
        if not self.input.text().strip():
            clipboard = QApplication.clipboard()
            text = clipboard.text().strip()
            if text:
                self.input.setText(text)

        self.show()
        self.activateWindow()
        self.raise_()
        self.input.setFocus()

