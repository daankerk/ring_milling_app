from PyQt6.QtCore import QThread, pyqtSignal
import numpy as np
import cv2
from core.read_config import camera_index

class CameraThread(QThread):
    frame_ready = pyqtSignal(np.ndarray)

    def run(self):
        cap = cv2.VideoCapture(camera_index)
        while cap.isOpened() and not self.isInterruptionRequested():
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

            # delete later, this adds the plus
            # Get center of frame
            h, w = frame.shape[:2]
            center_x = w // 2
            center_y = h // 2

            # Size of the plus
            size = 20
            thickness = 2
            color = (0, 0, 255)  # Red in BGR

            # Draw horizontal line
            cv2.line(frame,
                     (center_x - size, center_y),
                     (center_x + size, center_y),
                     color, thickness)

            # Draw vertical line
            cv2.line(frame,
                     (center_x, center_y - size),
                     (center_x, center_y + size),
                     color, thickness)

            self.frame_ready.emit(frame)
        cap.release()