# imports
from PyQt6.QtWidgets import QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget, QMessageBox, QGridLayout, QTextEdit, QFrame, QFileDialog
from PyQt6.QtGui import QImage, QPixmap, QDesktopServices
from PyQt6.QtCore import Qt, QUrl
from datetime import datetime
import json
import cv2
from core.camera_thread import CameraThread
from gui.calibration_window import CalibrationWindow
from gui.tool_path_window import ToolPathWindow
from gui.show_config_window import ShowConfigWindow
from core.read_config import camera_index, std_save_flag

class MainWindow(QMainWindow):
    # initializations
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ringing, Milling and Chilling")
        self.setGeometry(0, 0, 800, 800)

        # initialize variables
        self.latest_frame = None
        self.save_flag = std_save_flag  # set the standard save flag from config.json
        self.calibration_flag = False   # to cancel proceeding without a calibration file

        # set initial information string
        self.info_str = "Please Load A Calibration File"
        self.info_str_combined = "".join(map(str, self.info_str))

        # get the live camera feed dimensions for the layout
        self.live_label = QLabel(self)
        cap = cv2.VideoCapture(camera_index)
        self.cam_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.cam_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        # self.live_label.setFixedSize(self.cam_width, self.cam_height)     # horizontal placement
        self.live_label.setFixedSize(self.cam_height, self.cam_width)       # vertical placement

        # tool path selection button
        self.tp_button = QPushButton("Select Tool Path")
        self.tp_button.clicked.connect(self.capture_image)

        # create calibration button
        self.create_cal_button = QPushButton("Create Calibration")
        self.create_cal_button.clicked.connect(self.create_calibration)

        # load calibration button
        self.load_cal_button = QPushButton("Load Calibration")
        self.load_cal_button.clicked.connect(self.load_calibration)

        # flag for saving g-codes to archive yes or no
        self.save_flag_button = QPushButton("Change Save Flag")
        self.save_flag_button.clicked.connect(self.change_save_flag)

        # show config file button
        self.show_config_button = QPushButton("Show Configuration")
        self.show_config_button.clicked.connect(self.show_config)

        # manual button
        self.manual_button = QPushButton("Manual")
        self.manual_button.clicked.connect(self.open_manual)

        # create the central layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QGridLayout()

        # add the live camera view in the window
        main_layout.addWidget(self.live_label, 0, 0, 1, 1, alignment=Qt.AlignmentFlag.AlignCenter)

        # add the log box in the window
        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)
        self.text_log.setText("\n".join([]))
        main_layout.addWidget(self.text_log, 1, 0, 1, 1)

        # add the buttons to the window
        button_layout = QVBoxLayout()
        button_layout.addWidget(self.tp_button)
        button_layout.addWidget(self.create_cal_button)
        button_layout.addWidget(self.load_cal_button)
        button_layout.addWidget(self.save_flag_button)
        button_layout.addWidget(self.show_config_button)
        button_layout.addWidget(self.manual_button)

        button_layout.addStretch()
        button_layout.setSpacing(20)

        button_widget = QFrame()
        button_widget.setFrameShape(QFrame.Shape.Box)
        button_widget.setFrameShadow(QFrame.Shadow.Raised)

        button_widget.setLayout(button_layout)
        main_layout.addWidget(button_widget, 0, 1, 1, 1)

        # add the info section to the window
        self.info_label = QLabel(self.info_str_combined)
        main_layout.addWidget(self.info_label, 1, 1, 1, 1, alignment=Qt.AlignmentFlag.AlignTop)

        # set complete layout
        central_widget.setLayout(main_layout)

        # retrieve the image and connect to update function
        self.camera_thread = CameraThread()
        self.camera_thread.frame_ready.connect(self.update_frame)
        self.camera_thread.start()

        # mention the start-up
        self.append_log_string("Application Started Successfully")

    # make sure thread is shut down when window's closed
    def closeEvent(self, event):
        if self.camera_thread is not None:
            self.camera_thread.requestInterruption()
            self.camera_thread.quit()
            self.camera_thread.wait()
        event.accept()

    # function taking image for tp selection
    def capture_image(self):
        # display error when no mill gap is set
        if not self.calibration_flag:
            self.append_log_string("No calibration loaded. Please load a calibration file.")
            QMessageBox.critical(self, "Error", "No Calibration File Loaded!")
            return

        self.append_log_string("Opening Tool Path Selection...")
        if self.latest_frame is not None:
            self.toolpath_window = ToolPathWindow(self.latest_frame, self.x_offset, self.y_offset, self.mill_gap, self.save_flag, self.pix2mm)
            self.toolpath_window.show()

    # open the calibration creation window
    def create_calibration(self):
        self.append_log_string("Opening Calibration Window")
        if self.latest_frame is not None:
            self.calibration_window = CalibrationWindow(self.latest_frame)
            self.calibration_window.show()

    # load a calibration from a json file
    def load_calibration(self):
        self.append_log_string("Loading Calibration")

        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select JSON File",
            "",
            "JSON Files (*.json)"  # only .json allowed
        )

        # if the user closes the selection window
        if not file_name:
            self.append_log_string("Calibration loading cancelled. No file selected.")
            return

        try:
            # open the file
            with open(file_name, "r") as f:
                calibration_data = json.load(f)

            # see if the necessary values are there
            required_keys = [
                "pixels_per_mm",
                "camera_X_offset",
                "camera_Y_offset",
                "end_mill_gap",
                "microscope_height"
            ]

            missing_keys = [key for key in required_keys if key not in calibration_data]

            if missing_keys:
                raise KeyError(f"Missing keys: {', '.join(missing_keys)}")

            for key in required_keys:
                if not isinstance(calibration_data[key], (int, float)):
                    raise TypeError(f"'{key}' must be a number")

            self.pix2mm = calibration_data["pixels_per_mm"]
            self.x_offset = calibration_data["camera_X_offset"]
            self.y_offset = calibration_data["camera_Y_offset"]
            self.mill_gap = calibration_data["end_mill_gap"]
            self.microscope_height = calibration_data["microscope_height"]

            self.calibration_flag = True
            self.update_info_label()
            self.append_log_string("Calibration Loaded Successfully")

        except KeyError as e:
            QMessageBox.critical(self, "Error", f"Calibration file missing data:\n{e}")
            self.append_log_string(f"Error: {e}")

        except TypeError as e:
            QMessageBox.critical(self, "Error", f"Invalid data type:\n{e}")
            self.append_log_string(f"Error: {e}")

    # change the saving flag
    def change_save_flag(self):
        if not self.calibration_flag:
            self.append_log_string("No calibration loaded. Please load a calibration file.")
            QMessageBox.critical(self, "Error", "No Calibration File Loaded!")
            return

        self.save_flag = not self.save_flag
        self.append_log_string("Changing save flag...")
        self.update_info_label()

    # shows the items in the config file
    def show_config(self):
        self.append_log_string("Showing config file")
        self.show_config_window = ShowConfigWindow()
        self.show_config_window.show()

    # opens the app manual
    def open_manual(self):
        self.append_log_string("Opening Manual...")
        QDesktopServices.openUrl(
            QUrl.fromLocalFile("/home/daan/Documents/thesis/engineering/coding/ring_milling_app/resources/app_manual.pdf")
        )

    # adds text to the log
    def append_log_string(self, input_str):
        current_time = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{current_time}] {input_str}"
        self.text_log.append(log_line)
        print(log_line)

    # function updates the info label
    def update_info_label(self):
        self.info_str = [
            "Information:\n\n",
            "X-offset:\t", f"{self.x_offset:.2f}", " [mm]\n",
            "Y-offset:\t", f"{self.y_offset:.2f}", " [mm]\n",
            "Mill Gap:\t", f"{self.mill_gap:.2f}", " [mm]\n",
            "Camera Height:\t", f"{self.microscope_height:.2f}", " [mm]\n",
            "Pixels per mm:\t", f"{self.pix2mm:.2f}", " [mm]\n",
            "Save flag:      ", f"{self.save_flag}", "\n"
        ]
        self.info_str_combined = "".join(map(str, self.info_str))
        self.info_label.setText(self.info_str_combined)

    # take the updated frame and put it in the GUI
    def update_frame(self, frame):
        self.latest_frame = frame.copy()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w

        qt_image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.live_label.setPixmap(QPixmap.fromImage(qt_image))