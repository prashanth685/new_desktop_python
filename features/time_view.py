import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from pyqtgraph import PlotWidget, mkPen, AxisItem
from datetime import datetime, timedelta
import time
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class TimeAxisItem(AxisItem):
    """Custom axis to display datetime on x-axis."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        """Convert timestamps to formatted strings."""
        return [datetime.fromtimestamp(v).strftime('%H:%M:%S') for v in values]

class TimeViewFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.channel = channel
        self.model_name = model_name
        self.console = console
        self.widget = None
        self.plot_widgets = []
        self.plots = []
        self.data = []
        self.times = []
        self.sample_rate = 4096  # Default, matches MQTTPublisher
        self.num_channels = 4  # Default, updated from project data
        self.initUI()
        self.load_project_data()

    def load_project_data(self):
        """Load project data to determine number of channels."""
        try:
            project_data = self.db.get_project_data(self.project_name)
            if project_data and "models" in project_data and self.model_name in project_data["models"]:
                model_data = project_data["models"][self.model_name]
                self.num_channels = len(model_data.get("channels", []))
                logging.debug(f"Loaded project data: {self.num_channels} channels for model {self.model_name}")
            else:
                logging.warning(f"No valid model data found for {self.model_name}")
                if self.console:
                    self.console.append_to_console(f"No valid model data for {self.model_name}")
        except Exception as e:
            logging.error(f"Error loading project data: {str(e)}")
            if self.console:
                self.console.append_to_console(f"Error loading project data: {str(e)}")

    def initUI(self):
        """Initialize the UI with pyqtgraph subplots."""
        self.widget = QWidget()
        layout = QVBoxLayout()
        self.widget.setLayout(layout)

        layout.addWidget(QLabel(f"Time View for Model: {self.model_name}, Channels: {self.channel or 'All'}"))

        # Create a subplot for each channel
        colors = ['r', 'g', 'b', 'y']
        for i in range(self.num_channels):
            plot_widget = PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})
            plot_widget.setLabel('left', f'CH{i+1} Value')
            plot_widget.setLabel('bottom', 'Time')
            plot_widget.showGrid(x=True, y=True)
            plot_widget.addLegend()
            pen = mkPen(color=colors[i % len(colors)], width=2)
            plot = plot_widget.plot([], [], pen=pen)
            self.plots.append(plot)
            self.plot_widgets.append(plot_widget)
            layout.addWidget(plot_widget)
            self.data.append([])

        if not self.model_name and self.console:
            self.console.append_to_console("No model selected in TimeViewFeature.")
        if not self.channel and self.console:
            self.console.append_to_console("No channel selected in TimeViewFeature.")

    def get_widget(self):
        """Return the widget containing the plots."""
        return self.widget

    def on_data_received(self, tag_name, model_name, values, sample_rate):
        """Handle incoming MQTT data and update the plots."""
        logging.debug(f"on_data_received called with tag_name={tag_name}, model_name={model_name}, "
                     f"values_len={len(values) if values else 0}, sample_rate={sample_rate}")
        if self.model_name != model_name:
            logging.debug(f"Ignoring data for model {model_name}, expected {self.model_name}")
            return
        try:
            self.sample_rate = sample_rate
            num_samples = len(values[0]) if values and len(values) > 0 else 0
            if num_samples == 0:
                logging.warning("Received empty data values")
                if self.console:
                    self.console.append_to_console("Received empty data values")
                return

            # Generate timestamps for the 1-second window
            current_time = time.time()
            time_step = 1.0 / sample_rate
            self.times = np.array([current_time - 1.0 + i * time_step for i in range(num_samples)])

            # Update data for each channel
            for ch in range(min(self.num_channels, len(values))):
                self.data[ch] = np.array(values[ch][:num_samples])

            # Update each subplot
            for ch in range(self.num_channels):
                if ch < len(values) and len(self.data[ch]) > 0:
                    self.plots[ch].setData(self.times, self.data[ch])
                    self.plot_widgets[ch].setXRange(self.times[0], self.times[-1], padding=0)
                    self.plot_widgets[ch].enableAutoRange(axis='y')

            logging.debug(f"Updated plots for {model_name}, {num_samples} samples, {self.num_channels} channels")
            if self.console:
                self.console.append_to_console(
                    f"Time View ({self.model_name}): Updated plots with {num_samples} samples"
                )
        except Exception as e:
            logging.error(f"Error updating plots: {str(e)}")
            if self.console:
                self.console.append_to_console(f"Error updating plots: {str(e)}")