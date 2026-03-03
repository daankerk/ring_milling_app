import ast
import json
import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QLineEdit, QFormLayout, QPushButton, QVBoxLayout, QMessageBox, \
    QSpacerItem, QSizePolicy, QFileDialog
import cv2
import math

class CalibrationWindow(QWidget):
    def __init__(self, frame):
        super().__init__()
        self.setWindowTitle("Create Calibration File")

        # initialize variables
        self.coord1 = None
        self.coord2 = None
        self.xy_distance = None
        self.mm_length_input = None

        # initialize the files that get saved eventually
        self.px2mm = None
        self.x_offset_input = None
        self.y_offset_input = None
        self.end_mill_height = None
        self.microscope_height = None


        # initialize selected coordinate flag
        self.active_point = None

        # take the image
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        self.image_center_x = w // 2
        self.image_center_y = h // 2
        self.qt_image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

        # create the label image
        self.capture = QLabel()
        self.capture_pm = QPixmap.fromImage(self.qt_image)
        self.capture.setPixmap(self.capture_pm)
        self.capture.setFixedSize(w, h)

        # enable mouse tracking
        self.capture.setMouseTracking(True)
        self.capture.mousePressEvent = self.get_px_coords

        # create the input and output fields
        self.microscope_height_input_line = QLineEdit()
        self.microscope_height_input_line.editingFinished.connect(self.calculate_func)
        self.microscope_height_input_line.editingFinished.connect(lambda: self.update_value(self.microscope_height_input_line, "microscope_height"))

        self.mm_length_input_line = QLineEdit()
        self.mm_length_input_line.editingFinished.connect(self.calculate_func)
        self.mm_length_input_line.editingFinished.connect(lambda: self.update_value(self.mm_length_input_line, "mm_length_input"))

        self.end_mill_height_input_line = QLineEdit()
        self.end_mill_height_input_line.editingFinished.connect(self.calculate_func)
        self.end_mill_height_input_line.editingFinished.connect(lambda: self.update_value(self.end_mill_height_input_line, "end_mill_height"))

        self.x_offset_input_line = QLineEdit()
        self.x_offset_input_line.editingFinished.connect(self.calculate_func)
        self.x_offset_input_line.editingFinished.connect(lambda: self.update_value(self.x_offset_input_line, "x_offset_input"))

        self.y_offset_input_line = QLineEdit()
        self.y_offset_input_line.editingFinished.connect(self.calculate_func)
        self.y_offset_input_line.editingFinished.connect(lambda: self.update_value(self.y_offset_input_line, "y_offset_input"))

        self.coord1_line = QLineEdit()
        self.coord1_line.setStyleSheet("color: red;")
        self.coord1_line.editingFinished.connect(self.calculate_func)
        self.coord1_line.editingFinished.connect(lambda: self.update_coord(1 , self.coord1_line.text()))
        self.coord1_line.editingFinished.connect(self.update_image)

        self.coord2_line = QLineEdit()
        self.coord2_line.setStyleSheet("color: blue;")
        self.coord2_line.editingFinished.connect(self.calculate_func)
        self.coord2_line.editingFinished.connect(lambda: self.update_coord(2, self.coord2_line.text()))
        self.coord2_line.editingFinished.connect(self.update_image)

        self.xy_distance_line = QLineEdit()
        self.xy_distance_line.setReadOnly(True)

        self.pix2mm_line = QLineEdit()
        self.pix2mm_line.setReadOnly(True)

        # create the coordinate button and connect them
        self.select_coord1_button = QPushButton("Select Coordinate 1")
        self.select_coord2_button = QPushButton("Select Coordinate 2")

        self.select_coord1_button.clicked.connect(self.activate_coord1_select)
        self.select_coord2_button.clicked.connect(self.activate_coord2_select)

        # create the save button
        self.save_button = QPushButton("Save Calibration")
        self.save_button.clicked.connect(self.save_calibration_file)

        # create the subtitles
        input_subtitle = QLabel("Inputs")
        input_subtitle.setStyleSheet("font-weight: bold; font-size: 16px;")
        output_subtitle = QLabel("Outputs")
        output_subtitle.setStyleSheet("font-weight: bold; font-size: 16px;")

        # create a spacer
        spacer = QSpacerItem(80, 80,
                            QSizePolicy.Policy.Expanding,
                            QSizePolicy.Policy.Minimum)

        # create the layout
        layout = QHBoxLayout()
        layout.addWidget(self.capture)

        layout_inputs = QFormLayout()
        layout_inputs.addRow(input_subtitle)
        layout_inputs.addRow("Microscope Height:", self.microscope_height_input_line)
        layout_inputs.addRow("End Mill Height:", self.end_mill_height_input_line)
        layout_inputs.addRow("Millimeter Length:", self.mm_length_input_line)
        layout_inputs.addRow(self.select_coord1_button)
        layout_inputs.addRow("Coordinate 1:", self.coord1_line)
        layout_inputs.addRow(self.select_coord2_button)
        layout_inputs.addRow("Coordinate 2:", self.coord2_line)
        layout_inputs.addRow("X Offset:", self.x_offset_input_line)
        layout_inputs.addRow("Y Offset:", self.y_offset_input_line)

        layout_calc = QFormLayout()
        layout_calc.addRow(output_subtitle)
        layout_calc.addRow("XY distance:", self.xy_distance_line)
        layout_calc.addRow("pixels per mm:", self.pix2mm_line)

        layout_saving = QVBoxLayout()
        layout_saving.addWidget(self.save_button)

        layout_right = QVBoxLayout()
        layout_right.addLayout(layout_inputs)
        layout_right.addSpacerItem(spacer)
        layout_right.addLayout(layout_calc)
        layout_right.addSpacerItem(spacer)
        layout_right.addLayout(layout_saving)

        layout.addLayout(layout_right)
        self.setLayout(layout)

    def update_coord(self, coord_number, new_coord):

        def is_list_of_two(inp):
            return isinstance(inp, (list, tuple)) and len(inp) == 2

        try:
            new_coord = list(ast.literal_eval(new_coord))
        except:
            QMessageBox.critical(self, "Error", "Coordinate not in proper format. Please write it as: (X,Y)")
            return

        if coord_number == 1 and is_list_of_two(new_coord):
            self.coord1 = new_coord
            self.update_image()
            self.calculate_func()
        elif coord_number == 2 and is_list_of_two(new_coord):
            self.coord2 = new_coord
            self.update_image()
            self.calculate_func()
        else:
            QMessageBox.critical(self, "Error", "Coordinate not in proper format. Please write it as: (X,Y)")
            return

    def update_value(self, line_edit, attr_name):
        text = line_edit.text()
        try:
            value = float(text)
            setattr(self, attr_name, value)
            print(f"{attr_name} set to {value}")
        except ValueError:
            QMessageBox.critical(self, "Error", "Invalid format. Please input a number")

    def calculate_func(self):
        if (self.coord1 and self.coord2) != None:
            self.xy_distance = math.dist(self.coord1, self.coord2)
            self.xy_distance_line.setText(str(round(self.xy_distance,2)))
        else:
            self.pix2mm_line.setText("-")
            self.xy_distance_line.setText("-")
            return

        try:
            self.px2mm = self.xy_distance / float(self.mm_length_input_line.text())
            self.pix2mm_line.setText(str(round(self.px2mm,2)))
        except:
            self.pix2mm_line.setText("-")
            return


    def activate_coord1_select(self):
        self.active_point = 1
        self.select_coord1_button.setText("CLICK ON IMAGE")

    def activate_coord2_select(self):
        self.active_point = 2
        self.select_coord2_button.setText("CLICK ON IMAGE")

    def get_px_coords(self, event):
        if self.active_point is None:
            return

        # retrieve the coords
        pos = event.position()
        x = float(pos.x())
        y = float(pos.y())

        # assign the coords accordingly
        if self.active_point == 1:
            self.coord1 = [x,y]
            self.coord1_line.setText(f"({round(self.coord1[0],2)},{round(self.coord1[1],2)})")
            self.select_coord1_button.setText("Select Coordinate 1")
            self.update_image()
            self.calculate_func()
        elif self.active_point == 2:
            self.coord2 = [x, y]
            self.coord2_line.setText(f"({round(self.coord2[0], 2)},{round(self.coord2[1], 2)})")
            self.select_coord2_button.setText("Select Coordinate 2")
            self.update_image()
            self.calculate_func()

        # reset active points
        self.active_point = None

    def update_image(self):
        pixmap = self.capture_pm.copy()
        painter = QPainter(pixmap)

        radius = 6

        if self.coord1:
            pen = QPen(Qt.GlobalColor.red)
            pen.setWidth(3)
            painter.setPen(pen)

            painter.drawEllipse(int(self.coord1[0]) - radius,
                                 int(self.coord1[1]) - radius,
                                 radius * 2,
                                 radius * 2)

        if self.coord2:
            pen = QPen(Qt.GlobalColor.blue)
            pen.setWidth(3)
            painter.setPen(pen)

            painter.drawEllipse(int(self.coord2[0]) - radius,
                                 int(self.coord2[1]) - radius,
                                 radius * 2,
                                 radius * 2)

        painter.end()

        self.capture.setPixmap(pixmap)

    def save_calibration_file(self):

        if any(v is None for v in (self.px2mm, self.x_offset_input, self.y_offset_input,
                                   self.end_mill_height, self.microscope_height)):
            QMessageBox.warning(
                self,
                "Missing Data",
                "Not all variables are filled in!"
            )
            return

        # Open directory selection dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save JSON File",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return  # User cancelled

        # Ensure file ends with .json
        if not file_path.endswith(".json"):
            file_path += ".json"

        data = {
            "pixels_per_mm": self.px2mm,
            "camera_X_offset": self.x_offset_input,
            "camera_Y_offset": self.y_offset_input,
            "end_mill_gap": self.end_mill_height,
            "microscope_height": self.microscope_height
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

            QMessageBox.information(self, "Success", f"Saved to:\n{file_path}")
            self.close()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
