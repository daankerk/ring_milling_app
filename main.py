import sys
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow
from gui.app_style import base_style

# run the GUI
def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(base_style)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()