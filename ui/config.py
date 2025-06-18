import yaml
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QPlainTextEdit, QPushButton, QMessageBox
)
from PySide6.QtCore import Slot

from services.config import CONFIG_PATH

class ConfigEditorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Configuration")
        self.setMinimumSize(500, 400)
        self.config_path = CONFIG_PATH

        self.editor = QPlainTextEdit()
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_config)

        layout = QVBoxLayout(self)
        layout.addWidget(self.editor)
        layout.addWidget(self.save_button)

        self.load_config()

    def load_config(self):
        try:
            with open(self.config_path, "r") as f:
                self.editor.setPlainText(f.read())
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load config:\n{e}")

    def save_config(self):
        try:
            yaml.safe_load(self.editor.toPlainText())  # validate YAML
            with open(self.config_path, "w") as f:
                f.write(self.editor.toPlainText())
            print("✅ Configuration saved.")
            self.accept() 
        except yaml.YAMLError as e:
            QMessageBox.warning(self, "YAML Error", f"Invalid YAML:\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save config:\n{e}")