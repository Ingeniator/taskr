# ui/launcher.py
import logging
import traceback

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
from services.json_service import JsonService
from services.task_generator_service import TaskGeneratorService
from services.task_queue import TaskQueueWorker, TaskPayload
from services.task_loader import load_todays_tasks
from services.playbook_loader import load_playbooks
from services.config import load_config, get_resource_path

from ui.toast import ToastMessage
from ui.styles import NoCheckmarkBoldSelectedDelegate
from ui.config import ConfigEditorDialog
from ui.dashboard import TaskDashboard
from ui.playbook_dashboard import PlaybookDashboard

logger = logging.getLogger(__name__)

MAX_CLIPBOARD_LENGTH = 500

BACKENDS = {
    "jira": JiraService,
    "json": JsonService,
}


def _create_task_service():
    config = load_config()
    backend = config.get("task", {}).get("backend", "json")
    cls = BACKENDS.get(backend)
    if cls is None:
        raise ValueError(f"Unknown task backend: {backend!r}. Choose from: {', '.join(BACKENDS)}")
    return cls()


class CtrlLord(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(700, 180)

        self.step = 0
        self._active_toasts = []

        self.generator = TaskGeneratorService()
        self.task_service = _create_task_service()

        self._worker = TaskQueueWorker(self.task_service)
        self._worker.task_completed.connect(self._on_task_completed)
        self._worker.task_failed.connect(self._on_task_failed)
        self._worker.start()

        QApplication.instance().aboutToQuit.connect(self._shutdown_worker)

        self.init_ui()
        self.create_tray()

    def create_tray(self):
        # Load tray icon
        tray_icon_path = get_resource_path("resources/icon.png")
        icon = QIcon(tray_icon_path)
        if icon.isNull():
            logger.error("Failed to load tray icon from %s", tray_icon_path)
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(icon)
        self.tray.setToolTip("CtrlLord")

        menu = QMenu(self)
        open_action = QAction("Create Task", self)
        open_action.triggered.connect(self.show_launcher)
        menu.addAction(open_action)
        dashboard_action = QAction("Today's Tasks", self)
        dashboard_action.triggered.connect(self.toggle_dashboard)
        menu.addAction(dashboard_action)
        playbook_action = QAction("Playbooks", self)
        playbook_action.triggered.connect(self.toggle_playbook_dashboard)
        menu.addAction(playbook_action)
        menu.addSeparator()
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_config)
        menu.addAction(settings_action)
        menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.setVisible(True)

    def eventFilter(self, obj, event):
        try:
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
        except Exception as e:
            logger.error("Error in eventFilter: %s", e)
            logger.debug(traceback.format_exc())
            return False
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
        if hasattr(self, "_dashboard"):
            self._dashboard.hide()
        if hasattr(self, "_playbook_dashboard"):
            self._playbook_dashboard.hide()
        self.hide()

    def refresh_from_config(self):
        try:
            config = load_config()
            self.task_service.reload_config(config)
            self.generator.reload_config(config)
        except Exception as e:
            logger.error("Error during reconfiguration: %s", e)
            self.show_toast(str(e))
            return

        logger.info("UI reloading categories")
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
        self.input.returnPressed.connect(self.handle_enter)
        self.input.installEventFilter(self)

        # Dashboard icon inside input field
        dashboard_icon = QIcon(get_resource_path("resources/dashboard.svg"))
        self._dashboard_action = self.input.addAction(
            dashboard_icon, QLineEdit.TrailingPosition
        )
        self._dashboard_action.triggered.connect(self.toggle_dashboard)

        playbook_icon = QIcon(get_resource_path("resources/playbook.svg"))
        self._playbook_action = self.input.addAction(
            playbook_icon, QLineEdit.TrailingPosition
        )
        self._playbook_action.triggered.connect(self.toggle_playbook_dashboard)
        self.input.setStyleSheet("""
            QLineEdit {
                padding: 14px 38px 14px 24px;
                border-radius: 14px;
                border: 1px solid #ccc;
            }
        """)

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

        # Use first component from dropdown as default instead of hardcoded value
        default_component = self.component_dropdown.itemText(0) if self.component_dropdown.count() > 0 else ""

        self.task_data = {
            "type": task_generated_data.get("type", "Task"),
            "summary": task_generated_data.get("summary", summary),
            "description": task_generated_data.get("description", ""),
            "component": default_component
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

        payload = TaskPayload(
            summary=summary,
            description=description,
            issue_type=issue_type,
            component=component,
        )
        self._worker.enqueue(payload)
        self.reset_ui()

    @Slot(dict)
    def _on_task_completed(self, result):
        jira_url = result.get("url")
        task_key = result.get("key")
        toast_text = f'Task <a href="{jira_url}">{task_key}</a> created (copied)'

        try:
            QApplication.clipboard().setText(task_key)
        except Exception as e:
            logger.warning("Clipboard copy failed: %s", e)
            toast_text = "Task created, but clipboard copy failed."

        self._show_background_toast(toast_text)

    @Slot(str, object)
    def _on_task_failed(self, error, payload):
        self._show_background_toast(f"Failed to create task: {error}")

    def show_toast(self, message: str):
        toast = ToastMessage(message)
        x = self.x() + (self.width() - toast.width()) // 2
        y = self.y() + self.height() + 10
        toast.show_at(x, y)
        self._active_toasts.append(toast)
        toast.destroyed.connect(lambda: self._active_toasts.remove(toast) if toast in self._active_toasts else None)

    def _show_background_toast(self, message: str):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        toast = ToastMessage(message)
        x = (screen.width() - toast.width()) // 2
        y = int(screen.height() * 0.2)
        toast.show_at(x, y)
        self._active_toasts.append(toast)
        toast.destroyed.connect(lambda: self._active_toasts.remove(toast) if toast in self._active_toasts else None)

    def _shutdown_worker(self):
        self._worker.stop()
        self._worker.wait(5000)

    def fix_screen_position(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = int(screen.height() * 0.2)  # top 20% of screen
        self.move(x, y)

    @Slot()
    def toggle_dashboard(self):
        if not hasattr(self, "_dashboard"):
            self._dashboard = TaskDashboard()

        if self._dashboard.isVisible():
            self._dashboard.hide()
            return

        config = load_config()
        data_dir = config.get("task", {}).get("data_dir", "~/.config/CtrlLord/data")
        tasks = load_todays_tasks(data_dir)
        self._dashboard.load_tasks(tasks)

        screen = QGuiApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self._dashboard.width()) // 2
        y = int(screen.height() * 0.1) + self.height() + 10
        self._dashboard.show_at(x, y)

    @Slot()
    def toggle_playbook_dashboard(self):
        if not hasattr(self, "_playbook_dashboard"):
            self._playbook_dashboard = PlaybookDashboard()

        if self._playbook_dashboard.isVisible():
            self._playbook_dashboard.hide()
            return

        config = load_config()
        pb_cfg = config.get("playbook")
        if not pb_cfg:
            self.show_toast("Add [playbook] section to config")
            return

        playbook_dir = pb_cfg.get("playbook_dir", "~/.config/CtrlLord/playbooks")
        playbooks = load_playbooks(playbook_dir)
        self._playbook_dashboard.load_playbooks(playbooks)

        screen = QGuiApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self._playbook_dashboard.width()) // 2
        y = int(screen.height() * 0.1) + self.height() + 10
        self._playbook_dashboard.show_at(x, y)

    @Slot()
    def show_config(self):
        self.fix_screen_position()
        dialog = ConfigEditorDialog(self)
        if dialog.exec():  # Will return True if dialog was accepted
            self.refresh_from_config()

    @Slot()
    def show_launcher(self):
        self.fix_screen_position()

        # Pre-fill from clipboard (with length limit)
        if not self.input.text().strip():
            clipboard = QApplication.clipboard()
            text = clipboard.text().strip()
            if text and len(text) <= MAX_CLIPBOARD_LENGTH:
                self.input.setText(text)

        self.show()
        self.activateWindow()
        self.raise_()
        self.input.setFocus()
