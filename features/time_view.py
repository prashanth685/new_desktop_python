import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PyQt5.QtCore import QObject, QEvent, Qt
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
        self.data = []
        self.channel_times = []
        self.tacho_times = []
        self.sample_rate = 4096
        self.num_channels = 4
        self.scaling_factor = 3.3 / 65535
        self.num_plots = 6
        self.channel_samples = 4096
        self.tacho_samples = 4096
        self.vlines = []
        self.proxies = []
        self.trackers = []
        self.trigger_lines = []
        self.active_line_idx = None
        self.initUI()
        self.load_project_data()

    def load_project_data(self):
        """Load project data to determine number of channels."""
        try:
            project_data = self.db.get_project_data(self.project_name)
            if project_data and "models" in project_data:
                for model in project_data["models"]:
                    if model.get("name") == self.model_name:
                        available_channels = len(model.get("channels", []))
                        self.num_channels = min(available_channels, 4)
                        logging.debug(f"Loaded project data: {self.num_channels} channels for model {self.model_name}")
                        return
                logging.warning(f"No model data found for {self.model_name}")
                if self.console:
                    self.console.append_to_console(f"No model data for {self.model_name}")
            else:
                logging.warning(f"No valid project data found for {self.project_name}")
                if self.console:
                    self.console.append_to_console(f"No valid project data for {self.project_name}")
        except Exception as e:
            logging.error(f"Error loading project data: {str(e)}")
            if self.console:
                self.console.append_to_console(f"Error loading project data: {str(e)}")

    def initUI(self):
        """Initialize the UI with pyqtgraph subplots."""
        self.widget = QWidget()
        layout = QVBoxLayout()
        
        # Create a scroll area to contain the plots
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
    
        colors = ['r', 'g', 'b', 'y', 'c', 'm']
        for i in range(self.num_plots):
            plot_widget = PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')}, background='w')
            plot_widget.setFixedHeight(250)
            plot_widget.setMinimumWidth(0)
            if i < self.num_channels:
                plot_widget.setLabel('left', f'CH{i+1} Value')
            elif i == self.num_channels:
                plot_widget.setLabel('left', 'Tacho Frequency')
            else:
                plot_widget.setLabel('left', 'Tacho Trigger')
                plot_widget.setYRange(-0.5, 1.5, padding=0)
            plot_widget.showGrid(x=True, y=True)
            plot_widget.addLegend()
            pen = mkPen(color=colors[i % len(colors)], width=2)
            plot = plot_widget.plot([], [], pen=pen)
            self.plots.append(plot)
            self.plot_widgets.append(plot_widget)
            self.data.append([])

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

            scroll_layout.addWidget(plot_widget)

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        self.widget.setLayout(layout)

        if not self.model_name and self.console:
            self.console.append_to_console("No model selected in TimeViewFeature.")
        if not self.channel and self.console:
            self.console.append_to_console("No channel selected in TimeViewFeature.")

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
            logging.error(f"Error refreshing filenames: {str(e)}")
            if self.console:
                self.console.append_to_console(f"Error refreshing filenames: {str(e)}")
            self.filename_counter = 1
            return []

    def start_saving(self):
        """Start saving data to the database."""
        if not self.parent.current_project or not self.model_name:
            logging.error("Cannot start saving: No project or model selected")
            if self.console:
                self.console.append_to_console("Cannot start saving: No project or model selected")
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
        """Handle incoming MQTT data, update plots, and save to database if saving is enabled."""
        logging.debug(f"on_data_received called with tag_name={tag_name}, model_name={model_name}, "
                    f"values_len={len(values) if values else 0}, sample_rate={sample_rate}")
        if self.model_name != model_name:
            logging.debug(f"Ignoring data for model {model_name}, expected {self.model_name}")
            return
        try:
            if not values or len(values) != 6:
                logging.warning(f"Received incorrect number of sublists: {len(values)}, expected 6")
                if self.console:
                    self.console.append_to_console(f"Received incorrect number of sublists: {len(values)}")
                return

            self.sample_rate = sample_rate
            self.channel_samples = 4096
            self.tacho_samples = 4096

            for ch in range(self.num_channels):
                if len(values[ch]) != self.channel_samples:
                    logging.warning(f"Channel {ch+1} has {len(values[ch])} samples, expected {self.channel_samples}")
                    if self.console:
                        self.console.append_to_console(f"Channel {ch+1} sample mismatch: {len(values[ch])}")
                    return

            tacho_freq_samples = len(values[4])
            tacho_trigger_samples = len(values[5])
            if tacho_freq_samples != self.tacho_samples or tacho_trigger_samples != self.tacho_samples:
                logging.warning(f"Tacho data length mismatch: freq={tacho_freq_samples}, trigger={tacho_trigger_samples}, expected={self.tacho_samples}")
                if self.console:
                    self.console.append_to_console(f"Tacho data length mismatch: freq={tacho_freq_samples}, trigger={tacho_trigger_samples}")
                return

            current_time = time.time()
            channel_time_step = 1.0 / sample_rate
            tacho_time_step = 1.0 / sample_rate
            self.channel_times = np.array([current_time - (self.channel_samples - 1) * channel_time_step + i * channel_time_step for i in range(self.channel_samples)])
            self.tacho_times = np.array([current_time - (self.tacho_samples - 1) * tacho_time_step + i * tacho_time_step for i in range(self.tacho_samples)])

            for ch in range(self.num_channels):
                self.data[ch] = np.array(values[ch][:self.channel_samples]) * self.scaling_factor
                logging.debug(f"Channel {ch+1} data: {len(self.data[ch])} samples, scaled with factor {self.scaling_factor}")

            self.data[self.num_channels] = np.array(values[4][:self.tacho_samples]) / 100
            self.data[self.num_channels + 1] = np.array(values[5][:self.tacho_samples])
            logging.debug(f"Tacho freq data: {len(self.data[self.num_channels])} samples")
            logging.debug(f"Tacho trigger data: {len(self.data[self.num_channels + 1])} samples, first 10: {self.data[self.num_channels + 1][:10]}")

            for ch in range(self.num_plots):
                times = self.tacho_times if ch >= self.num_channels else self.channel_times
                if ch < len(self.data) and len(self.data[ch]) > 0 and len(times) > 0:
                    self.plots[ch].setData(times, self.data[ch])
                    self.plot_widgets[ch].setXRange(times[0], times[-1], padding=0)
                    if ch < self.num_channels:
                        self.plot_widgets[ch].enableAutoRange(axis='y')
                    elif ch == self.num_channels:
                        self.plot_widgets[ch].enableAutoRange(axis='y')
                    else:
                        self.plot_widgets[ch].setYRange(0, 1.0, padding=0)
                else:
                    logging.warning(f"No data for plot {ch}, data_len={len(self.data[ch])}, times_len={len(times)}")
                    if self.console:
                        self.console.append_to_console(f"No data for plot {ch}")

            if len(self.data[self.num_channels + 1]) > 0:
                if self.trigger_lines:
                    for line in self.trigger_lines:
                        if line:
                            self.plot_widgets[self.num_plots - 1].removeItem(line)
                self.trigger_lines = []

                trigger_indices = np.where(self.data[self.num_plots - 1] == 1)[0]
                logging.debug(f"Tacho trigger indices (value=1): {len(trigger_indices)} points")
                for idx in trigger_indices:
                    if idx < len(self.tacho_times):
                        line = InfiniteLine(
                            pos=self.tacho_times[idx],
                            angle=90,
                            movable=False,
                            pen=mkPen('k', width=2, style=Qt.SolidLine)
                        )
                        self.plot_widgets[self.num_plots - 1].addItem(line)
                        self.trigger_lines.append(line)

            if self.is_saving:
                try:
                    message_data = {
                        "topic": tag_name,
                        "filename": self.current_filename,
                        "frameIndex": 0,
                        "message": {
                            "channel_data": [list(self.data[i]) for i in range(self.num_channels)],
                            "tacho_freq": list(self.data[self.num_channels]),
                            "tacho_trigger": list(self.data[self.num_channels + 1])
                        },
                        "numberOfChannels": self.num_channels,
                        "samplingRate": self.sample_rate,
                        "samplingSize": self.channel_samples,
                        "messageFrequency": None,
                        "createdAt": datetime.now().isoformat()
                    }
                    success, msg = self.db.save_timeview_message(self.project_name, self.model_name, message_data)
                    if success:
                        logging.info(f"Saved data to database: {self.current_filename}")
                        if self.console:
                            self.console.append_to_console(f"Saved data to {self.current_filename}")
                    else:
                        logging.error(f"Failed to save data: {msg}")
                        if self.console:
                            self.console.append_to_console(f"Failed to save data: {msg}")
                except Exception as e:
                    logging.error(f"Error saving data to database: {str(e)}")
                    if self.console:
                        self.console.append_to_console(f"Error saving data: {str(e)}")

            logging.debug(f"Updated {self.num_plots} plots: {self.channel_samples} channel samples, {self.tacho_samples} tacho samples")
            if self.console:
                self.console.append_to_console(
                    f"Time View ({self.model_name}): Updated {self.num_plots} plots with {self.channel_samples} channel samples, {self.tacho_samples} tacho samples"
                )
        except Exception as e:
            logging.error(f"Error updating plots: {str(e)}")
            if self.console:
                self.console.append_to_console(f"Error updating plots: {str(e)}")

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

        times = self.tacho_times if idx >= self.num_channels else self.channel_times
        if len(times) > 0:
            if x < times[0]:
                x = times[0]
            elif x > times[-1]:
                x = times[-1]

        for vline in self.vlines:
            vline.setPos(x)
            vline.setVisible(True)