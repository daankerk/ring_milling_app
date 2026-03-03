# imports
from PyQt6.QtWidgets import QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget, QInputDialog, QMessageBox, QGridLayout, QTextEdit, QFrame, QFileDialog
from PyQt6.QtGui import QImage, QPixmap, QDesktopServices
from PyQt6.QtCore import Qt, QUrl
from datetime import datetime
import json
import cv2
from core.camera_thread import CameraThread
from gui.calibration_window import CalibrationWindow
from gui.tool_path_window import ToolPathWindow
from gui.setting_window import SettingWindow
from core.read_config import cal_dir, camera_index, std_save_flag

class MainWindow(QMainWindow):
    # initializations
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ringing, Milling and Chilling")
        self.setGeometry(0, 0, 800, 800)

        # initialize tp selection frame
        self.latest_frame = None

        # set the archive save flag
        self.save_flag = std_save_flag

        # see if calibration is loaded
        self.calibration_flag = False

        # initialize the mill gap
        self.mill_gap = 3#0

        # read the calibration file path
        calibration_file_path = cal_dir

        # create the log string
        self.log_str = []

        # read initial calibration values from the file
        with open(calibration_file_path) as f:
            lines = [line.strip() for line in f if line.strip()]
            self.x_offset_ini = self.y_offset_ini = 0
            for line in lines:
                if line.startswith("X"):
                    self.x_offset_ini = float(line[1:])
                elif line.startswith("Y"):
                    self.y_offset_ini = float(line[1:])

        # assign the initial offset
        self.x_offset = self.x_offset_ini
        self.y_offset = self.y_offset_ini

        # create the initial information string
        # self.info_str = ["Information:\n\n"
        #                  "X-offset:\t", f"{self.x_offset}", " [mm]\n",
        #                  "Y-offset:\t", f"{self.y_offset}", " [mm]\n",
        #                  "Mill Gap:\t", f"{self.mill_gap}", " [mm]\n"
        #                  "Save flag:      ", f"{self.save_flag}", "\n"]
        self.info_str = "Please Load A Calibration File"
        self.info_str_combined = "".join(map(str, self.info_str))

        # live camera feed
        self.live_label = QLabel(self)
        cap = cv2.VideoCapture(camera_index)
        self.cam_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.cam_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        # self.live_label.setFixedSize(self.cam_width, self.cam_height)
        self.live_label.setFixedSize(self.cam_height, self.cam_width)

        # input mill gap button with indicator
        self.gap_button = QPushButton("Set Mill Gap")
        self.gap_button.clicked.connect(lambda: self.input_number("mill_gap"))

        # input x offset
        self.change_x_offset_button = QPushButton("Change X Offset")
        self.change_x_offset_button.clicked.connect(lambda: self.input_number("x_offset"))

        # input y offset
        self.change_y_offset_button = QPushButton("Change Y Offset")
        self.change_y_offset_button.clicked.connect(lambda: self.input_number("y_offset"))

        # create calibration button
        self.create_cal_button = QPushButton("Create Calibration")
        self.create_cal_button.clicked.connect(self.create_calibration)

        # load calibration button
        self.load_cal_button = QPushButton("Load Calibration")
        self.load_cal_button.clicked.connect(self.load_calibration)

        # flag for saving g-codes to archive yes or no
        self.save_flag_button = QPushButton("Change Save Flag")
        self.save_flag_button.clicked.connect(self.change_save_flag)

        # tool path selection button
        self.tp_button = QPushButton("Select Tool Path")
        self.tp_button.clicked.connect(self.capture_image)

        # settings
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.change_settings)

        # manual button
        self.manual_button = QPushButton("Manual")
        self.manual_button.clicked.connect(self.open_manual)

        # create the central layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QGridLayout()

        # add the live camera view
        main_layout.addWidget(self.live_label, 0, 0, 1, 1, alignment=Qt.AlignmentFlag.AlignCenter)

        # add the log box
        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)
        self.text_log.setText("\n".join(self.log_str))
        main_layout.addWidget(self.text_log, 1, 0, 1, 1)

        # add the buttons
        button_layout = QVBoxLayout()
        # button_layout.addWidget(self.change_x_offset_button)
        # button_layout.addWidget(self.change_y_offset_button)
        # button_layout.addWidget(self.gap_button)
        # button_layout.addWidget(self.res_cal_button)
        button_layout.addWidget(self.tp_button)
        button_layout.addWidget(self.create_cal_button)
        button_layout.addWidget(self.load_cal_button)
        button_layout.addWidget(self.save_flag_button)
        button_layout.addWidget(self.settings_button)
        button_layout.addWidget(self.manual_button)

        button_layout.addStretch()
        button_layout.setSpacing(20)

        button_widget = QFrame()
        button_widget.setFrameShape(QFrame.Shape.Box)
        button_widget.setFrameShadow(QFrame.Shadow.Raised)

        button_widget.setLayout(button_layout)
        main_layout.addWidget(button_widget, 0, 1, 1, 1)

        # add the info section
        self.info_label = QLabel(self.info_str_combined)
        main_layout.addWidget(self.info_label, 1, 1, 1, 1, alignment=Qt.AlignmentFlag.AlignTop)

        # Set complete layout
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
        if self.calibration_flag == False:
            self.append_log_string("No calibration loaded. Please load a calibration file.")
            QMessageBox.critical(self, "Error", "No Calibration File Loaded!")
            return

        self.append_log_string("Opening Tool Path Selection...")
        if self.latest_frame is not None:
            self.toolpath_window = ToolPathWindow(self.latest_frame, self.x_offset, self.y_offset, self.mill_gap, self.save_flag)
            self.toolpath_window.show()

    def input_number(self, variable):
            current_value = float(getattr(self, variable))
            number, ok = QInputDialog.getDouble(
                self,
                "Input por favor",  # window title
                "Please enter the distance in mm:",  # label text
                value=current_value,  # default value
                min=0,  # minimum
                max=1000  # maximum
            )
            if ok:
                # assign the number
                setattr(self, variable, number)
                # update the log/info label
                self.append_log_string(f"changed {variable} to:")
                self.append_log_string(str(number))
                self.update_info_label()

    def create_calibration(self):
        self.append_log_string("Opening Calibration Window")
        if self.latest_frame is not None:
            self.calibration_window = CalibrationWindow(self.latest_frame)
            self.calibration_window.show()

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

    def change_save_flag(self):
        self.save_flag = not self.save_flag
        self.append_log_string("Changing save flag...")
        self.update_info_label()

    def change_settings(self):
        self.append_log_string("changing settings jaja")
        self.setting_window = SettingWindow()
        self.setting_window.show()

    def open_manual(self):
        self.append_log_string("Opening Manual...")
        QDesktopServices.openUrl(
            QUrl.fromLocalFile("/home/daan/Documents/thesis/engineering/coding/ring_milling_app/resources/app_manual.pdf")
        )

    def append_log_string(self, input_str):
        current_time = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{current_time}] {input_str}"
        self.text_log.append(log_line)
        print(log_line)

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