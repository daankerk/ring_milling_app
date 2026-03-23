from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from core.read_config import config_path
import json

class ShowConfigWindow(QWidget):
    def __init__(self, path = config_path):
        super().__init__()
        self.path = path
        self.setWindowTitle("Show Configuration File")
        self.setGeometry(500, 500, 1000, 300)

        with open(path, "r") as f:
            self.settings_list = json.load(f)

        layout = QVBoxLayout()

        for key, value in self.settings_list.items():
            label = QLabel(f"{key}:\n\n{value}")
            layout.addWidget(label)

        self.setLayout(layout)
