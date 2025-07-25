import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QScrollArea, QPushButton, QCheckBox, QComboBox, QGridLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, QThread, QObject, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon
import pyqtgraph as pg
from datetime import datetime
from pymongo import MongoClient
import scipy.signal as signal
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class TabularViewSettings:
    def __init__(self, project_id):
        self.project_id = project_id
        self.bandpass_selection = "None"
        self.channel_name_visible = True
        self.unit_visible = True
        self.datetime_visible = True
        self.rpm_visible = True
        self.gap_visible = True
        self.direct_visible = True
        self.bandpass_visible = True
        self.one_xa_visible = True
        self.one_xp_visible = True
        self.two_xa_visible = True
        self.two_xp_visible = True
        self.nx_amp_visible = True
        self.nx_phase_visible = True
        self.updated_at = datetime.utcnow()

class TabularViewWorker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    initialized = pyqtSignal(list, int, str, dict, str)

    def __init__(self, parent, project_name, model_name, channel, db):
        super().__init__()
        self.parent = parent
        self.project_name = project_name
        self.model_name = model_name
        self.channel = channel
        self.db = db
        self.mongo_client = MongoClient("mongodb://localhost:27017")

    def run(self):
        try:
            database = self.mongo_client.get_database("changed_db")
            projects_collection = database.get_collection("projects")
            project = projects_collection.find_one({"project_name": self.project_name, "email": self.db.email})
            if not project:
                self.error.emit(f"Project {self.project_name} not found for email {self.db.email}.")
                self.initialized.emit(["Channel 1"], 1, "", {}, None)
                return

            project_id = project["_id"]
            model = next((m for m in project["models"] if m["name"] == self.model_name), None)
            if not model or not model.get("channels"):
                self.error.emit(f"Model {self.model_name} or channels not found in project {self.project_name}.")
                self.initialized.emit(["Channel 1"], 1, "", {}, None)
                return

            channel_names = [c.get("channelName", f"Channel {i+1}") for i, c in enumerate(model["channels"])]
            num_channels = len(channel_names)
            if not channel_names:
                self.error.emit("No channels found in model.")
                self.initialized.emit(["Channel 1"], 1, "", {}, None)
                return

            channel_properties = {}
            for channel in model["channels"]:
                channel_name = channel.get("channelName", "Unknown")
                correction_value = float(channel.get("CorrectionValue", "1.0")) if channel.get("CorrectionValue") else 1.0
                gain = float(channel.get("Gain", "1.0")) if channel.get("Gain") else 1.0
                sensitivity = float(channel.get("Sensitivity", "1.0")) if channel.get("Sensitivity") and float(channel.get("Sensitivity")) != 0 else 1.0
                channel_properties[channel_name] = {
                    "Unit": channel.get("Unit", "mil").lower(),
                    "CorrectionValue": correction_value,
                    "Gain": gain,
                    "Sensitivity": sensitivity
                }

            tag_name = model.get("tagName", "")
            self.initialized.emit(channel_names, num_channels, tag_name, channel_properties, project_id)
        except Exception as ex:
            self.error.emit(f"Error initializing TabularView: {str(ex)}")
            self.initialized.emit(["Channel 1"], 1, "", {}, None)
        finally:
            self.mongo_client.close()
            self.finished.emit()

class TabularViewFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.channel = channel
        self.model_name = model_name
        self.console = console
        self.widget = None
        self.data = None
        self.sample_rate = 4096
        self.num_channels = 1
        self.channel_names = ["Channel 1"]
        self.channel_properties = {}
        self.project_id = None
        self.raw_data = [np.zeros(4096)]
        self.low_pass_data = [np.zeros(4096)]
        self.high_pass_data = [np.zeros(4096)]
        self.band_pass_data = [np.zeros(4096)]
        self.time_points = np.arange(4096) / self.sample_rate
        self.band_pass_peak_to_peak_history = [[]]
        self.band_pass_peak_to_peak_times = [[]]
        self.average_frequency = [0.0]
        self.band_pass_peak_to_peak = [0.0]
        self.start_time = datetime.now()
        self.column_visibility = {
            "Channel Name": True, "Unit": True, "DateTime": True, "RPM": True, "Gap": True,
            "Direct": True, "Bandpass": True, "1xA": True, "1xP": True, "2xA": True,
            "2xP": True, "NXAmp": True, "NXPhase": True
        }
        self.bandpass_selection = "None"
        self.plot_initialized = False
        self.table = None
        self.plot_widgets = []
        self.plots = []
        self.selected_channel_idx = 0
        self.tag_name = ""
        self.channel_selector = None
        self.scroll_content = None
        self.scroll_layout = None
        self.mongo_client = MongoClient("mongodb://localhost:27017")
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(1000)  # Update every second
        self.initUI()
        self.initialize_thread()

    def initUI(self):
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        self.widget = QWidget()
        layout = QVBoxLayout()
        self.widget.setLayout(layout)

        top_layout = QHBoxLayout()
        self.settings_button = QPushButton("Settings")
        self.settings_button.setIcon(QIcon("settings_icon.png"))
        self.settings_button.clicked.connect(self.toggle_settings)
        top_layout.addWidget(self.settings_button)

        top_layout.addWidget(QLabel("Select Channel for Plots:"))
        self.channel_selector = QComboBox()
        self.channel_selector.addItem("Select Channel")
        self.channel_selector.addItems(self.channel_names)
        self.channel_selector.currentIndexChanged.connect(self.update_selected_channel)
        top_layout.addWidget(self.channel_selector)
        top_layout.addStretch()
        layout.addLayout(top_layout)

        self.settings_panel = QWidget()
        self.settings_panel.setVisible(False)
        settings_layout = QGridLayout()
        self.settings_panel.setLayout(settings_layout)

        self.bandpass_combo = QComboBox()
        self.bandpass_combo.addItems(["None", "50-200 Hz", "100-300 Hz"])
        settings_layout.addWidget(QLabel("Bandpass Selection:"), 0, 0)
        settings_layout.addWidget(self.bandpass_combo, 0, 1)

        headers = ["Channel Name", "Unit", "DateTime", "RPM", "Gap", "Direct", "Bandpass", "1xA", "1xP", "2xA", "2xP", "NXAmp", "NXPhase"]
        self.checkbox_dict = {}
        for i, header in enumerate(headers):
            cb = QCheckBox(header)
            cb.setChecked(True)
            self.checkbox_dict[header] = cb
            settings_layout.addWidget(cb, (i // 3) + 1, i % 3)

        self.save_settings_button = QPushButton("Save")
        self.save_settings_button.clicked.connect(self.save_settings)
        self.close_settings_button = QPushButton("Close")
        self.close_settings_button.clicked.connect(self.close_settings)
        settings_layout.addWidget(self.save_settings_button, len(headers) // 3 + 1, 0)
        settings_layout.addWidget(self.close_settings_button, len(headers) // 3 + 1, 1)
        settings_layout.addWidget(QLabel(""), len(headers) // 3 + 1, 2)  # Spacer
        layout.addWidget(self.settings_panel)

        self.table = QTableWidget()
        self.table.setRowCount(self.num_channels)
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setFixedHeight(100 * self.num_channels)
        layout.addWidget(self.table)

        default_data = {
            "Channel Name": "N/A", "Unit": "mil", "DateTime": datetime.now().strftime("%d-%b-%Y %I:%M:%S %p"),
            "RPM": "0.00", "Gap": "0.00", "Direct": "0.00", "Bandpass": "0.00", "1xA": "0.00",
            "1xP": "0.00", "2xA": "0.00", "2xP": "0.00", "NXAmp": "0.00", "NXPhase": "0.00"
        }
        for row in range(self.num_channels):
            default_data["Channel Name"] = self.channel_names[row] if row < len(self.channel_names) else f"Channel {row+1}"
            default_data["Unit"] = self.channel_properties.get(self.channel_names[row], {"Unit": "mil"})["Unit"]
            for col, header in enumerate(headers):
                item = QTableWidgetItem(default_data[header])
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        scroll_area.setWidget(self.scroll_content)
        layout.addWidget(scroll_area)

        self.initialize_plots()

        if self.console:
            self.console.append_to_console(f"Initialized UI with {self.num_channels} channels: {self.channel_names}")

    def initialize_thread(self):
        self.worker = TabularViewWorker(self, self.project_name, self.model_name, self.channel, self.db)
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.error.connect(self.log_and_set_status)
        self.worker.initialized.connect(self.complete_initialization)
        self.thread.start()

    def complete_initialization(self, channel_names, num_channels, tag_name, channel_properties, project_id):
        try:
            self.channel_names = channel_names
            self.num_channels = num_channels
            self.tag_name = tag_name
            self.channel_properties = channel_properties
            self.project_id = project_id

            self.table.setRowCount(self.num_channels)
            self.channel_selector.clear()
            self.channel_selector.addItem("Select Channel")
            self.channel_selector.addItems(self.channel_names)
            if self.channel in self.channel_names:
                self.selected_channel_idx = self.channel_names.index(self.channel)
                self.channel_selector.setCurrentIndex(self.selected_channel_idx + 1)
            else:
                self.log_and_set_status(f"Selected channel {self.channel} not found. Defaulting to first channel.")
                self.selected_channel_idx = 0
                self.channel_selector.setCurrentIndex(1 if self.channel_names else 0)

            self.initialize_data_arrays()
            self.update_table_defaults()
            self.load_settings_from_database()
            self.initialize_plots()

            if self.console:
                self.console.append_to_console(f"Initialized with TagName: {self.tag_name}, Model: {self.model_name}, Channels: {self.channel_names}, Project ID: {self.project_id}")
        except Exception as ex:
            self.log_and_set_status(f"Error completing initialization: {str(ex)}")
            self.channel_names = ["Channel 1"]
            self.num_channels = 1
            self.table.setRowCount(1)
            self.channel_selector.clear()
            self.channel_selector.addItem("Select Channel")
            self.channel_selector.addItems(self.channel_names)
            self.channel_selector.setCurrentIndex(1)
            self.initialize_data_arrays()
            self.update_table_defaults()
            self.initialize_plots()

    def initialize_plots(self):
        for widget in self.plot_widgets:
            self.scroll_layout.removeWidget(widget)
            widget.deleteLater()
        self.plot_widgets = []
        self.plots = []

        plot_titles = [
            "Raw Data", "Low-Pass Filtered Data (20 Hz)", "High-Pass Filtered Data (200 Hz)",
            "Band-Pass Filtered Data (50-200 Hz)", "Bandpass Peak-to-Peak Over Time"
        ]

        for i, title in enumerate(plot_titles):
            plot_widget = pg.PlotWidget(title=title)
            plot_widget.showGrid(x=True, y=True)
            plot_widget.setLabel('bottom', 'Time (s)' if i < 4 else 'Time (s)')
            plot_widget.setLabel('left', 'Amplitude' if i < 4 else 'Peak-to-Peak Value')
            plot_widget.setFixedHeight(250)
            self.scroll_layout.addWidget(plot_widget)
            self.plot_widgets.append(plot_widget)
            plot = plot_widget.plot(pen='b')
            plot.setData(np.array([]), np.array([]))
            self.plots.append(plot)

        self.scroll_layout.addStretch()
        self.update_plots()

    def get_widget(self):
        return self.widget

    def update_selected_channel(self, index):
        if index > 0:
            self.selected_channel_idx = index - 1
            if self.console:
                self.console.append_to_console(f"Selected channel for plots: {self.channel_names[self.selected_channel_idx]}")
        else:
            self.selected_channel_idx = 0
            if self.console:
                self.console.append_to_console("No valid channel selected for plots, defaulting to first channel.")
        self.update_plots()

    def initialize_data_arrays(self):
        self.raw_data = [np.zeros(4096) for _ in range(self.num_channels)]
        self.low_pass_data = [np.zeros(4096) for _ in range(self.num_channels)]
        self.high_pass_data = [np.zeros(4096) for _ in range(self.num_channels)]
        self.band_pass_data = [np.zeros(4096) for _ in range(self.num_channels)]
        self.band_pass_peak_to_peak_history = [[] for _ in range(self.num_channels)]
        self.band_pass_peak_to_peak_times = [[] for _ in range(self.num_channels)]
        self.average_frequency = [0.0 for _ in range(self.num_channels)]
        self.band_pass_peak_to_peak = [0.0 for _ in range(self.num_channels)]
        self.one_x_amps = [[] for _ in range(self.num_channels)]
        self.one_x_phases = [[] for _ in range(self.num_channels)]
        self.two_x_amps = [[] for _ in range(self.num_channels)]
        self.two_x_phases = [[] for _ in range(self.num_channels)]
        self.three_x_amps = [[] for _ in range(self.num_channels)]
        self.three_x_phases = [[] for _ in range(self.num_channels)]
        self.time_points = np.arange(4096) / self.sample_rate

    def update_table_defaults(self):
        headers = ["Channel Name", "Unit", "DateTime", "RPM", "Gap", "Direct", "Bandpass", "1xA", "1xP", "2xA", "2xP", "NXAmp", "NXPhase"]
        default_data = {
            "Channel Name": "N/A", "Unit": "mil", "DateTime": datetime.now().strftime("%d-%b-%Y %I:%M:%S %p"),
            "RPM": "0.00", "Gap": "0.00", "Direct": "0.00", "Bandpass": "0.00", "1xA": "0.00",
            "1xP": "0.00", "2xA": "0.00", "2xP": "0.00", "NXAmp": "0.00", "NXPhase": "0.00"
        }
        for row in range(self.num_channels):
            default_data["Channel Name"] = self.channel_names[row] if row < len(self.channel_names) else f"Channel {row+1}"
            default_data["Unit"] = self.channel_properties.get(self.channel_names[row], {"Unit": "mil"})["Unit"]
            for col, header in enumerate(headers):
                item = QTableWidgetItem(default_data[header])
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)
        self.table.setFixedHeight(100 * self.num_channels)
        if self.console:
            self.console.append_to_console(f"Updated table with {self.num_channels} rows for channels: {self.channel_names}")

    def load_settings_from_database(self):
        try:
            database = self.mongo_client.get_database("changed_db")
            settings_collection = database.get_collection("TabularViewSettings")
            setting = settings_collection.find_one({"projectId": self.project_id}, sort=[("updated_at", -1)])
            if setting:
                self.bandpass_selection = setting.get("bandpassSelection", "None")
                self.column_visibility = {
                    "Channel Name": setting.get("channelNameVisible", True),
                    "Unit": setting.get("unitVisible", True),
                    "DateTime": setting.get("datetimeVisible", True),
                    "RPM": setting.get("rpmVisible", True),
                    "Gap": setting.get("gapVisible", True),
                    "Direct": setting.get("directVisible", True),
                    "Bandpass": setting.get("bandpassVisible", True),
                    "1xA": setting.get("one_xa_visible", True),
                    "1xP": setting.get("one_xp_visible", True),
                    "2xA": setting.get("two_xa_visible", True),
                    "2xP": setting.get("two_xp_visible", True),
                    "NXAmp": setting.get("nx_amp_visible", True),
                    "NXPhase": setting.get("nx_phase_visible", True)
                }
                self.bandpass_combo.setCurrentText(self.bandpass_selection)
                for header, cb in self.checkbox_dict.items():
                    cb.setChecked(self.column_visibility[header])
                if self.console:
                    self.console.append_to_console(f"Loaded TabularView settings for project ID: {self.project_id}")
            else:
                if self.console:
                    self.console.append_to_console(f"No TabularView settings found for project ID: {self.project_id}. Using defaults.")
            self.update_column_visibility()
        except Exception as ex:
            self.log_and_set_status(f"Error loading TabularView settings: {str(ex)}")

    def save_settings_to_database(self):
        try:
            database = self.mongo_client.get_database("changed_db")
            settings_collection = database.get_collection("TabularViewSettings")
            setting = {
                "projectId": self.project_id,
                "bandpassSelection": self.bandpass_selection,
                "channelNameVisible": self.column_visibility["Channel Name"],
                "unitVisible": self.column_visibility["Unit"],
                "datetimeVisible": self.column_visibility["DateTime"],
                "rpmVisible": self.column_visibility["RPM"],
                "gapVisible": self.column_visibility["Gap"],
                "directVisible": self.column_visibility["Direct"],
                "bandpassVisible": self.column_visibility["Bandpass"],
                "one_xa_visible": self.column_visibility["1xA"],
                "one_xp_visible": self.column_visibility["1xP"],
                "two_xa_visible": self.column_visibility["2xA"],
                "two_xp_visible": self.column_visibility["2xP"],
                "nx_amp_visible": self.column_visibility["NXAmp"],
                "nx_phase_visible": self.column_visibility["NXPhase"],
                "updated_at": datetime.utcnow()
            }
            settings_collection.update_one(
                {"projectId": self.project_id},
                {"$set": setting},
                upsert=True
            )
            if self.console:
                self.console.append_to_console(f"Saved TabularView settings for project ID: {self.project_id}")
        except Exception as ex:
            self.log_and_set_status(f"Error saving TabularView settings: {str(ex)}")

    def toggle_settings(self):
        self.settings_panel.setVisible(not self.settings_panel.isVisible())
        self.settings_button.setVisible(not self.settings_panel.isVisible())

    def save_settings(self):
        self.bandpass_selection = self.bandpass_combo.currentText()
        self.column_visibility = {header: cb.isChecked() for header, cb in self.checkbox_dict.items()}
        self.save_settings_to_database()
        self.update_column_visibility()
        self.settings_panel.setVisible(False)
        self.settings_button.setVisible(True)
        if self.console:
            self.console.append_to_console("Table settings updated and saved.")

    def close_settings(self):
        self.bandpass_combo.setCurrentText(self.bandpass_selection)
        for header, cb in self.checkbox_dict.items():
            cb.setChecked(self.column_visibility[header])
        self.settings_panel.setVisible(False)
        self.settings_button.setVisible(True)

    def update_column_visibility(self):
        headers = ["Channel Name", "Unit", "DateTime", "RPM", "Gap", "Direct", "Bandpass", "1xA", "1xP", "2xA", "2xP", "NXAmp", "NXPhase"]
        for col, header in enumerate(headers):
            self.table.setColumnHidden(col, not self.column_visibility[header])

    def compute_harmonics(self, data, start_idx, length, harmonic):
        if length <= 0 or start_idx + length > len(data):
            return 0.0, 0.0
        sine_sum = cosine_sum = 0.0
        for n in range(length):
            global_idx = start_idx + n
            theta = (2 * np.pi * harmonic * n) / length
            sine_sum += data[global_idx] * np.sin(theta)
            cosine_sum += data[global_idx] * np.cos(theta)
        amplitude = np.sqrt((sine_sum / length) ** 2 + (cosine_sum / length) ** 2) * 2 if length > 0 else 0.0
        phase = np.arctan2(cosine_sum, sine_sum) * (180.0 / np.pi) if length > 0 else 0.0
        if phase < 0:
            phase += 360
        return amplitude, phase

    def process_calibrated_data(self, data, channel_idx):
        channel_name = self.channel_names[channel_idx]
        props = self.channel_properties.get(channel_name, {"Unit": "mil", "CorrectionValue": 1.0, "Gain": 1.0, "Sensitivity": 1.0})
        channel_data = np.array(data[channel_idx], dtype=float) * (3.3 / 65535.0) * (props["CorrectionValue"] * props["Gain"]) / props["Sensitivity"]
        if props["Unit"].lower() == "mil":
            channel_data /= 25.4
        elif props["Unit"].lower() == "mm":
            channel_data /= 1000.0
        return channel_data

    def format_direct_value(self, values, unit):
        if not values or len(values) == 0:
            return "0.0"
        avg = np.mean(values)
        if unit.lower() == "mil":
            return f"{avg:.1f}"
        elif unit.lower() == "um":
            return f"{int(avg)}"
        elif unit.lower() == "mm":
            return f"{avg:.3f}"
        return f"{avg:.1f}"

    def on_data_received(self, tag_name, model_name, values, sample_rate, header=None):
        if not values or len(values) < 6:
            return

        try:
            # Pad or truncate to 6 channels, 4096 samples each
            values = values[:6] + [np.zeros(4096).tolist() for _ in range(6 - len(values))] if len(values) < 6 else values[:6]
            for i in range(len(values)):
                if len(values[i]) < 4096:
                    values[i] = np.pad(values[i], (0, 4096 - len(values[i])), 'constant')[:4096]
                elif len(values[i]) > 4096:
                    values[i] = values[i][:4096]

            self.sample_rate = sample_rate if sample_rate > 0 else 4096
            self.data = values
            main_channels = min(self.num_channels, len(values), 4)

            frequency_data = np.array(values[4], dtype=float) / 100.0
            trigger_data = np.array(values[5], dtype=float)

            for ch in range(main_channels):
                channel_name = self.channel_names[ch] if ch < len(self.channel_names) else f"Channel {ch+1}"
                self.raw_data[ch] = self.process_calibrated_data(values, ch)

                # Filter design
                nyquist = self.sample_rate / 2.0
                tap_num = 31
                low_pass_coeffs = signal.firwin(tap_num, 20 / nyquist, window='hamming')
                high_pass_coeffs = signal.firwin(tap_num, 200 / nyquist, window='hamming', pass_zero=False)
                band_pass_coeffs = signal.firwin(tap_num, [50 / nyquist, 200 / nyquist], window='hamming', pass_zero=False)

                self.low_pass_data[ch] = signal.lfilter(low_pass_coeffs, 1.0, self.raw_data[ch])
                self.high_pass_data[ch] = signal.lfilter(high_pass_coeffs, 1.0, self.raw_data[ch])
                self.band_pass_data[ch] = signal.lfilter(band_pass_coeffs, 1.0, self.raw_data[ch])

                # RPM calculation
                valid_freqs = frequency_data[frequency_data > 0]
                self.average_frequency[ch] = np.mean(valid_freqs) if valid_freqs.size > 0 else 0.0
                rpm_values = [(f / 100.0) * 60.0 for f in valid_freqs]
                average_rpm = np.mean(rpm_values) if rpm_values else 0.0

                # Trigger detection
                trigger_indices = np.where(trigger_data == 1)[0]
                if len(trigger_indices) < 2:
                    trigger_indices = [0, len(trigger_data) - 1]
                filtered_trigger_indices = [trigger_indices[0]]
                for i in range(1, len(trigger_indices)):
                    if trigger_indices[i] - filtered_trigger_indices[-1] >= 5:
                        filtered_trigger_indices.append(trigger_indices[i])

                band_pass_peak_to_peak_values = []
                direct_values = []
                one_x_amps, one_x_phases = [], []
                two_x_amps, two_x_phases = [], []
                three_x_amps, three_x_phases = [], []

                for i in range(len(filtered_trigger_indices) - 1):
                    start_idx = filtered_trigger_indices[i]
                    end_idx = filtered_trigger_indices[i + 1]
                    segment_length = end_idx - start_idx
                    if segment_length <= 0 or start_idx >= len(self.raw_data[ch]) or end_idx > len(self.raw_data[ch]):
                        continue

                    segment_bp = self.band_pass_data[ch][start_idx:end_idx]
                    segment_raw = self.raw_data[ch][start_idx:end_idx]
                    if len(segment_bp) > 0:
                        band_pass_peak_to_peak_values.append(np.ptp(segment_bp))
                    if len(segment_raw) > 0:
                        direct_values.append(np.ptp(segment_raw))

                    amp1, phase1 = self.compute_harmonics(self.raw_data[ch], start_idx, segment_length, 1)
                    amp2, phase2 = self.compute_harmonics(self.raw_data[ch], start_idx, segment_length, 2)
                    amp3, phase3 = self.compute_harmonics(self.raw_data[ch], start_idx, segment_length, 3)
                    one_x_amps.append(amp1)
                    one_x_phases.append(phase1)
                    two_x_amps.append(amp2)
                    two_x_phases.append(phase2)
                    three_x_amps.append(amp3)
                    three_x_phases.append(phase3)

                self.band_pass_peak_to_peak[ch] = np.mean(band_pass_peak_to_peak_values) if band_pass_peak_to_peak_values else 0.0
                self.band_pass_peak_to_peak_history[ch].append(self.band_pass_peak_to_peak[ch])
                self.band_pass_peak_to_peak_times[ch].append((datetime.now() - self.start_time).total_seconds())
                self.one_x_amps[ch].append(np.mean(one_x_amps) if one_x_amps else 0.0)
                self.one_x_phases[ch].append(np.mean(one_x_phases) if one_x_phases else 0.0)
                self.two_x_amps[ch].append(np.mean(two_x_amps) if two_x_amps else 0.0)
                self.two_x_phases[ch].append(np.mean(two_x_phases) if two_x_phases else 0.0)
                self.three_x_amps[ch].append(np.mean(three_x_amps) if three_x_amps else 0.0)
                self.three_x_phases[ch].append(np.mean(three_x_phases) if three_x_phases else 0.0)

                props = self.channel_properties.get(channel_name, {"Unit": "mil"})
                unit = props["Unit"]
                direct_formatted = self.format_direct_value(direct_values, unit)
                gap_value = 0.0  # No header data

                channel_data = {
                    "Channel Name": channel_name,
                    "Unit": unit,
                    "DateTime": datetime.now().strftime("%d-%b-%Y %I:%M:%S %p"),
                    "RPM": f"{average_rpm:.2f}",
                    "Gap": f"{gap_value:.2f}",
                    "Direct": direct_formatted,
                    "Bandpass": f"{self.band_pass_peak_to_peak[ch]:.2f}",
                    "1xA": f"{np.mean(self.one_x_amps[ch]):.2f}" if self.one_x_amps[ch] else "0.00",
                    "1xP": f"{np.mean(self.one_x_phases[ch]):.2f}" if self.one_x_phases[ch] else "0.00",
                    "2xA": f"{np.mean(self.two_x_amps[ch]):.2f}" if self.two_x_amps[ch] else "0.00",
                    "2xP": f"{np.mean(self.two_x_phases[ch]):.2f}" if self.two_x_phases[ch] else "0.00",
                    "NXAmp": f"{np.mean(self.three_x_amps[ch]):.2f}" if self.three_x_amps[ch] else "0.00",
                    "NXPhase": f"{np.mean(self.three_x_phases[ch]):.2f}" if self.three_x_phases[ch] else "0.00"
                }

                self.update_table_row(ch, channel_data)

            self.update_plots()

        except Exception as ex:
            self.log_and_set_status(f"Error processing data: {str(ex)}")

    def update_table_row(self, row, channel_data):
        headers = ["Channel Name", "Unit", "DateTime", "RPM", "Gap", "Direct", "Bandpass", "1xA", "1xP", "2xA", "2xP", "NXAmp", "NXPhase"]
        for col, header in enumerate(headers):
            item = QTableWidgetItem(channel_data[header])
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, col, item)

    def update_display(self):
        self.update_plots()
        for ch in range(min(self.num_channels, 4)):
            channel_name = self.channel_names[ch] if ch < len(self.channel_names) else f"Channel {ch+1}"
            props = self.channel_properties.get(channel_name, {"Unit": "mil"})
            unit = props["Unit"]
            channel_data = {
                "Channel Name": channel_name,
                "Unit": unit,
                "DateTime": datetime.now().strftime("%d-%b-%Y %I:%M:%S %p"),
                "RPM": f"{self.average_frequency[ch] * 60.0:.2f}" if self.average_frequency[ch] > 0 else "0.00",
                "Gap": "0.00",
                "Direct": self.format_direct_value([np.ptp(self.raw_data[ch])], unit),
                "Bandpass": f"{self.band_pass_peak_to_peak[ch]:.2f}",
                "1xA": f"{np.mean(self.one_x_amps[ch]):.2f}" if self.one_x_amps[ch] else "0.00",
                "1xP": f"{np.mean(self.one_x_phases[ch]):.2f}" if self.one_x_phases[ch] else "0.00",
                "2xA": f"{np.mean(self.two_x_amps[ch]):.2f}" if self.two_x_amps[ch] else "0.00",
                "2xP": f"{np.mean(self.two_x_phases[ch]):.2f}" if self.two_x_phases[ch] else "0.00",
                "NXAmp": f"{np.mean(self.three_x_amps[ch]):.2f}" if self.three_x_amps[ch] else "0.00",
                "NXPhase": f"{np.mean(self.three_x_phases[ch]):.2f}" if self.three_x_phases[ch] else "0.00"
            }
            self.update_table_row(ch, channel_data)

    def update_plots(self):
        if not self.plot_widgets or not self.plots:
            return

        ch = self.selected_channel_idx
        if ch >= self.num_channels:
            ch = 0

        trim_samples = 47
        low_pass_trim = 0
        high_pass_trim = 110
        band_pass_trim = 110
        raw_trim = trim_samples

        if len(self.raw_data[ch]) <= trim_samples:
            raw_trim = low_pass_trim = high_pass_trim = band_pass_trim = 0

        data_sets = [
            (self.raw_data[ch], raw_trim, "Raw Data"),
            (self.low_pass_data[ch], low_pass_trim, "Low-Pass Filtered Data (20 Hz)"),
            (self.high_pass_data[ch], high_pass_trim, "High-Pass Filtered Data (200 Hz)"),
            (self.band_pass_data[ch], band_pass_trim, "Band-Pass Filtered Data (50-200 Hz)")
        ]

        for i, (data, trim, title) in enumerate(data_sets):
            if len(data) <= trim:
                data = np.array([0])
                time_data = np.array([0])
            else:
                data = data[trim:]
                time_data = self.time_points[trim:]
            self.plots[i].setData(time_data, data)
            self.plot_widgets[i].setTitle(f"{title} (Channel: {self.channel_names[ch]}, Freq: {self.average_frequency[ch]:.2f} Hz)")
            y_min = np.min(data) * 1.1 if data.size > 0 else -1.0
            y_max = np.max(data) * 1.1 if data.size > 0 else 1.0
            self.plot_widgets[i].setYRange(y_min, y_max, padding=0.1)

        # Peak-to-Peak plot
        if self.band_pass_peak_to_peak_times[ch] and self.band_pass_peak_to_peak_history[ch]:
            self.plots[4].setData(self.band_pass_peak_to_peak_times[ch], self.band_pass_peak_to_peak_history[ch])
            y_max = max(0.01, max(self.band_pass_peak_to_peak_history[ch]) * 1.1)
            self.plot_widgets[4].setYRange(0, y_max, padding=0.1)
        else:
            self.plots[4].setData(np.array([0]), np.array([0]))
            self.plot_widgets[4].setYRange(0, 0.01, padding=0.1)

    def log_and_set_status(self, message):
        logging.error(message)
        if self.console:
            self.console.append_to_console(message)

    def close(self):
        self.timer.stop()
        if hasattr(self, 'thread') and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
        self.mongo_client.close()