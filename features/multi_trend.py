import struct
import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QScrollArea
from PyQt5.QtCore import QTimer
import pyqtgraph as pg
from datetime import datetime
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MultiTrendFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.channel = channel
        self.model_name = model_name
        self.console = console
        self.widget = None
        self.plot_widget = None
        self.plots = []
        self.channel_data = []
        self.channel_names = []
        self.channel_checkboxes = []
        self.colors = [
            (0, 0, 255),    # Blue
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green
            (128, 0, 128),  # Purple
            (255, 165, 0),  # Orange
            (0, 255, 255),  # Cyan
            (255, 0, 255),  # Magenta
            (165, 42, 42),  # Brown
            (0, 128, 128),  # Teal
            (255, 215, 0)   # Gold
        ]
        self.scaling_factor = 3.3 / 65535.0
        self.display_window_seconds = 60.0
        self.user_interacted = False
        self.last_right_limit = float('-inf')
        self.tag_name = None
        self.init_data()
        self.init_ui()

    def init_data(self):
        try:
            if not self.db.is_connected():
                self.db.reconnect()
            project_data = self.db.get_project_data(self.project_name)
            if not project_data or "models" not in project_data:
                self.log_error(f"Project {self.project_name} or models not found.")
                return
            model = next((m for m in project_data["models"] if m["name"] == self.model_name), None)
            if not model or not model.get("tagName"):
                self.log_error(f"TagName not found for Model: {self.model_name}")
                return
            self.tag_name = model["tagName"]
            self.log_info(f"Retrieved TagName: {self.tag_name} for Model: {self.model_name}")
            self.channel_names = [c["channelName"] for c in model.get("channels", [])]
            if not self.channel_names:
                self.log_error(f"No channels found in model {self.model_name}.")
                return
            self.channel_data = [{"direct_data": [], "timestamps": []} for _ in self.channel_names]
            self.log_info(f"Initialized {len(self.channel_names)} channels for Model: {self.model_name}")
        except Exception as e:
            self.log_error(f"Error initializing MultiTrendFeature: {str(e)}")

    def init_ui(self):
        self.widget = QWidget()
        main_layout = QVBoxLayout()
        self.widget.setLayout(main_layout)

        # Header
        header_label = QLabel(f"Multi Trend View for Model: {self.model_name}")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        main_layout.addWidget(header_label)

        # Channel selection
        channel_selection_widget = QWidget()
        channel_layout = QHBoxLayout()
        channel_selection_widget.setLayout(channel_layout)
        scroll_area = QScrollArea()
        scroll_area.setWidget(channel_selection_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(60)
        for i, ch_name in enumerate(self.channel_names):
            cb = QCheckBox(ch_name)
            cb.setChecked(True)
            cb.stateChanged.connect(lambda state, idx=i: self.toggle_channel(idx, state))
            cb.setStyleSheet(f"color: rgb{self.colors[i % len(self.colors)]};")
            self.channel_checkboxes.append(cb)
            channel_layout.addWidget(cb)
        channel_layout.addStretch()
        main_layout.addWidget(scroll_area)

        # Plot
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setLabel('bottom', 'Time')
        self.plot_widget.setLabel('left', 'Direct (Peak-to-Peak Voltage, V)')
        self.plot_widget.addLegend()
        self.plots = []
        for i, ch_name in enumerate(self.channel_names):
            plot = self.plot_widget.plot([], [], pen=pg.mkPen(color=self.colors[i % len(self.colors)], width=2),
                                         name=ch_name, symbol='o', symbolSize=5)
            self.plots.append(plot)
        main_layout.addWidget(self.plot_widget)

        # Handle user interaction
        self.plot_widget.scene().sigMouseClicked.connect(self.on_mouse_clicked)
        self.plot_widget.getViewBox().sigRangeChanged.connect(self.on_range_changed)

        # Error message
        self.error_label = QLabel("Waiting for data...")
        self.error_label.setStyleSheet("color: red; font-size: 14px; padding: 10px;")
        self.error_label.setAlignment(pg.QtCore.Qt.AlignCenter)
        main_layout.addWidget(self.error_label)
        self.error_label.setVisible(True)

        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_plot)
        self.update_timer.start(1000)  # Update every second

        if not self.model_name and self.console:
            self.console.append_to_console("No model selected in MultiTrendFeature.")
        self.log_info("Initialized MultiTrendFeature UI")

    def toggle_channel(self, index, state):
        self.plots[index].setVisible(state == pg.QtCore.Qt.Checked)
        self.plot_widget.getViewBox().update()
        self.update_plot()

    def on_mouse_clicked(self, event):
        self.user_interacted = True

    def on_range_changed(self, viewbox, range):
        self.user_interacted = True
        self.last_right_limit = range[0][1]

    def log_info(self, message):
        logging.info(message)
        if self.console:
            self.console.append_to_console(message)

    def log_error(self, message):
        logging.error(message)
        if self.console:
            self.console.append_to_console(message)
        self.error_label.setText(message)
        self.error_label.setVisible(True)

    def on_data_received(self, tag_name, model_name, values, sample_rate):
        if self.model_name != model_name or self.tag_name != tag_name:
            self.log_info(f"Ignoring data for tag: {tag_name}, model: {model_name}")
            return
        try:
            # Log received data structure
            self.log_info(f"Received data: {len(values)} channels, sample_rate: {sample_rate}, first channel length: {len(values[0]) if values else 0}")

            # Handle single-channel data (if channel_index is used)
            if not isinstance(values[0], (list, np.ndarray)):
                values = [values]  # Wrap single channel data in a list

            # Validate data
            expected_channels = len(self.channel_names)
            if len(values) < expected_channels:
                self.log_error(f"Invalid data: expected at least {expected_channels} channels, got {len(values)}")
                return

            # Extract main channels and tacho trigger (last channel, if available)
            main_data = values[:expected_channels]
            trigger_data = values[-1] if len(values) > expected_channels else []

            # Fallback trigger data if none provided
            if not trigger_data or len(trigger_data) < len(main_data[0]):
                # Generate synthetic triggers (every 100 samples)
                trigger_data = [1 if i % 100 == 0 else 0 for i in range(len(main_data[0]))]
                self.log_info("No valid trigger data; using synthetic triggers.")

            # Find trigger indices
            trigger_indices = [i for i, v in enumerate(trigger_data) if v >= 1.0]
            min_distance = 5
            filtered_triggers = [trigger_indices[0]] if trigger_indices else []
            for idx in trigger_indices[1:]:
                if idx - filtered_triggers[-1] >= min_distance:
                    filtered_triggers.append(idx)
            trigger_indices = filtered_triggers

            if len(trigger_indices) < 2:
                self.log_error("Not enough trigger points detected.")
                # Use synthetic triggers as fallback
                trigger_indices = list(range(0, len(main_data[0]), 100))
                if len(trigger_indices) < 2:
                    self.log_error("Synthetic triggers insufficient.")
                    return

            # Calibrate data
            calibrated_data = [[float(v) * self.scaling_factor for v in ch] for ch in main_data]

            # Calculate Direct (peak-to-peak) values
            current_time = datetime.now().timestamp() / 86400.0  # Convert to days since epoch
            for ch_idx, ch_data in enumerate(calibrated_data):
                direct_values = []
                for i in range(len(trigger_indices) - 1):
                    start_idx = trigger_indices[i]
                    end_idx = trigger_indices[i + 1]
                    if end_idx <= len(ch_data):
                        segment = ch_data[start_idx:end_idx]
                        if segment:
                            peak_to_peak = max(segment) - min(segment)
                            direct_values.append(peak_to_peak)
                direct_avg = np.mean(direct_values) if direct_values else 0.0
                self.channel_data[ch_idx]["direct_data"].append(direct_avg)
                self.channel_data[ch_idx]["timestamps"].append(current_time)
                # Limit data to last 1 hour
                if len(self.channel_data[ch_idx]["timestamps"]) > 3600:
                    self.channel_data[ch_idx]["timestamps"] = self.channel_data[ch_idx]["timestamps"][-3600:]
                    self.channel_data[ch_idx]["direct_data"] = self.channel_data[ch_idx]["direct_data"][-3600:]

            self.log_info(f"Processed data for {tag_name}: {len(self.channel_names)} channels at {datetime.now().strftime('%H:%M:%S')}")
            self.update_plot()
        except Exception as e:
            self.log_error(f"Error processing data: {str(e)}")

    def update_plot(self):
        try:
            has_data = any(data["timestamps"] for data in self.channel_data)
            self.error_label.setVisible(not has_data)

            current_time = datetime.now().timestamp() / 86400.0
            vb = self.plot_widget.getViewBox()

            # Update plots
            for i, (plot, data, cb) in enumerate(zip(self.plots, self.channel_data, self.channel_checkboxes)):
                if cb.isChecked() and data["timestamps"]:
                    x = np.array(data["timestamps"])
                    y = np.array(data["direct_data"])
                    plot.setData(x, y, connect="all")
                else:
                    plot.setData([], [])

            if not has_data:
                vb.setXRange(current_time - self.display_window_seconds / 86400.0, current_time, padding=0.05)
                vb.setYRange(-1, 1, padding=0.05)
                self.plot_widget.getPlotItem().autoRange()
                return

            max_time = max(max((d["timestamps"] or [0])[-1] for d in self.channel_data if d["timestamps"]), current_time)
            min_time = max_time - self.display_window_seconds / 86400.0

            if self.user_interacted:
                current_range = vb.viewRange()
                min_time = current_range[0][0]
                max_time = current_range[0][1]
                if abs(max_time - max(d["timestamps"][-1] for d in self.channel_data if d["timestamps"])) < 1.0 / 86400.0:
                    self.user_interacted = False
                    min_time = max_time - self.display_window_seconds / 86400.0
            else:
                if max(d["timestamps"][-1] for d in self.channel_data if d["timestamps"]) - min(d["timestamps"][0] for d in self.channel_data if d["timestamps"]) < self.display_window_seconds / 86400.0:
                    min_time = min(d["timestamps"][0] for d in self.channel_data if d["timestamps"])

            vb.setXRange(min_time, max_time, padding=0.05)

            if any(d["direct_data"] for d in self.channel_data):
                min_y = min(min(d["direct_data"] or [float('inf')]) for d in self.channel_data) * 0.9
                max_y = max(max(d["direct_data"] or [float('-inf')]) for d in self.channel_data) * 1.1
                vb.setYRange(min_y, max_y, padding=0.05)
            else:
                vb.setYRange(-1, 1, padding=0.05)

            self.plot_widget.getPlotItem().autoRange()
            self.log_info("Plot updated")
        except Exception as e:
            self.log_error(f"Error updating plot: {str(e)}")

    def get_widget(self):
        return self.widget

    def cleanup(self):
        self.update_timer.stop()
        self.channel_data.clear()
        self.plots.clear()
        self.channel_checkboxes.clear()
        self.log_info("Cleaned up MultiTrendFeature")