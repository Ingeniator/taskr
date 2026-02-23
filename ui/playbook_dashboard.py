import json
import os

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QListWidget, QTextEdit, QStackedWidget, QPushButton,
    QGraphicsDropShadowEffect, QScrollArea, QLineEdit, QSplitter,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from services.playbook_runner import PlaybookRunner

_PARAMS_CACHE = os.path.expanduser("~/.config/CtrlLord/data/playbook_params.json")


class PlaybookDashboard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(850, 550)

        self._playbooks = []
        self._runners: dict[str, PlaybookRunner] = {}
        self._step_labels = []
        self._param_fields: list[tuple[str, QLineEdit]] = []
        self._playbook_logs: dict[str, list[str]] = {}
        self._playbook_step_states: dict[str, list[tuple[str, str]]] = {}
        self._current_file_path: str = ""
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
        container.setObjectName("PlaybookContainer")
        container.setStyleSheet("""
            #PlaybookContainer {
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

        header = QLabel("Playbooks")
        header.setFont(QFont("Helvetica Neue", 16, QFont.Bold))
        left_layout.addWidget(header)

        subtitle = QLabel("Run sequential steps")
        subtitle.setStyleSheet("color: #888; font-size: 12px;")
        left_layout.addWidget(subtitle)
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

        # --- Right panel ---
        self._stack = QStackedWidget()

        # Index 0: empty state
        empty = QLabel("No playbooks found")
        empty.setAlignment(Qt.AlignCenter)
        empty.setStyleSheet("color: #888; font-size: 14px;")
        self._stack.addWidget(empty)

        # Index 1: detail view
        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(16, 16, 16, 16)
        detail_layout.setSpacing(8)

        self._name_label = QLabel()
        self._name_label.setFont(QFont("Helvetica Neue", 18, QFont.Bold))
        self._name_label.setWordWrap(True)
        detail_layout.addWidget(self._name_label)

        self._desc_label = QLabel()
        self._desc_label.setStyleSheet("color: #888; font-size: 12px;")
        self._desc_label.setWordWrap(True)
        detail_layout.addWidget(self._desc_label)

        self._cwd_label = QLabel()
        self._cwd_label.setStyleSheet("color: #888; font-size: 11px;")
        detail_layout.addWidget(self._cwd_label)

        # Param input fields
        self._params_layout = QVBoxLayout()
        self._params_layout.setContentsMargins(0, 4, 0, 4)
        self._params_layout.setSpacing(4)
        detail_layout.addLayout(self._params_layout)

        # Splitter: steps on top, log on bottom
        splitter = QSplitter(Qt.Vertical)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #555;
                height: 3px;
                border-radius: 1px;
                margin: 2px 40px;
            }
        """)

        # Step list in scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self._steps_widget = QWidget()
        self._steps_layout = QVBoxLayout(self._steps_widget)
        self._steps_layout.setContentsMargins(0, 4, 0, 4)
        self._steps_layout.setSpacing(2)
        self._steps_layout.addStretch()
        scroll.setWidget(self._steps_widget)
        splitter.addWidget(scroll)

        # Log viewer
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFont(QFont("Menlo", 11))
        self._log.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        splitter.addWidget(self._log)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        detail_layout.addWidget(splitter, 1)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)

        self._run_btn = QPushButton("Run")
        self._run_btn.setFixedWidth(80)
        self._run_btn.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 13px;
            }
            QPushButton:disabled {
                background-color: #555;
            }
        """)
        self._run_btn.clicked.connect(self._on_run)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setFixedWidth(80)
        self._stop_btn.setEnabled(False)
        self._stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF3B30;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 13px;
            }
            QPushButton:disabled {
                background-color: #555;
            }
        """)
        self._stop_btn.clicked.connect(self._on_stop)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setFixedWidth(80)
        self._clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 13px;
            }
        """)
        self._clear_btn.clicked.connect(self._on_clear)

        btn_layout.addWidget(self._run_btn)
        btn_layout.addWidget(self._stop_btn)
        btn_layout.addWidget(self._clear_btn)
        btn_layout.addStretch()
        detail_layout.addLayout(btn_layout)

        self._stack.addWidget(detail)

        main_layout.addWidget(self._stack, 1)
        outer.addWidget(container)

        self._list.currentRowChanged.connect(self._on_row_changed)

    def load_playbooks(self, playbooks: list[dict]):
        self._playbooks = playbooks
        self._list.clear()
        self._clear_detail()

        if not playbooks:
            self._stack.setCurrentIndex(0)
            return

        self._stack.setCurrentIndex(1)
        for pb in playbooks:
            self._list.addItem(pb["name"])

        self._list.setCurrentRow(0)

    def _clear_detail(self):
        self._name_label.clear()
        self._desc_label.clear()
        self._cwd_label.clear()
        self._log.clear()
        self._current_file_path = ""
        self._clear_step_labels()
        self._clear_param_fields()

    def _clear_step_labels(self):
        for label in self._step_labels:
            self._steps_layout.removeWidget(label)
            label.deleteLater()
        self._step_labels = []

    def _load_saved_params(self, file_path: str) -> dict:
        try:
            with open(_PARAMS_CACHE) as f:
                return json.load(f).get(file_path, {})
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_params(self, file_path: str, values: dict):
        try:
            with open(_PARAMS_CACHE) as f:
                cache = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            cache = {}
        cache[file_path] = values
        os.makedirs(os.path.dirname(_PARAMS_CACHE), exist_ok=True)
        with open(_PARAMS_CACHE, "w") as f:
            json.dump(cache, f, indent=2)

    def _display_log(self, file_path: str):
        self._log.clear()
        for line in self._playbook_logs.get(file_path, []):
            self._log.append(line)

    def _clear_param_fields(self):
        for _name, widget in self._param_fields:
            label = self._params_layout.itemAt(
                self._params_layout.indexOf(widget) - 1
            )
            if label and label.widget():
                label.widget().deleteLater()
            widget.deleteLater()
        self._param_fields = []

    def _on_row_changed(self, row):
        if row < 0 or row >= len(self._playbooks):
            return
        pb = self._playbooks[row]
        self._current_file_path = pb.get("file_path", "")
        self._name_label.setText(pb["name"])
        self._desc_label.setText(pb.get("description", ""))
        self._cwd_label.setText(f"cwd: {pb.get('cwd', '')}")
        self._display_log(self._current_file_path)

        self._clear_param_fields()
        saved = self._load_saved_params(pb.get("file_path", ""))
        for param in pb.get("params", []):
            lbl = QLabel(param["label"])
            lbl.setStyleSheet("font-size: 12px; color: #aaa;")
            field = QLineEdit()
            field.setText(saved.get(param["name"], param.get("default", "")))
            field.setStyleSheet("font-size: 13px; padding: 4px;")
            self._params_layout.addWidget(lbl)
            self._params_layout.addWidget(field)
            self._param_fields.append((param["name"], field))

        self._clear_step_labels()
        saved_states = self._playbook_step_states.get(self._current_file_path)
        for i, step in enumerate(pb["steps"]):
            if saved_states and i < len(saved_states):
                icon, color = saved_states[i]
            else:
                icon, color = "\u25CB", "#888"
            lbl = QLabel(f"  {icon}  {step['name']}")
            lbl.setFont(QFont("Helvetica Neue", 13))
            lbl.setStyleSheet(f"color: {color};")
            self._steps_layout.insertWidget(self._steps_layout.count() - 1, lbl)
            self._step_labels.append(lbl)

        self._update_buttons()

    def _on_run(self):
        row = self._list.currentRow()
        if row < 0 or row >= len(self._playbooks):
            return

        pb = self._playbooks[row]
        fp = pb.get("file_path", "")

        # Don't start if this playbook already has a running runner
        if fp in self._runners and self._runners[fp].isRunning():
            return

        # Reset step states for this playbook
        n_steps = len(pb["steps"])
        self._playbook_step_states[fp] = [
            ("\u25CB", "#888") for _ in range(n_steps)
        ]
        for lbl in self._step_labels:
            step_name = lbl.text().split("  ", 2)[-1]
            lbl.setText(f"  \u25CB  {step_name}")
            lbl.setStyleSheet("color: #888;")
        self._log.clear()
        self._playbook_logs[fp] = []

        env_overrides = {name: field.text() for name, field in self._param_fields}
        if env_overrides:
            self._save_params(fp, env_overrides)

        runner = PlaybookRunner(pb, env_overrides=env_overrides, parent=self)
        runner.step_started.connect(lambda i, n, _fp=fp: self._on_step_started(_fp, i, n))
        runner.step_finished.connect(lambda i, s, _fp=fp: self._on_step_finished(_fp, i, s))
        runner.log_line.connect(lambda t, _fp=fp: self._on_log_line(_fp, t))
        runner.playbook_finished.connect(lambda s, _fp=fp: self._on_playbook_finished(_fp, s))
        self._runners[fp] = runner

        self._update_buttons()
        runner.start()

    def _on_stop(self):
        runner = self._runners.get(self._current_file_path)
        if runner is not None:
            runner.stop()

    def _on_clear(self):
        self._playbook_logs[self._current_file_path] = []
        self._log.clear()
        # Reset step labels to pending
        self._playbook_step_states.pop(self._current_file_path, None)
        for lbl in self._step_labels:
            step_name = lbl.text().split("  ", 2)[-1]
            lbl.setText(f"  \u25CB  {step_name}")
            lbl.setStyleSheet("color: #888;")

    def _update_buttons(self):
        runner = self._runners.get(self._current_file_path)
        running = runner is not None and runner.isRunning()
        self._run_btn.setEnabled(not running)
        self._stop_btn.setEnabled(running)

    def _on_step_started(self, file_path, index, name):
        states = self._playbook_step_states.get(file_path)
        if states and 0 <= index < len(states):
            states[index] = ("\u25B6", "#007AFF")
        if file_path == self._current_file_path:
            if 0 <= index < len(self._step_labels):
                lbl = self._step_labels[index]
                lbl.setText(f"  \u25B6  {name}")
                lbl.setStyleSheet("color: #007AFF;")

    def _on_step_finished(self, file_path, index, success):
        icon = "\u2713" if success else "\u2717"
        color = "#34C759" if success else "#FF3B30"
        states = self._playbook_step_states.get(file_path)
        if states and 0 <= index < len(states):
            states[index] = (icon, color)
        if file_path == self._current_file_path:
            if 0 <= index < len(self._step_labels):
                lbl = self._step_labels[index]
                step_name = lbl.text().split("  ", 2)[-1]
                lbl.setText(f"  {icon}  {step_name}")
                lbl.setStyleSheet(f"color: {color};")

    def _on_log_line(self, file_path, text):
        self._playbook_logs.setdefault(file_path, []).append(text)
        if file_path == self._current_file_path:
            self._log.append(text)
            scrollbar = self._log.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _on_playbook_finished(self, file_path, success):
        if file_path == self._current_file_path:
            self._update_buttons()

    def show_at(self, x, y):
        self.move(x, y)
        self.show()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)
