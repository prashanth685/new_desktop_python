import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout, QComboBox, 
                            QScrollArea, QPushButton, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
import pyqtgraph as pg
import numpy as np
from datetime import datetime, timedelta
from collections import deque
import logging
import re

class TimeViewFeature:
    def __init__(self, parent, db, project_name, channel=None):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.channel = channel
        self.mqtt_tag = channel  # Use channel as tag_name
        self.widget = QWidget()
        self.window_size = 1.0
        self.data_rate = 4096.0
        self.buffer_size = int(self.data_rate * self.window_size)
        self.time_view_buffer = deque(maxlen=self.buffer_size)  # Single buffer for one channel
        self.time_view_timestamps = deque(maxlen=self.buffer_size)
        self.timer = QTimer(self.widget)
        self.timer.timeout.connect(self.update_time_view_plot)
        self.plot_widget = None  # Single PlotWidget for the channel
        self.plot = None  # Single plot item
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
            self.setup_time_view_plot()

    def get_widget(self):
        return self.widget

    def get_next_filename_counter(self):
        try:
            filenames = self.db.get_distinct_filenames(self.project_name)
            max_counter = 0
            for filename in filenames:
                match = re.match(r"data(\d+)", filename)
                if match:
                    counter = int(match.group(1))
                    max_counter = max(max_counter, counter)
            counter = max_counter + 1
            logging.debug(f"Next filename counter for project {self.project_name}: {counter}")
            return counter
        except Exception as e:
            logging.error(f"Error getting next filename counter: {str(e)}")
            self.parent.append_to_console(f"Error getting next filename counter: {str(e)}")
            return 1  # Default to 1 if there's an error

    def initUI(self):
        main_layout = QVBoxLayout()
        self.widget.setLayout(main_layout)

        # Fixed control widget
        control_widget = QWidget()
        control_layout = QVBoxLayout()
        control_widget.setLayout(control_layout)
        control_widget.setStyleSheet("background-color: #2c3e50; border-radius: 5px; padding: 10px 20px;")

        # Header
        channel_display = self.channel if self.channel else "No Channel Selected"
        header = QLabel(f"TIME VIEW FOR {self.project_name.upper()} - Channel: {channel_display}")
        header.setStyleSheet("color: white; font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        self.header = header
        control_layout.addWidget(header, alignment=Qt.AlignCenter)

        control_layout.setSpacing(15)
        control_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(control_widget)

        # Graph area (no scroll needed for single plot)
        self.graph_widget = QWidget()
        self.graph_layout = QVBoxLayout()
        self.graph_widget.setLayout(self.graph_layout)
        self.graph_widget.setStyleSheet("background-color: #2c3e50; border: 1px solid #ffffff; border-radius: 5px; padding: 8px;")
        main_layout.addWidget(self.graph_widget, stretch=1)

    def update_save_duration(self):
        if self.save_start_time:
            duration = datetime.now() - self.save_start_time
            seconds = duration.total_seconds()
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            seconds = int(seconds % 60)
            # Removed timer_label update since it's no longer in the UI

    def refresh_filenames(self):
        # Method still needed for SubToolBar to call
        filenames = self.db.get_distinct_filenames(self.project_name)
        return filenames

    def open_data_table(self, selected_filename):
        if "(Next)" in selected_filename:
            return
        if not self.db.timeview_collection.find_one({"filename": selected_filename, "project_name": self.project_name}):
            return

    def on_delete(self, deleted_filename):
        self.filename_counter = self.get_next_filename_counter()
        # Notify SubToolBar to refresh filenames
        if hasattr(self.parent, 'sub_toolbar'):
            self.parent.sub_toolbar.refresh_filenames()

    def start_saving(self):
        if not self.mqtt_tag:
            self.parent.append_to_console("Error: No valid channel selected!")
            QMessageBox.warning(self.widget, "Error", "No valid channel selected!")
            return

        filename = f"data{self.filename_counter}"
        self.is_saving = True
        self.frame_index = 0
        self.save_start_time = datetime.now()
        self.save_timer.start(1000)
        self.parent.is_saving = True
        logging.info(f"Started saving data for {self.mqtt_tag} with filename {filename}")
        self.parent.append_to_console(f"Started saving data for {self.mqtt_tag} with filename {filename}")
        # Notify SubToolBar to update its UI
        if hasattr(self.parent, 'sub_toolbar'):
            self.parent.sub_toolbar.update_subtoolbar()

    def stop_saving(self):
        if not self.is_saving:
            return

        self.is_saving = False
        self.save_timer.stop()
        stop_time = datetime.now()
        self.save_end_time = stop_time
        self.parent.is_saving = False
        self.filename_counter += 1
        logging.info(f"Stopped saving data for {self.mqtt_tag}")
        self.parent.append_to_console(f"Stopped saving data for {self.mqtt_tag}")
        self.save_start_time = None
        # Notify SubToolBar to update its UI and filenames
        if hasattr(self.parent, 'sub_toolbar'):
            self.parent.sub_toolbar.refresh_filenames()
            self.parent.sub_toolbar.update_subtoolbar()

    def setup_time_view_plot(self):
        if not self.project_name or not self.mqtt_tag:
            logging.warning("No project or valid channel selected for Time View!")
            self.parent.append_to_console("No project or valid channel selected for Time View!")
            self.timer.stop()
            # Clear existing plot
            if self.plot_widget:
                self.graph_layout.removeWidget(self.plot_widget)
                self.plot_widget.setParent(None)
                self.plot_widget = None
                self.plot = None
            return

        self.timer.stop()
        self.timer.setInterval(100)
        self.time_view_buffer.clear()
        self.time_view_timestamps.clear()
        self.last_data_time = None
        self.is_saving = False
        self.save_timer.stop()
        self.frame_index = 0
        self.parent.is_saving = False

        # Initialize single plot
        self.initialize_plot()

        self.timer.start()
        logging.info(f"Initialized plot for channel {self.mqtt_tag}, buffer size: {self.buffer_size}")
        self.parent.append_to_console(f"Initialized plot for channel {self.mqtt_tag}")

    def initialize_plot(self):
        # Clear existing plot
        if self.plot_widget:
            self.graph_layout.removeWidget(self.plot_widget)
            self.plot_widget.setParent(None)

        # Create single PlotWidget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.7)
        self.plot_widget.setXRange(0, self.window_size)
        self.plot_widget.setYRange(0, 65535)
        self.plot_widget.setLabel('bottom', 'Time (s)')
        self.plot_widget.setLabel('right', f'Channel: {self.channel or "Unknown"}')
        self.plot_widget.getAxis('right').setStyle(tickTextOffset=10)
        self.plot_widget.getAxis('left').setStyle(showValues=False)
        self.plot = self.plot_widget.plot(pen=pg.mkPen(color='b', width=1.5))
        self.graph_layout.addWidget(self.plot_widget)

        self.buffer_size = int(self.data_rate * self.window_size)
        self.time_view_buffer = deque(maxlen=self.buffer_size)
        self.time_view_timestamps = deque(maxlen=self.buffer_size)

        self.graph_widget.setMinimumSize(1000, 300)
        logging.info(f"Initialized subplot for channel {self.mqtt_tag}")
        self.parent.append_to_console(f"Initialized subplot for channel {self.mqtt_tag}")

    def split_and_store_values(self, values, timestamp):
        try:
            if len(values) < 10:
                logging.warning(f"Insufficient data: received {len(values)} values, expected at least 10")
                self.parent.append_to_console(f"Insufficient data: received {len(values)} values")
                return

            frame_index = values[0] + (values[1] * 65535)
            number_of_channels = values[2]
            sampling_rate = values[3]
            sampling_size = values[4]
            message_frequency = values[5]
            slot6 = str(values[6])
            slot7 = str(values[7])
            slot8 = str(values[8])
            slot9 = str(values[9])

            plot_values = values[10:]
            if len(plot_values) < number_of_channels:
                logging.warning(f"Unexpected number of plot values: {len(plot_values)}. Expected at least {number_of_channels}")
                self.parent.append_to_console(f"Unexpected number of plot values: {len(plot_values)}")
                return

            # Assume first channel's data for simplicity (or adjust if channel index is known)
            num_samples = len(plot_values) // number_of_channels
            start_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00')) if 'Z' in timestamp else datetime.fromisoformat(timestamp)
            timestamps = [start_time + timedelta(seconds=i / self.data_rate) for i in range(num_samples)]

            for i in range(0, len(plot_values), number_of_channels):
                sample_idx = i // number_of_channels
                try:
                    sample_value = float(plot_values[i])  # Take first channel's value
                    self.time_view_buffer.append(sample_value)
                    self.time_view_timestamps.append(timestamps[sample_idx])
                except (ValueError, TypeError) as e:
                    logging.warning(f"Invalid sample at index {i}: {e}")
                    self.parent.append_to_console(f"Warning: Invalid sample data at index {i}")
                    continue

            if self.is_saving:
                filename = f"data{self.filename_counter}"
                message_data = {
                    "project_name": self.project_name,
                    "topic": self.mqtt_tag,
                    "filename": filename,
                    "frameIndex": frame_index,
                    "numberOfChannels": 1,  # Store as single channel
                    "samplingRate": sampling_rate,
                    "samplingSize": sampling_size,
                    "messageFrequency": message_frequency,
                    "slot6": slot6,
                    "slot7": slot7,
                    "slot8": slot8,
                    "slot9": slot9,
                    "message": [plot_values[i] for i in range(0, len(plot_values), number_of_channels)],  # Store first channel's values
                    "createdAt": timestamp
                }
                success, msg = self.db.save_timeview_message(self.project_name, "default_model", message_data)
                if success:
                    self.frame_index += 1
                    self.header.setText(f"TIME VIEW FOR {self.project_name.upper()} - Channel: {self.channel}")
                    logging.debug(f"Saved frame {self.frame_index - 1} for {self.mqtt_tag} to {filename}")
                    self.parent.append_to_console(f"Saved frame {self.frame_index - 1} to {filename}")
                else:
                    logging.error(f"Failed to save data: {msg}")
                    self.parent.append_to_console(f"Failed to save data: {msg}")
                    self.is_saving = False
                    self.save_timer.stop()
                    self.save_start_time = None
                    if hasattr(self.parent, 'sub_toolbar'):
                        self.parent.sub_toolbar.update_subtoolbar()

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
            return np.arange(0, 65536, 10000)
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
        if not self.project_name or not self.mqtt_tag or not self.plot or not self.time_view_buffer:
            return

        window_values = list(self.time_view_buffer)
        window_timestamps = list(self.time_view_timestamps)

        if not window_values or not all(np.isfinite(v) for v in window_values):
            self.plot.setData([], [])
            self.plot_widget.setYRange(0, 65535)
            self.plot_widget.getAxis('right').setTicks([[(v, str(int(v))) for v in np.arange(0, 65536, 10000)]])
            return

        self.adjust_buffer_size()

        time_points = np.linspace(0, self.window_size, len(window_values))
        self.plot.setData(time_points, window_values)
        y_ticks = self.generate_y_ticks(window_values)
        self.plot_widget.setYRange(min(window_values) - 1000, max(window_values) + 1000)
        self.plot_widget.getAxis('right').setTicks([[(v, str(int(v))) for v in y_ticks]])

        if window_timestamps:
            try:
                start_time = window_timestamps[0]
                end_time = window_timestamps[-1]
                if isinstance(start_time, datetime) and isinstance(end_time, datetime):
                    tick_positions = np.linspace(0, self.window_size, 11)
                    time_labels = [
                        (start_time + timedelta(seconds=pos)).strftime('%H:%M:%S.%f')[:-3]
                        for pos in tick_positions
                    ]
                    axis = self.plot_widget.getAxis('bottom')
                    axis.setTicks([[(pos, label) for pos, label in zip(tick_positions, time_labels)]])
            except Exception as e:
                logging.error(f"Error setting x-ticks: {e}")
                self.parent.append_to_console(f"Error setting x-ticks: {str(e)}")

    def on_data_received(self, tag_name, values):
        if tag_name != self.mqtt_tag:
            return

        current_time = datetime.now()
        timestamp = current_time.isoformat()
        self.split_and_store_values(values, timestamp)

    def cleanup(self):
        if self.is_saving:
            self.stop_saving()
        self.timer.stop()
        self.save_timer.stop()
        self.plot = None
        self.plot_widget = None
        self.time_view_buffer.clear()
        self.time_view_timestamps.clear()
        logging.info(f"Cleaned up TimeViewFeature for channel {self.mqtt_tag}")