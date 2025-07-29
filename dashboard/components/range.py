from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QSlider
from PyQt5.QtCore import Qt, pyqtSignal
import logging
import datetime

class FrequencyWindow(QDialog):
    def __init__(self, parent=None, project_name=None, model_name=None, filename=None, start_time=None, end_time=None):
        super().__init__(parent)
        self.setWindowTitle("Frequency Window")
        self.setFixedSize(400, 300)
        self.project_name = project_name
        self.model_name = model_name
        self.filename = filename
        self.start_time = start_time
        self.end_time = end_time
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        title = QLabel(f"Frequency Analysis for {self.filename}")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(title)

        time_label = QLabel(f"Selected Range: {self.start_time} to {self.end_time}")
        time_label.setStyleSheet("font-size: 14px; color: #333;")
        layout.addWidget(time_label)

        frame_button = QPushButton("Open Frame Index Window")
        frame_button.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #357abd; }
            QPushButton:pressed { background-color: #2c5d9b; }
        """)
        frame_button.clicked.connect(self.open_frame_index_window)
        layout.addWidget(frame_button)

        layout.addStretch()
        self.setLayout(layout)

    def open_frame_index_window(self):
        frame_window = FrameIndexWindow(
            self, self.project_name, self.model_name, self.filename, self.start_time, self.end_time
        )
        frame_window.show()

class FrameIndexWindow(QDialog):
    def __init__(self, parent=None, project_name=None, model_name=None, filename=None, start_time=None, end_time=None):
        super().__init__(parent)
        self.setWindowTitle("Frame Index Window")
        self.setFixedSize(400, 300)
        self.project_name = project_name
        self.model_name = model_name
        self.filename = filename
        self.start_time = start_time
        self.end_time = end_time
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        title = QLabel(f"Frame Indices for {self.filename}")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(title)

        time_label = QLabel(f"Time Range: {self.start_time} to {self.end_time}")
        time_label.setStyleSheet("font-size: 14px; color: #333;")
        layout.addWidget(time_label)

        # Placeholder for frame index display
        frame_label = QLabel("Frame indices would be listed here")
        frame_label.setStyleSheet("font-size: 14px; color: #333;")
        layout.addWidget(frame_label)

        layout.addStretch()
        self.setLayout(layout)

class RangeDialog(QDialog):
    time_range_selected = pyqtSignal(str, str)

    def __init__(self, parent=None, project_name=None, model_name=None, filename=None, start_time=None, end_time=None):
        super().__init__(parent)
        self.setWindowTitle("Select Time Range")
        self.setFixedSize(500, 300)
        self.project_name = project_name
        self.model_name = model_name
        self.filename = filename
        self.start_time = start_time
        self.end_time = end_time
        self.start_timestamp = self.parse_time(start_time) if start_time else 0
        self.end_timestamp = self.parse_time(end_time) if end_time else 0
        self.initUI()

    def parse_time(self, time_str):
        try:
            return datetime.datetime.fromisoformat(time_str.replace('Z', '+00:00')).timestamp()
        except Exception as e:
            logging.error(f"Error parsing time {time_str}: {str(e)}")
            return 0

    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        title = QLabel(f"Select Time Range for {self.filename}")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(title)

        time_range_label = QLabel(f"Available Range: {self.start_time} to {self.end_time}")
        time_range_label.setStyleSheet("font-size: 14px; color: #333;")
        layout.addWidget(time_range_label)

        self.start_slider = QSlider(Qt.Horizontal)
        self.start_slider.setMinimum(0)
        self.start_slider.setMaximum(100)
        self.start_slider.setValue(0)
        self.start_slider.valueChanged.connect(self.update_labels)
        layout.addWidget(QLabel("Start Time:"))
        layout.addWidget(self.start_slider)

        self.end_slider = QSlider(Qt.Horizontal)
        self.end_slider.setMinimum(0)
        self.end_slider.setMaximum(100)
        self.end_slider.setValue(100)
        self.end_slider.valueChanged.connect(self.update_labels)
        layout.addWidget(QLabel("End Time:"))
        layout.addWidget(self.end_slider)

        self.start_label = QLabel("Start: " + self.start_time)
        self.start_label.setStyleSheet("font-size: 14px; color: #333;")
        layout.addWidget(self.start_label)

        self.end_label = QLabel("End: " + self.end_time)
        self.end_label.setStyleSheet("font-size: 14px; color: #333;")
        layout.addWidget(self.end_label)

        confirm_button = QPushButton("Confirm")
        confirm_button.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #357abd; }
            QPushButton:pressed { background-color: #2c5d9b; }
        """)
        confirm_button.clicked.connect(self.confirm_selection)
        layout.addWidget(confirm_button)

        layout.addStretch()
        self.setLayout(layout)

    def update_labels(self):
        total_duration = self.end_timestamp - self.start_timestamp
        start_value = self.start_slider.value() / 100.0
        end_value = self.end_slider.value() / 100.0
        start_ts = self.start_timestamp + (total_duration * start_value)
        end_ts = self.start_timestamp + (total_duration * end_value)
        start_time_str = datetime.datetime.fromtimestamp(start_ts).isoformat()
        end_time_str = datetime.datetime.fromtimestamp(end_ts).isoformat()
        self.start_label.setText(f"Start: {start_time_str}")
        self.end_label.setText(f"End: {end_time_str}")

    def confirm_selection(self):
        total_duration = self.end_timestamp - self.start_timestamp
        start_value = self.start_slider.value() / 100.0
        end_value = self.end_slider.value() / 100.0
        start_ts = self.start_timestamp + (total_duration * start_value)
        end_ts = self.start_timestamp + (total_duration * end_value)
        start_time_str = datetime.datetime.fromtimestamp(start_ts).isoformat()
        end_time_str = datetime.datetime.fromtimestamp(end_ts).isoformat()
        self.time_range_selected.emit(start_time_str, end_time_str)
        self.accept()