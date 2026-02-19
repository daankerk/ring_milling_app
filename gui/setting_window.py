from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton
from core.read_config import config_path
import json

class SettingWindow(QWidget):
    def __init__(self, path = config_path):
        super().__init__()
        self.path = path
        self.setWindowTitle("Edit Settings")
        self.setGeometry(500, 500, 1000, 300)
        layout = QVBoxLayout(self)

        self.editor = QTextEdit()
        layout.addWidget(self.editor)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save)
        layout.addWidget(save_btn)

        with open(path, "r") as f:
            self.editor.setText(f.read())

    def save(self):
        try:
            json.loads(self.editor.toPlainText())  # validate
            with open(self.path, "w") as f:
                f.write(self.editor.toPlainText())
        except json.JSONDecodeError:
            print("Invalid JSON")
