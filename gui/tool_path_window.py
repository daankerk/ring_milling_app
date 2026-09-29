import cv2
import numpy as np
from datetime import datetime
import json
import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QFrame, QHBoxLayout, QMessageBox, QInputDialog, \
    QDoubleSpinBox
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QPen
from core.g_code import coords_to_gcode
from core.read_config import save_dir, prev_points_dir

class ToolPathWindow(QWidget):
    def __init__(self, frame, x_offset, y_offset, mill_gap, save_flag, pix2mm):
        super().__init__()
        self.setWindowTitle("Tool Path Selection")

        # initialize the coords
        self.points = []  # list of (x, y) coordinates
        self.x_offset = x_offset    # this is the fixed x offset between drill and camera
        self.y_offset = y_offset    # this is the fixed y offset between drill and camera
        self.mill_gap = mill_gap
        self.first_point = None     # for the calibration
        self.save_flag = save_flag
        self.pix2mm = pix2mm
        self.drill_depth = 1    # standard is 1 mm

        # take the image
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        self.image_center_x = w//2
        self.image_center_y = h//2
        self.qt_image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

        # create the label image
        self.capture = QLabel()
        self.capture_pm = QPixmap.fromImage(self.qt_image)
        self.capture.setPixmap(self.capture_pm)
        self.capture.setFixedSize(w, h)
        self.capture.mousePressEvent = self.get_mouse_click

        # create a change drill depth spinbox
        self.depth_spin = QDoubleSpinBox()
        self.depth_spin.setRange(0.0, 15.0)
        self.depth_spin.setSingleStep(0.01)
        self.depth_spin.setDecimals(3)
        self.depth_spin.setValue(self.drill_depth)
        self.depth_spin.setSuffix(" mm")
        self.depth_spin.valueChanged.connect(self.spin_change)
        self.depth_spin_label = QLabel("Drilling depth:")

        # create a save button
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_points)

        # create a ctrl-z button
        self.back_button = QPushButton("Remove last point")
        self.back_button.clicked.connect(self.tp_back)

        # create a clear button
        self.clear_points_button = QPushButton("Clear Points")
        self.clear_points_button.clicked.connect(self.clear_points)

        # create a reload previous points button
        self.reload_button = QPushButton("Reload Points")
        self.reload_button.clicked.connect(self.load_prev_points)

        # place the camera image and the buttons
        layout = QHBoxLayout()
        layout.addWidget(self.capture)

        button_layout = QVBoxLayout()
        button_layout.addWidget(self.depth_spin_label)
        button_layout.addWidget(self.depth_spin)
        button_layout.addWidget(self.back_button)
        button_layout.addWidget(self.clear_points_button)
        button_layout.addWidget(self.reload_button)
        button_layout.addWidget(self.save_button)

        button_layout.addStretch()
        button_layout.setSpacing(20)

        button_widget = QFrame()
        button_widget.setFrameShape(QFrame.Shape.Box)
        button_widget.setFrameShadow(QFrame.Shadow.Raised)
        button_widget.setLayout(button_layout)

        layout.addWidget(button_widget)

        self.setLayout(layout)

    # function takes mouse clicks, converts the click to coords and draws a mark
    def get_mouse_click(self, event):
        x = event.position().x()
        y = event.position().y()

        # save the first points
        if self.first_point is None:
            self.first_point = (x,y)
            print(f"first points: {self.first_point}" )

        self.points.append((x, y))
        print(f"Point selected: ({x}, {y})")
        self.draw_points()

    def load_prev_points(self):
        # first give a warning since current points will be replaced
        reply = QMessageBox.question(self,
                                     "Warning!",
                                     "Are you sure you want to load the previous points? The current points will be deleted",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self.clear_points()
            if os.path.exists(prev_points_dir):
                with open(prev_points_dir, "r") as f:
                    self.points = json.load(f)# ADD HERE THAT THE FIRST POINTS ALSO CHANGES!
            else:
                QMessageBox.critical(self, "Error", "No Proper Directory For Previous Points\n\nCheck config.json")
            self.draw_points()
        else:
            return

    def draw_points(self):
        pixmap = QPixmap.fromImage(self.qt_image)   # convert the image into drawable pixmap
        painter = QPainter(pixmap)                  # make sure it is drawable

        painter.setRenderHint(QPainter.RenderHint.Antialiasing) # for smoother rendering of the shape

        pen = QPen(QColor(255, 0, 0))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        radius = 4
        cross_size = 7

        for x, y in self.points:
            cx = round(x)
            cy = round(y)

            # draw the circle
            painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

            # draw the lines through the circle
            painter.drawLine(cx - cross_size, cy, cx + cross_size, cy)
            painter.drawLine(cx, cy - cross_size, cx, cy + cross_size)

        painter.end()
        self.capture.setPixmap(pixmap)

    def save_points(self):

        if len(self.points) == 0:
            print("No points selected")
            QMessageBox.critical(self, "Error", "No Points Selected!")
            return

        # calculate the calibration offset
        self.first_point_offset_x = self.first_point[0] - self.image_center_x
        self.first_point_offset_y = -1*(self.first_point[1] - self.image_center_y)
        print(f"first point = {self.first_point}")
        print(f"center at x = {self.image_center_x}, y = {self.image_center_y}")
        print(f"cal_offset_x: {self.first_point_offset_x}")
        print(f"cal_offset_y: {self.first_point_offset_y}")

        # converting the points into G-code
        g_export_arr = np.array(self.points)
        self.g_export = coords_to_gcode(g_export_arr[:,0], g_export_arr[:,1], self.x_offset, self.y_offset, self.mill_gap,
                                        self.first_point_offset_x, self.first_point_offset_y, self.pix2mm, self.drill_depth)
        print(self.g_export)

        # write the g-code to a txt file
        text_file = open("/home/daan/Documents/thesis/engineering/coding/ring_milling_app/exports/g_export.txt", "w")
        text_file.write(self.g_export)
        text_file.close()

        # save according to the flag
        if (self.save_flag):
            now = datetime.now()
            fn = now.strftime(save_dir + "/coordinates_%Y-%m-%d_%H-%M-%S.txt")
            with open(fn, 'w') as file:
                file.write(self.g_export)

        # save the points as previous points
        with open(prev_points_dir, 'w') as file:
            json.dump(self.points, file)

        # close the window
        self.close()

    def tp_back(self):
        if not self.points:  # safety check
            return
        self.points.pop()  # remove last (x, y)
        self.draw_points()  # redraw image

    def clear_points(self):
            self.points.clear()
            self.draw_points()
            self.first_point = None

    def spin_change(self, value):
        self.drill_depth = value