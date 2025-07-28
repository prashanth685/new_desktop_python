from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QSpinBox, QPushButton, QMessageBox
from PyQt5.QtCore import Qt, pyqtSignal
import logging
import datetime

class RangeDialog(QDialog):
    features_selected = pyqtSignal(str, str)

    def __init__(self, parent, db, project_name, model_name, filename):
        super().__init__(parent)
        self.db = db
        self.project_name = project_name
        self.model_name = model_name
        self.filename = filename
        self.setWindowTitle("Select Frame Range")
        self.setFixedSize(400, 300)
        self.initUI()
        self.load_file_info()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        self.filename_label = QLabel(f"File: {self.filename}")
        self.filename_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(self.filename_label)

        self.start_time_label = QLabel("Start Time: Loading...")
        self.start_time_label.setStyleSheet("font-size: 14px; color: #333;")
        layout.addWidget(self.start_time_label)

        self.end_time_label = QLabel("End Time: Loading...")
        self.end_time_label.setStyleSheet("font-size: 14px; color: #333;")
        layout.addWidget(self.end_time_label)

        self.start_frame_label = QLabel("Start Frame Index:")
        self.start_frame_label.setStyleSheet("font-size: 14px; color: #333;")
        layout.addWidget(self.start_frame_label)

        self.start_frame_spin = QSpinBox()
        self.start_frame_spin.setRange(0, 0)
        self.start_frame_spin.setStyleSheet("""
            QSpinBox {
                font-size: 14px;
                padding: 5px;
                border: 1px solid #90caf9;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.start_frame_spin)

        self.end_frame_label = QLabel("End Frame Index:")
        self.end_frame_label.setStyleSheet("font-size: 14px; color: #333;")
        layout.addWidget(self.end_frame_label)

        self.end_frame_spin = QSpinBox()
        self.end_frame_spin.setRange(0, 0)
        self.end_frame_spin.setStyleSheet("""
            QSpinBox {
                font-size: 14px;
                padding: 5px;
                border: 1px solid #90caf9;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.end_frame_spin)

        button_layout = QVBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #2c5d9b;
            }
        """)
        self.ok_button.clicked.connect(self.on_ok_clicked)
        button_layout.addWidget(self.ok_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #ef5350;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def load_file_info(self):
        try:
            if not self.db.is_connected():
                self.db.reconnect()
            messages = self.db.get_timeview_messages(self.project_name, self.model_name, filename=self.filename)
            if not messages:
                logging.warning(f"No messages found for file {self.filename} in project {self.project_name}/{self.model_name}")
                self.start_time_label.setText("Start Time: Not available")
                self.end_time_label.setText("End Time: Not available")
                self.start_frame_spin.setEnabled(False)
                self.end_frame_spin.setEnabled(False)
                self.ok_button.setEnabled(False)
                return

            frame_indices = [msg["frameIndex"] for msg in messages]
            timestamps = [msg["createdAt"] for msg in messages]
            if frame_indices and timestamps:
                min_frame = min(frame_indices)
                max_frame = max(frame_indices)
                min_time = min(timestamps)
                max_time = max(timestamps)
                try:
                    start_dt = datetime.datetime.fromisoformat(min_time.replace('Z', '+00:00'))
                    end_dt = datetime.datetime.fromisoformat(max_time.replace('Z', '+00:00'))
                    self.start_time_label.setText(f"Start Time: {start_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                    self.end_time_label.setText(f"End Time: {end_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                    self.start_frame_spin.setRange(min_frame, max_frame)
                    self.start_frame_spin.setValue(min_frame)
                    self.end_frame_spin.setRange(min_frame, max_frame)
                    self.end_frame_spin.setValue(max_frame)
                except ValueError as e:
                    logging.error(f"Error parsing timestamps: {e}")
                    self.start_time_label.setText("Start Time: Invalid format")
                    self.end_time_label.setText("End Time: Invalid format")
                    self.start_frame_spin.setEnabled(False)
                    self.end_frame_spin.setEnabled(False)
                    self.ok_button.setEnabled(False)
            else:
                self.start_time_label.setText("Start Time: Not available")
                self.end_time_label.setText("End Time: Not available")
                self.start_frame_spin.setEnabled(False)
                self.end_frame_spin.setEnabled(False)
                self.ok_button.setEnabled(False)
        except Exception as e:
            logging.error(f"Error loading file info for {self.filename}: {e}")
            self.start_time_label.setText("Start Time: Error")
            self.end_time_label.setText("End Time: Error")
            self.start_frame_spin.setEnabled(False)
            self.end_frame_spin.setEnabled(False)
            self.ok_button.setEnabled(False)

    def on_ok_clicked(self):
        start_frame = self.start_frame_spin.value()
        end_frame = self.end_frame_spin.value()
        if start_frame > end_frame:
            QMessageBox.warning(self, "Error", "Start frame index cannot be greater than end frame index!")
            return

        try:
            if not self.db.is_connected():
                self.db.reconnect()
            # Update feature instances to use the selected frame range
            for feature_name in [
                "Tabular View", "Time View", "Time Report", "FFT", "Waterfall",
                "Centerline", "Orbit", "Trend View", "Multiple Trend View",
                "Bode Plot", "History Plot", "Polar Plot", "Report"
            ]:
                self.features_selected.emit(feature_name, self.project_name)
            logging.info(f"Selected frame range {start_frame} to {end_frame} for file {self.filename}")
            self.accept()
        except Exception as e:
            logging.error(f"Error processing selected frame range: {e}")
            QMessageBox.warning(self, "Error", f"Failed to open features: {str(e)}")