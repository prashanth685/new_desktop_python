import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QPushButton, QComboBox, QGridLayout
from PyQt5.QtCore import QObject, QEvent, Qt, QTimer
from PyQt5.QtGui import QIcon
from pyqtgraph import PlotWidget, mkPen, AxisItem, InfiniteLine, SignalProxy
from datetime import datetime
import time
import re
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class TimeAxisItem(AxisItem):
    """Custom axis to display datetime on x-axis."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        """Convert timestamps to 'YYYY-MM-DD\nHH:MM:SS' format."""
        return [datetime.fromtimestamp(v).strftime('%Y-%m-%d\n%H:%M:%S') for v in values]

class MouseTracker(QObject):
    """Event filter to track mouse enter/leave on plot viewport."""
    def __init__(self, parent, idx, feature):
        super().__init__(parent)
        self.idx = idx
        self.feature = feature

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Enter:
            self.feature.mouse_enter(self.idx)
        elif event.type() == QEvent.Leave:
            self.feature.mouse_leave(self.idx)
        return False

class TimeViewFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None):
        super().__init__()
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.channel = channel
        self.model_name = model_name
        self.console = console
        self.is_saving = False
        self.filename_counter = 0
        self.current_filename = None
        self.widget = None
        self.plot_widgets = []
        self.plots = []
        self.fifo_data = []  # FIFO buffers for each channel
        self.fifo_times = []  # FIFO time buffers
        self.sample_rate = None
        self.main_channels = None
        self.tacho_channels_count = None
        self.total_channels = None
        self.scaling_factor = 3.3 / 65535
        self.num_plots = None
        self.samples_per_channel = None
        self.vlines = []
        self.proxies = []
        self.trackers = []
        self.trigger_lines = []
        self.active_line_idx = None
        self.window_seconds = 1  # Default window size in seconds
        self.fifo_window_samples = None
        self.settings_panel = None
        self.settings_button = None
        self.refresh_timer = None
        self.needs_refresh = []  # Flag for plot updates
        self.is_initialized = False  # Track initialization state
        self.initUI()

    def initUI(self):
        """Initialize the UI with settings panel and placeholder for dynamic plots."""
        self.widget = QWidget()
        main_layout = QVBoxLayout()

        # Settings and channel selection
        top_layout = QHBoxLayout()
        self.settings_button = QPushButton("Settings")
        self.settings_button.setIcon(QIcon("settings_icon.png"))  # Replace with your image path
        self.settings_button.clicked.connect(self.toggle_settings)
        top_layout.addWidget(self.settings_button)
        top_layout.addStretch()
        main_layout.addLayout(top_layout)

        # Settings panel
        self.settings_panel = QWidget()
        self.settings_panel.setVisible(False)
        settings_layout = QGridLayout()
        self.settings_panel.setLayout(settings_layout)

        # Window Seconds
        settings_layout.addWidget(QLabel("Window Size (seconds)"), 0, 0)
        window_combo = QComboBox()
        window_combo.addItems([str(i) for i in range(1, 11)])
        window_combo.setCurrentText(str(self.window_seconds))
        settings_layout.addWidget(window_combo, 0, 1)
        self.settings_widgets = {"WindowSeconds": window_combo}

        # Save and Close buttons
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_settings)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close_settings)
        settings_layout.addWidget(save_button, 1, 0)
        settings_layout.addWidget(close_button, 1, 1)

        main_layout.addWidget(self.settings_panel)

        # Create a scroll area to contain the plots
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)
        self.widget.setLayout(main_layout)

        # Initialize refresh timer but don't start it yet
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_plots)

        if not self.model_name and self.console:
            self.console.append_to_console("No model selected in TimeViewFeature.")
        if not self.channel and self.console:
            self.console.append_to_console("No channel selected in TimeViewFeature.")
        logging.debug("UI initialized, waiting for data to start refresh timer")

    def initialize_plots(self):
        """Initialize plots based on dynamically received channel counts."""
        if not self.main_channels or not self.tacho_channels_count or not self.total_channels:
            logging.error("Cannot initialize plots: channel counts not set")
            self.log_and_set_status("Cannot initialize plots: channel counts not set")
            return

        # Clear existing plots
        self.plot_widgets = []
        self.plots = []
        self.fifo_data = []
        self.fifo_times = []
        self.vlines = []
        self.proxies = []
        self.trackers = []
        self.trigger_lines = []
        self.needs_refresh = []

        # Clear existing scroll content
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)

        colors = ['r', 'g', 'b', 'y', 'c', 'm', 'k', 'w', '#FF4500', '#32CD32', '#00CED1', '#FFD700', '#FF69B4', '#8A2BE2', '#FF6347', '#20B2AA', '#ADFF2F', '#9932CC', '#FF7F50', '#00FA9A', '#9400D3']  # Extended color list for up to 20+ channels
        self.num_plots = self.total_channels
        for i in range(self.num_plots):
            plot_widget = PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')}, background='w')
            plot_widget.setFixedHeight(250)
            plot_widget.setMinimumWidth(0)
            if i < self.main_channels:
                plot_widget.setLabel('left', f'CH{i+1} Value')
            elif i == self.main_channels:
                plot_widget.setLabel('left', 'Tacho Frequency')
            else:
                plot_widget.setLabel('left', f'Tacho Trigger {i - self.main_channels}')
                plot_widget.setYRange(-0.5, 1.5, padding=0)
            plot_widget.showGrid(x=True, y=True)
            plot_widget.addLegend()
            pen = mkPen(color=colors[i % len(colors)], width=2)
            plot = plot_widget.plot([], [], pen=pen)
            self.plots.append(plot)
            self.plot_widgets.append(plot_widget)
            self.fifo_data.append([])
            self.fifo_times.append([])
            self.needs_refresh.append(True)

            vline = InfiniteLine(angle=90, movable=False, pen=mkPen('r', width=2))
            vline.setVisible(False)
            plot_widget.addItem(vline)
            self.vlines.append(vline)

            if i == self.num_plots - 1:
                self.trigger_lines = []
            else:
                self.trigger_lines.append(None)

            proxy = SignalProxy(plot_widget.scene().sigMouseMoved, rateLimit=60, slot=lambda evt, idx=i: self.mouse_moved(evt, idx))
            self.proxies.append(proxy)

            tracker = MouseTracker(plot_widget.viewport(), i, self)
            plot_widget.viewport().installEventFilter(tracker)
            self.trackers.append(tracker)

            self.scroll_layout.addWidget(plot_widget)

        self.scroll_area.setWidget(self.scroll_content)
        self.initialize_buffers()

    def initialize_buffers(self):
        """Initialize FIFO buffers for each channel."""
        if not self.sample_rate or not self.num_plots or not self.samples_per_channel:
            logging.error("Cannot initialize buffers: sample_rate, num_plots, or samples_per_channel not set")
            self.log_and_set_status("Buffer initialization failed: Missing sample_rate, num_plots, or samples_per_channel")
            return
        self.fifo_window_samples = self.sample_rate * self.window_seconds
        for i in range(self.num_plots):
            self.fifo_data[i] = np.zeros(self.fifo_window_samples)
            time_step = self.window_seconds / self.fifo_window_samples
            self.fifo_times[i] = np.array([i * time_step for i in range(self.fifo_window_samples)])
        logging.debug(f"Initialized FIFO buffers: {self.num_plots} channels, {self.fifo_window_samples} samples each")
        self.is_initialized = True  # Mark initialization as complete
        # Start the refresh timer if not already running
        if not self.refresh_timer.isActive():
            self.refresh_timer.start(100)
            logging.debug("Started refresh timer after buffer initialization")

    def load_project_data(self):
        """Load project data to initialize model information."""
        try:
            project_data = self.db.get_project_data(self.project_name)
            if project_data and "models" in project_data:
                for model in project_data["models"]:
                    if model.get("name") == self.model_name:
                        logging.debug(f"Loaded project data for model {self.model_name}")
                        if self.console:
                            self.console.append_to_console(f"Loaded project data for model {self.model_name}")
                        return
                self.log_and_set_status(f"No model data found for {self.model_name}")
            else:
                self.log_and_set_status(f"No valid project data found for {self.project_name}")
        except Exception as e:
            self.log_and_set_status(f"Error loading project data: {str(e)}")

    def toggle_settings(self):
        """Toggle visibility of the settings panel."""
        self.settings_panel.setVisible(not self.settings_panel.isVisible())
        self.settings_button.setVisible(not self.settings_panel.isVisible())

    def save_settings(self):
        """Save settings from the panel and update buffers."""
        try:
            selected_seconds = int(self.settings_widgets["WindowSeconds"].currentText())
            if 1 <= selected_seconds <= 10:
                if selected_seconds != self.window_seconds:
                    self.window_seconds = selected_seconds
                    self.update_window_size()
                    if self.console:
                        self.console.append_to_console(f"Applied window size: {self.window_seconds} seconds.")
                self.settings_panel.setVisible(False)
                self.settings_button.setVisible(True)
            else:
                self.log_and_set_status(f"Invalid window seconds selected: {selected_seconds}. Must be 1-10.")
        except Exception as e:
            self.log_and_set_status(f"Error saving TimeView settings: {str(e)}")

    def close_settings(self):
        """Close the settings panel without saving."""
        self.settings_widgets["WindowSeconds"].setCurrentText(str(self.window_seconds))
        self.settings_panel.setVisible(False)
        self.settings_button.setVisible(True)

    def update_window_size(self):
        """Update FIFO buffer sizes when window_seconds changes."""
        if not self.sample_rate or not self.num_plots:
            logging.error("Cannot update window size: sample_rate or num_plots not set")
            self.log_and_set_status("Cannot update window size: Missing sample_rate or num_plots")
            return
        new_fifo_window_samples = self.sample_rate * self.window_seconds
        for i in range(self.num_plots):
            current_data = self.fifo_data[i]
            current_length = len(current_data)
            new_data = np.zeros(new_fifo_window_samples)
            copy_length = min(current_length, new_fifo_window_samples)
            new_data[:copy_length] = current_data[:copy_length]
            self.fifo_data[i] = new_data
            time_step = self.window_seconds / new_fifo_window_samples
            self.fifo_times[i] = np.array([j * time_step for j in range(new_fifo_window_samples)])
            self.needs_refresh[i] = True
        self.fifo_window_samples = new_fifo_window_samples
        logging.debug(f"Updated FIFO buffers to {self.window_seconds} seconds, {self.fifo_window_samples} samples")

    def get_widget(self):
        """Return the widget containing the plots."""
        return self.widget

    def refresh_filenames(self):
        """Retrieve distinct filenames from the database and update filename counter."""
        try:
            filenames = self.db.get_distinct_filenames(self.project_name, self.model_name)
            logging.debug(f"Retrieved filenames from database: {filenames}")
            
            if filenames:
                numbers = []
                for f in filenames:
                    match = re.match(r"data(\d+)", f)
                    if match:
                        numbers.append(int(match.group(1)))
                self.filename_counter = max(numbers, default=0) + 1 if numbers else 1
            else:
                self.filename_counter = 1
                
            logging.info(f"Updated filename counter to: {self.filename_counter}")
            if self.console:
                self.console.append_to_console(f"Refreshed filenames: {len(filenames)} found, counter set to {self.filename_counter}")
            return filenames
        except Exception as e:
            self.log_and_set_status(f"Error refreshing filenames: {str(e)}")
            self.filename_counter = 1
            return []

    def start_saving(self):
        """Start saving data to the database."""
        if not self.parent.current_project or not self.model_name:
            self.log_and_set_status("Cannot start saving: No project or model selected")
            return
        
        self.refresh_filenames()
        
        self.is_saving = True
        self.current_filename = f"data{self.filename_counter}"
        logging.info(f"Started saving data to filename: {self.current_filename}")
        if self.console:
            self.console.append_to_console(f"Started saving data to {self.current_filename}")

    def stop_saving(self):
        """Stop saving data and increment filename counter."""
        self.is_saving = False
        self.current_filename = None
        self.filename_counter += 1
        logging.info(f"Stopped saving data, new filename counter: {self.filename_counter}")
        if self.console:
            self.console.append_to_console(f"Stopped saving data, next filename counter: {self.filename_counter}")
        try:
            self.parent.sub_tool_bar.refresh_filenames()
        except AttributeError:
            logging.warning("No sub_tool_bar found to refresh filenames")

    def on_data_received(self, tag_name, model_name, values, sample_rate):
        """Handle incoming MQTT data, update FIFO buffers, and save if enabled."""
        logging.debug(f"on_data_received called with tag_name={tag_name}, model_name={model_name}, "
                    f"values_len={len(values) if values else 0}, sample_rate={sample_rate}")
        if self.model_name != model_name:
            logging.debug(f"Ignoring data for model {model_name}, expected {self.model_name}")
            return
        try:
            # Validate input data
            if not values or not sample_rate or sample_rate <= 0:
                self.log_and_set_status(f"Invalid MQTT data: values={values}, sample_rate={sample_rate}")
                return

            # Dynamically set channel counts from MQTT data
            self.main_channels = len(values) - 2 if len(values) >= 2 else 0
            self.tacho_channels_count = 2  # Assuming 2 tacho channels
            self.total_channels = self.main_channels + self.tacho_channels_count
            self.num_plots = self.total_channels
            self.sample_rate = sample_rate
            self.samples_per_channel = len(values[0]) if values else 0

            if not self.main_channels or len(values) < self.tacho_channels_count:
                self.log_and_set_status(f"Received incorrect number of sublists: {len(values) if values else 0}, expected at least {self.tacho_channels_count}")
                return

            if not all(len(values[i]) == self.samples_per_channel for i in range(self.main_channels)):
                self.log_and_set_status(f"Channel data length mismatch: expected {self.samples_per_channel} samples")
                return

            tacho_freq_samples = len(values[self.main_channels]) if self.main_channels < len(values) else 0
            tacho_trigger_samples = len(values[self.main_channels + 1]) if self.main_channels + 1 < len(values) else 0
            if tacho_freq_samples != self.samples_per_channel or tacho_trigger_samples != self.samples_per_channel:
                self.log_and_set_status(f"Tacho data length mismatch: freq={tacho_freq_samples}, trigger={tacho_trigger_samples}, expected={self.samples_per_channel}")
                return

            # Initialize plots and buffers if not already done or if channel counts changed
            if not self.fifo_data or len(self.fifo_data) != self.num_plots or not self.is_initialized:
                self.initialize_plots()

            # Update FIFO buffers
            current_time = time.time()
            time_step = 1.0 / sample_rate
            new_times = np.array([current_time - (self.samples_per_channel - 1 - i) * time_step for i in range(self.samples_per_channel)])

            # Shift and append data
            for ch in range(self.main_channels):
                new_data = np.array(values[ch]) * self.scaling_factor
                self.fifo_data[ch] = np.roll(self.fifo_data[ch], -self.samples_per_channel)
                self.fifo_data[ch][-self.samples_per_channel:] = new_data
                self.needs_refresh[ch] = True

            if self.tacho_channels_count >= 1:
                self.fifo_data[self.main_channels] = np.roll(self.fifo_data[self.main_channels], -self.samples_per_channel)
                self.fifo_data[self.main_channels][-self.samples_per_channel:] = np.array(values[self.main_channels]) / 100
                self.needs_refresh[self.main_channels] = True

            if self.tacho_channels_count >= 2:
                self.fifo_data[self.main_channels + 1] = np.roll(self.fifo_data[self.main_channels + 1], -self.samples_per_channel)
                self.fifo_data[self.main_channels + 1][-self.samples_per_channel:] = np.array(values[self.main_channels + 1])
                self.needs_refresh[self.main_channels + 1] = True

            # Update time buffer
            for ch in range(self.num_plots):
                self.fifo_times[ch] = np.roll(self.fifo_times[ch], -self.samples_per_channel)
                base_time = self.fifo_times[ch][-self.samples_per_channel - 1] if len(self.fifo_times[ch]) > self.samples_per_channel else 0
                self.fifo_times[ch][-self.samples_per_channel:] = base_time + np.array([(i + 1) * time_step for i in range(self.samples_per_channel)])

            if self.is_saving:
                try:
                    message_data = {
                        "topic": tag_name,
                        "filename": self.current_filename,
                        "frameIndex": 0,
                        "message": {
                            "channel_data": [list(values[i]) for i in range(self.main_channels)],
                            "tacho_freq": list(values[self.main_channels]) if self.tacho_channels_count >= 1 else [],
                            "tacho_trigger": list(values[self.main_channels + 1]) if self.tacho_channels_count >= 2 else []
                        },
                        "numberOfChannels": self.main_channels,
                        "samplingRate": self.sample_rate,
                        "samplingSize": self.samples_per_channel,
                        "messageFrequency": None,
                        "createdAt": datetime.now().isoformat()
                    }
                    success, msg = self.db.save_timeview_message(self.project_name, self.model_name, message_data)
                    if success:
                        logging.info(f"Saved data to database: {self.current_filename}")
                        if self.console:
                            self.console.append_to_console(f"Saved data to {self.current_filename}")
                    else:
                        self.log_and_set_status(f"Failed to save data: {msg}")
                except Exception as e:
                    self.log_and_set_status(f"Error saving data to database: {str(e)}")

            logging.debug(f"Updated FIFO buffers: {self.samples_per_channel} new samples, window={self.window_seconds}s")
        except Exception as e:
            self.log_and_set_status(f"Error processing MQTT data: {str(e)}")

    def refresh_plots(self):
        """Refresh plots if needed."""
        try:
            # Check if initialization is complete
            if not self.is_initialized or self.fifo_window_samples is None or not self.plot_widgets or \
               not self.plots or not self.fifo_data or not self.fifo_times:
                logging.warning("Skipping plot refresh: Plots or buffers not initialized")
                self.log_and_set_status("Cannot refresh plots: Initialization incomplete")
                return

            for ch in range(self.num_plots):
                if not self.needs_refresh[ch]:
                    continue

                times = self.fifo_times[ch]
                data = self.fifo_data[ch]
                if len(data) == 0 or len(times) == 0:
                    self.log_and_set_status(f"No data for plot {ch}, data_len={len(data)}, times_len={len(times)}")
                    continue

                # Ensure times array is long enough
                if len(times) < self.fifo_window_samples:
                    self.log_and_set_status(f"Insufficient time data for plot {ch}: {len(times)} < {self.fifo_window_samples}")
                    continue

                self.plots[ch].setData(times, data)
                self.plot_widgets[ch].setXRange(times[-self.fifo_window_samples], times[-1], padding=0)
                if ch < self.main_channels:
                    self.plot_widgets[ch].enableAutoRange(axis='y')
                elif ch == self.main_channels:
                    self.plot_widgets[ch].enableAutoRange(axis='y')
                else:
                    self.plot_widgets[ch].setYRange(-0.5, 1.5, padding=0)

                # Update trigger lines for the last tacho channel
                if ch == self.num_plots - 1:
                    if self.trigger_lines:
                        for line in self.trigger_lines:
                            if line:
                                self.plot_widgets[ch].removeItem(line)
                        self.trigger_lines = []

                    trigger_indices = np.where(self.fifo_data[ch][-self.fifo_window_samples:] == 1)[0]
                    logging.debug(f"Tacho trigger indices (value=1): {len(trigger_indices)} points")
                    for idx in trigger_indices:
                        if idx < len(times):
                            line = InfiniteLine(
                                pos=times[idx],
                                angle=90,
                                movable=False,
                                pen=mkPen('k', width=2, style=Qt.SolidLine)
                            )
                            self.plot_widgets[ch].addItem(line)
                            self.trigger_lines.append(line)

                self.needs_refresh[ch] = False

            if any(self.needs_refresh):
                logging.debug(f"Refreshed plots: {self.fifo_window_samples} samples, window={self.window_seconds}s")
                if self.console:
                    self.console.append_to_console(
                        f"Time View ({self.model_name}): Refreshed {self.num_plots} plots with {self.fifo_window_samples} samples, window={self.window_seconds}s"
                    )
        except Exception as e:
            self.log_and_set_status(f"Error refreshing plots: {str(e)}")

    def mouse_enter(self, idx):
        """Called when mouse enters plot idx viewport."""
        self.active_line_idx = idx
        self.vlines[idx].setVisible(True)
        logging.debug(f"Mouse entered plot {idx}")

    def mouse_leave(self, idx):
        """Called when mouse leaves plot idx viewport."""
        self.active_line_idx = None
        for vline in self.vlines:
            vline.setVisible(False)
        logging.debug(f"Mouse left plot {idx}")

    def mouse_moved(self, evt, idx):
        """Update vertical lines on mouse move."""
        if self.active_line_idx is None:
            return

        pos = evt[0]
        if not self.plot_widgets[idx].sceneBoundingRect().contains(pos):
            return

        mouse_point = self.plot_widgets[idx].plotItem.vb.mapSceneToView(pos)
        x = mouse_point.x()

        times = self.fifo_times[idx]
        if len(times) > 0:
            if x < times[0]:
                x = times[0]
            elif x > times[-1]:
                x = times[-1]

        for vline in self.vlines:
            vline.setPos(x)
            vline.setVisible(True)

    def log_and_set_status(self, message):
        """Log a message and append to console if available."""
        logging.error(message)
        if self.console:
            self.console.append_to_console(message)

    def close(self):
        """Clean up resources."""
        if self.refresh_timer:
            self.refresh_timer.stop()