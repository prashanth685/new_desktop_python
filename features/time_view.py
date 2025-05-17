from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QMessageBox
from PyQt5.QtCore import Qt, QTimer
import pyqtgraph as pg
import numpy as np
from datetime import datetime, timedelta
from collections import deque
import logging
import re
import struct

class TimeViewFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.channel = channel
        self.mqtt_tag = channel
        self.model_name = model_name or "default_model"
        self.widget = QWidget()
        self.window_size = 1.0
        self.data_rate = 4096.0
        self.buffer_size = int(self.data_rate * self.window_size)
        self.time_view_buffer = deque(maxlen=self.buffer_size)
        self.time_view_timestamps = deque(maxlen=self.buffer_size)
        self.timer = QTimer(self.widget)
        self.timer.timeout.connect(self.update_time_view_plot)
        self.plot_widget = None
        self.plot = None
        self.last_data_time = None
        self.is_saving = False
        self.frame_index = 0
        self.filename_counter = self.get_next_filename_counter()
        self.save_start_time = None
        self.save_end_time = None
        self.save_timer = QTimer(self.widget)
        self.save_timer.timeout.connect(self.update_save_duration)
        self.initUI()
        if self.mqtt_tag:
            tag = self.db.tags_collection.find_one({
                "project_name": self.project_name,
                "model_name": self.model_name,
                "tag_name": self.mqtt_tag,
                "email": self.db.email
            })
            if tag:
                self.setup_time_view_plot()
                logging.info(f"Tag {self.mqtt_tag} found, plot setup initiated")
                self.parent.append_to_console(f"Tag {self.mqtt_tag} found, plot setup initiated")
            else:
                logging.error(f"Tag {self.mqtt_tag} not found in tagcreated collection")
                self.parent.append_to_console(f"Error: Tag {self.mqtt_tag} not found in tagcreated collection")
                self.setup_time_view_plot()  # Still setup plot for dummy data
                self.populate_dummy_data()
        else:
            logging.warning("No MQTT tag provided, initializing with dummy data")
            self.parent.append_to_console("No MQTT tag provided, initializing with dummy data")
            self.setup_time_view_plot()
            self.populate_dummy_data()

    def get_widget(self):
        return self.widget

    def get_next_filename_counter(self):
        try:
            filenames = self.db.get_distinct_filenames(self.project_name, self.model_name)
            max_counter = 0
            for filename in filenames:
                match = re.match(r"data(\d+)", filename)
                if match:
                    counter = int(match.group(1))
                    max_counter = max(max_counter, counter)
            counter = max_counter + 1
            logging.debug(f"Next filename counter: {counter}")
            return counter
        except Exception as e:
            logging.error(f"Error getting filename counter: {str(e)}")
            self.parent.append_to_console(f"Error getting filename counter: {str(e)}")
            return 1

    def initUI(self):
        main_layout = QVBoxLayout()
        self.widget.setLayout(main_layout)

        control_widget = QWidget()
        control_layout = QVBoxLayout()
        control_widget.setLayout(control_layout)
        control_widget.setStyleSheet("background-color: #2c3e50; border-radius: 5px; padding: 10px 20px;")

        channel_display = self.channel if self.channel else "No Channel Selected"
        self.header = QLabel(f"TIME VIEW FOR {self.project_name.upper()} - Channel: {channel_display}")
        self.header.setStyleSheet("color: white; font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        control_layout.addWidget(self.header, alignment=Qt.AlignCenter)

        control_layout.setSpacing(15)
        control_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(control_widget)

        self.graph_widget = QWidget()
        self.graph_layout = QVBoxLayout()
        self.graph_widget.setLayout(self.graph_layout)
        self.graph_widget.setStyleSheet("background-color: #2c3e50; border: 1px solid #ffffff; border-radius: 5px; padding: 8px;")

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.graph_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #2c3e50;
                border-radius: 5px;
            }
            QScrollBar:vertical {
                background: #ffffff;
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #000000;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        scroll_area.setMinimumHeight(300)
        main_layout.addWidget(scroll_area)

    def update_save_duration(self):
        if self.save_start_time:
            duration = datetime.now() - self.save_start_time
            seconds = duration.total_seconds()
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            seconds = int(seconds % 60)
            self.header.setText(
                f"TIME VIEW FOR {self.project_name.upper()} - Channel: {self.channel} (Saving: {hours:02d}:{minutes:02d}:{seconds:02d})"
            )

    def refresh_filenames(self):
        filenames = self.db.get_distinct_filenames(self.project_name, self.model_name)
        return filenames

    def open_data_table(self, selected_filename):
        if "(Next)" in selected_filename:
            return
        if not self.db.timeview_collection.find_one({"filename": selected_filename, "project_name": self.project_name, "model_name": self.model_name}):
            return

    def on_delete(self, deleted_filename):
        self.filename_counter = self.get_next_filename_counter()
        if hasattr(self.parent, 'sub_toolbar'):
            self.parent.sub_toolbar.refresh_filenames()

    def start_saving(self):
        if not self.mqtt_tag:
            self.parent.append_to_console("Error: No valid channel selected!")
            QMessageBox.warning(self.widget, "Error", "No valid channel selected!")
            return

        tag = self.db.tags_collection.find_one({
            "project_name": self.project_name,
            "model_name": self.model_name,
            "tag_name": self.mqtt_tag,
            "email": self.db.email
        })
        if not tag:
            self.parent.append_to_console(f"Error: Tag {self.mqtt_tag} not found in tagcreated collection")
            QMessageBox.warning(self.widget, "Error", f"Tag {self.mqtt_tag} not found in tagcreated collection")
            return

        filename = f"data{self.filename_counter}"
        self.is_saving = True
        self.frame_index = 0
        self.save_start_time = datetime.now()
        self.save_timer.start(1000)
        self.parent.is_saving = True
        logging.info(f"Started saving data for {self.mqtt_tag} with filename {filename}")
        self.parent.append_to_console(f"Started saving data for {self.mqtt_tag} with filename {filename}")
        if hasattr(self.parent, 'sub_toolbar'):
            self.parent.sub_toolbar.update_subtoolbar()

    def stop_saving(self):
        if not self.is_saving:
            return

        self.is_saving = False
        self.save_timer.stop()
        self.save_end_time = datetime.now()
        self.parent.is_saving = False
        self.filename_counter += 1
        logging.info(f"Stopped saving data for {self.mqtt_tag}")
        self.parent.append_to_console(f"Stopped saving data for {self.mqtt_tag}")
        self.save_start_time = None
        self.header.setText(f"TIME VIEW FOR {self.project_name.upper()} - Channel: {self.channel}")
        if hasattr(self.parent, 'sub_toolbar'):
            self.parent.sub_toolbar.refresh_filenames()
            self.parent.sub_toolbar.update_subtoolbar()

    def populate_dummy_data(self):
        self.time_view_buffer.clear()
        self.time_view_timestamps.clear()
        num_samples = self.buffer_size
        start_time = datetime.now() - timedelta(seconds=self.window_size)
        for i in range(num_samples):
            sample_value = 32768 + 10000 * np.sin(2 * np.pi * i / num_samples)
            self.time_view_buffer.append(sample_value)
            sample_time = start_time + timedelta(seconds=i * self.window_size / num_samples)
            self.time_view_timestamps.append(sample_time)
        logging.info("Populated dummy data for testing")
        self.parent.append_to_console("Populated dummy data for testing")

    def setup_time_view_plot(self):
        self.timer.stop()
        self.time_view_buffer.clear()
        self.time_view_timestamps.clear()
        self.last_data_time = None
        self.is_saving = False
        self.save_timer.stop()
        self.frame_index = 0
        self.parent.is_saving = False
        self.initialize_plot()
        self.timer.start(66)
        logging.info(f"Initialized plot for channel {self.mqtt_tag}, buffer size: {self.buffer_size}")
        self.parent.append_to_console(f"Initialized plot for channel {self.mqtt_tag}")

    def initialize_plot(self):
        if self.plot_widget:
            self.graph_layout.removeWidget(self.plot_widget)
            self.plot_widget.setParent(None)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.7)
        self.plot_widget.setXRange(0, self.window_size)
        self.plot_widget.setYRange(16390, 46537)
        self.plot_widget.setLabel('bottom', 'Time (s)')
        self.plot_widget.setLabel('right', f'Channel: {self.channel or "Unknown"}')
        self.plot_widget.getAxis('right').setStyle(tickTextOffset=10)
        self.plot_widget.getAxis('left').setStyle(showValues=False)
        self.plot = self.plot_widget.plot(pen=pg.mkPen(color='b', width=1.5))
        self.graph_layout.addWidget(self.plot_widget)

        self.buffer_size = int(self.data_rate * self.window_size)
        self.time_view_buffer = deque(maxlen=self.buffer_size)
        self.time_view_timestamps = deque(maxlen=self.buffer_size)

        self.plot_widget.setMinimumSize(1000, 300)
        self.plot_widget.setVisible(True)
        logging.info(f"Initialized plot widget for channel {self.mqtt_tag}")
        self.parent.append_to_console(f"Initialized plot widget for channel {self.mqtt_tag}")

    def split_and_store_values(self, payload, timestamp):
        try:
            logging.debug(f"Received payload size: {len(payload)} bytes")
            self.parent.append_to_console(f"Received payload size: {len(payload)} bytes")

            if len(payload) < 20:
                logging.warning(f"Insufficient data: received {len(payload)} bytes")
                self.parent.append_to_console(f"Insufficient data: received {len(payload)} bytes")
                return

            if len(payload) % 2 != 0:
                logging.warning("Payload size is not a multiple of 2, cannot unpack as uint16_t")
                self.parent.append_to_console("Payload size is not a multiple of 2")
                return

            values = list(struct.unpack(f"{len(payload) // 2}H", payload))
            logging.debug(f"First 10 values: {values[:10]}")

            if len(values) < 10:
                logging.warning(f"Insufficient values: unpacked {len(values)} values")
                self.parent.append_to_console(f"Insufficient values: unpacked {len(values)} values")
                return

            number_of_channels = values[2]
            sampling_rate = values[3]
            plot_values = values[10:]
            logging.debug(f"Number of channels: {number_of_channels}, Sampling rate: {sampling_rate}, Plot values length: {len(plot_values)}")

            if len(plot_values) < number_of_channels:
                logging.warning(f"Unexpected number of plot values: {len(plot_values)}")
                self.parent.append_to_console(f"Unexpected number of plot values: {len(plot_values)}")
                return

            num_samples = len(plot_values) // number_of_channels
            if num_samples == 0:
                logging.warning("No samples to process after dividing plot values")
                self.parent.append_to_console("No samples to process")
                return

            if self.buffer_size != num_samples:
                self.buffer_size = num_samples
                self.time_view_buffer = deque(maxlen=self.buffer_size)
                self.time_view_timestamps = deque(maxlen=self.buffer_size)
                logging.info(f"Adjusted buffer size to {self.buffer_size}")
                self.parent.append_to_console(f"Adjusted buffer size to {self.buffer_size}")

            current_time = datetime.now()
            start_time = current_time - timedelta(seconds=self.window_size)
            time_step = self.window_size / (num_samples - 1) if num_samples > 1 else self.window_size

            for i in range(0, len(plot_values), number_of_channels):
                try:
                    sample_value = float(plot_values[i])
                    if np.isfinite(sample_value):
                        self.time_view_buffer.append(sample_value)
                        sample_time = start_time + timedelta(seconds=(i // number_of_channels) * time_step)
                        self.time_view_timestamps.append(sample_time)
                        logging.debug(f"Appended sample: {sample_value} at time {sample_time}")
                    else:
                        logging.warning(f"Invalid sample value at index {i}: {sample_value}")
                except (ValueError, TypeError) as e:
                    logging.warning(f"Invalid sample at index {i}: {e}")
                    self.parent.append_to_console(f"Warning: Invalid sample data at index {i}")
                    continue

            if self.time_view_buffer:
                logging.info(f"Buffer updated with {len(self.time_view_buffer)} samples")
                self.parent.append_to_console(f"Buffer updated with {len(self.time_view_buffer)} samples")

            if self.is_saving:
                filename = f"data{self.filename_counter}"
                message_data = {
                    "project_name": self.project_name,
                    "model_name": self.model_name,
                    "topic": self.mqtt_tag,
                    "filename": filename,
                    "frameIndex": values[0] + (values[1] * 65535),
                    "numberOfChannels": 1,
                    "samplingRate": sampling_rate,
                    "samplingSize": values[4],
                    "messageFrequency": values[5],
                    "slot6": str(values[6]),
                    "slot7": str(values[7]),
                    "slot8": str(values[8]),
                    "slot9": str(values[9]),
                    "message": [plot_values[i] for i in range(0, len(plot_values), number_of_channels)],
                    "createdAt": timestamp
                }
                success, msg = self.db.save_timeview_message(self.project_name, self.model_name, message_data)
                if success:
                    self.frame_index += 1
                    self.parent.append_to_console(f"Saved frame {self.frame_index - 1} to {filename}")
                else:
                    logging.error(f"Failed to save data: {msg}")
                    self.parent.append_to_console(f"Failed to save data: {msg}")
                    self.is_saving = False
                    self.save_timer.stop()
                    self.save_start_time = None
                    if hasattr(self.parent, 'sub_toolbar'):
                        self.parent.sub_toolbar.update_subtoolbar()

        except struct.error as e:
            logging.error(f"Failed to unpack payload: {str(e)}")
            self.parent.append_to_console(f"Failed to unpack payload: {str(e)}")
        except Exception as e:
            logging.error(f"Error processing values: {e}")
            self.parent.append_to_console(f"Error processing values: {e}")

    def adjust_buffer_size(self):
        new_buffer_size = int(self.data_rate * self.window_size)
        if new_buffer_size != self.buffer_size:
            self.buffer_size = new_buffer_size
            self.time_view_buffer = deque(self.time_view_buffer, maxlen=self.buffer_size)
            self.time_view_timestamps = deque(self.time_view_timestamps, maxlen=self.buffer_size)
            logging.info(f"Adjusted buffer size to {self.buffer_size}")
            self.parent.append_to_console(f"Adjusted buffer size to {self.buffer_size}")
            if self.plot_widget:
                self.plot_widget.setXRange(0, self.window_size)

    def generate_y_ticks(self, values):
        if not values or not all(np.isfinite(v) for v in values):
            return np.arange(16390, 46537, 5000)
        y_max = max(values)
        y_min = min(values)
        padding = (y_max - y_min) * 0.1 if y_max != y_min else 1000
        y_max += padding
        y_min -= padding
        step = (y_max - y_min) / 10
        step = np.ceil(step / 500) * 500
        ticks = np.arange(np.floor(y_min / step) * step, y_max + step, step)
        return ticks

    def update_time_view_plot(self):
        if not self.project_name or not self.plot or not self.plot_widget:
            logging.debug("Skipping plot update: missing project, plot, or plot widget")
            self.parent.append_to_console("Skipping plot update: missing project or plot")
            return

        window_values = list(self.time_view_buffer)
        window_timestamps = list(self.time_view_timestamps)

        logging.debug(f"Updating plot with {len(window_values)} values")

        if not window_values or not all(np.isfinite(v) for v in window_values):
            logging.debug("No valid data, using dummy data or clearing plot")
            if not window_values:
                self.populate_dummy_data()
                window_values = list(self.time_view_buffer)
                window_timestamps = list(self.time_view_timestamps)
            else:
                self.plot.setData([], [])
                self.plot_widget.setYRange(16390, 46537)
                self.plot_widget.getAxis('right').setTicks([[(v, str(int(v))) for v in np.arange(16390, 46537, 5000)]])
                return

        self.adjust_buffer_size()

        time_points = np.linspace(0, self.window_size, len(window_values))
        self.plot.setData(time_points, window_values)
        y_ticks = self.generate_y_ticks(window_values)
        y_min = min(window_values) - 1000
        y_max = max(window_values) + 1000
        self.plot_widget.setYRange(y_min, y_max)
        self.plot_widget.getAxis('right').setTicks([[(v, str(int(v))) for v in y_ticks]])

        if window_timestamps:
            try:
                start_time = window_timestamps[0]
                end_time = window_timestamps[-1]
                if isinstance(start_time, datetime) and isinstance(end_time, datetime):
                    duration = (end_time - start_time).total_seconds()
                    if duration == 0:
                        duration = self.window_size
                    tick_positions = np.linspace(0, self.window_size, 11)
                    time_labels = [
                        (start_time + timedelta(seconds=pos * duration / self.window_size)).strftime('%H:%M:%S.%f')[:-3]
                        for pos in tick_positions
                    ]
                    axis = self.plot_widget.getAxis('bottom')
                    axis.setTicks([[(pos, label) for pos, label in zip(tick_positions, time_labels)]])
            except Exception as e:
                logging.error(f"Error setting x-ticks: {e}")
                self.parent.append_to_console(f"Error setting x-ticks: {str(e)}")

        self.plot_widget.repaint()
        logging.debug("Plot updated")

    def on_data_received(self, tag_name, model_name, payload):
        if tag_name != self.mqtt_tag or model_name != self.model_name:
            logging.debug(f"Ignoring data for tag {tag_name}, model {model_name}")
            return

        logging.info(f"Data received for {tag_name}: {len(payload)} bytes")
        self.parent.append_to_console(f"Data received for {tag_name}: {len(payload)} bytes")
        current_time = datetime.now().isoformat()
        self.split_and_store_values(payload, current_time)

    def cleanup(self):
        if self.is_saving:
            self.stop_saving()
        self.timer.stop()
        self.save_timer.stop()
        self.plot = None
        if self.plot_widget:
            self.graph_layout.removeWidget(self.plot_widget)
            self.plot_widget.setParent(None)
        self.time_view_buffer.clear()
        self.time_view_timestamps.clear()
        logging.info(f"Cleaned up TimeViewFeature for channel {self.mqtt_tag}")