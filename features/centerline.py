from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox
from PyQt5.QtCore import QTimer
import pyqtgraph as pg
import numpy as np
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class CenterLineFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.channel = channel
        self.model_name = model_name
        self.console = console
        self.widget = None
        self.plot_widget = None
        self.plot_item = None
        self.primary_gap_values = []
        self.secondary_gap_values = []
        self.channel_names = []
        self.channel_index = None
        self.secondary_channel_index = None
        self.tag_name = None
        self.main_channels = 0
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_plot)
        self.update_interval = 200  # ms
        self.initUI()
        self.cache_channel_data()
        logging.debug(f"Initialized CenterLineFeature with project_name: {project_name}, model_name: {model_name}, channel: {channel}")

    def initUI(self):
        self.widget = QWidget()
        main_layout = QVBoxLayout()
        self.widget.setLayout(main_layout)

        label = QLabel(f"Centerline Plot for Model: {self.model_name or 'Unknown'}, Channel: {self.channel or 'Unknown'}")
        label.setStyleSheet("color: #ecf0f1; font-size: 16px; padding: 10px;")
        main_layout.addWidget(label)

        # Secondary channel selection
        self.secondary_channel_combo = QComboBox()
        self.secondary_channel_combo.currentIndexChanged.connect(self.secondary_channel_changed)
        main_layout.addWidget(self.secondary_channel_combo)

        # Plot setup using pyqtgraph
        pg.setConfigOptions(antialias=False)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("white")
        self.plot_widget.setTitle("Centerline Plot", color="black", size="12pt")
        self.plot_widget.setLabel('left', 'Secondary Channel Gap', color='#000000')
        self.plot_widget.setLabel('bottom', 'Primary Channel Gap', color='#000000')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_item = self.plot_widget.plot(symbol='o', symbolSize=5, pen=None, symbolPen=pg.mkPen(color='#008000', width=2), name="Gap Data")
        main_layout.addWidget(self.plot_widget)

        self.update_timer.start(self.update_interval)

    def cache_channel_data(self):
        try:
            project_data = self.db.get_project_data(self.project_name)
            if project_data and "models" in project_data and self.model_name in project_data["models"]:
                model = project_data["models"][self.model_name]
                self.channel_names = [ch.get("channel_name") for ch in model.get("channels", [])]
                self.main_channels = len(self.channel_names)
                self.tag_name = model.get("tag_name")
                if not self.tag_name:
                    logging.error("TagName is empty for model")
                    if self.console:
                        self.console.append_to_console("TagName not found for selected model.")
                    return

                # Find primary channel index
                self.channel_index = next((i for i, ch in enumerate(model.get("channels", [])) 
                                         if ch.get("channel_name") == self.channel), -1)
                if self.channel_index == -1:
                    logging.error(f"Selected channel {self.channel} not found in model {self.model_name}")
                    if self.console:
                        self.console.append_to_console(f"Selected channel {self.channel} not found.")
                    return

                # Populate secondary channel combo box
                for channel_name in self.channel_names:
                    if channel_name != self.channel:
                        self.secondary_channel_combo.addItem(channel_name)

                # Set default secondary channel
                default_secondary_index = (self.channel_index + 1) % self.main_channels
                if default_secondary_index == self.channel_index:
                    default_secondary_index = (default_secondary_index + 1) % self.main_channels
                if default_secondary_index < len(self.channel_names):
                    self.secondary_channel_combo.setCurrentIndex(default_secondary_index)
                    self.secondary_channel_index = default_secondary_index
                elif self.secondary_channel_combo.count() > 0:
                    self.secondary_channel_combo.setCurrentIndex(0)
                    self.secondary_channel_index = self.channel_names.index(self.secondary_channel_combo.currentText())

                logging.debug(f"Channel {self.channel} index: {self.channel_index}, TagName: {self.tag_name}, Secondary channel: {self.secondary_channel_combo.currentText()}")
            else:
                logging.error(f"Project {self.project_name} or model {self.model_name} not found")
                if self.console:
                    self.console.append_to_console("Project or model not found.")
        except Exception as e:
            logging.error(f"Error caching channel data: {e}")
            if self.console:
                self.console.append_to_console(f"Error caching channel data: {e}")

    def get_widget(self):
        return self.widget

    def on_data_received(self, tag_name, model_name, values, sample_rate):
        if self.model_name != model_name:
            logging.debug(f"Ignoring data for model {model_name}, expected {self.model_name}")
            if self.console:
                self.console.append_to_console(f"Ignoring data for model {model_name}, expected {self.model_name}")
            return

        if self.channel is None or self.tag_name != tag_name:
            logging.debug(f"Ignoring data for tag {tag_name}, expected {self.tag_name}")
            if self.console:
                self.console.append_to_console(f"Ignoring data for tag {tag_name}, expected {self.tag_name}")
            return

        try:
            if len(values) < 200:  # Minimum 100 ushort values (200 bytes) for header
                logging.warning("Received invalid MQTT payload: too short.")
                if self.console:
                    self.console.append_to_console("Received invalid MQTT payload: too short.")
                return

            # Parse header (100 ushort values)
            header = np.frombuffer(values[:200], dtype=np.uint16)
            logging.debug(f"Header values [10-13]: {header[10:14].tolist()}")

            main_channels = header[2]
            if main_channels != self.main_channels:
                logging.warning(f"Mismatch in channel count: expected {self.main_channels}, got {main_channels}")
                if self.console:
                    self.console.append_to_console(f"Mismatch in channel count: expected {self.main_channels}, got {main_channels}")
                return

            # Get primary and secondary gap values
            primary_gap = float(header[10 + self.channel_index])
            secondary_gap = float(header[10 + self.secondary_channel_index])

            # Validate gap values
            if primary_gap > 1000 or secondary_gap > 1000:
                logging.warning(f"Ignoring unreasonable gap values - Primary ({self.channel_names[self.channel_index]}): {primary_gap}, Secondary ({self.channel_names[self.secondary_channel_index]}): {secondary_gap}")
                if self.console:
                    self.console.append_to_console(f"Ignoring unreasonable gap values - Primary: {primary_gap}, Secondary: {secondary_gap}")
                return

            # Append gap values
            self.primary_gap_values.append(primary_gap)
            self.secondary_gap_values.append(secondary_gap)

            logging.debug(f"Received data for {tag_name}: Primary Gap ({self.channel_names[self.channel_index]}): {primary_gap}, Secondary Gap ({self.channel_names[self.secondary_channel_index]}): {secondary_gap}")
            if self.console:
                self.console.append_to_console(f"Received: Primary Gap ({self.channel_names[self.channel_index]}): {primary_gap}, Secondary Gap ({self.channel_names[self.secondary_channel_index]}): {secondary_gap}")

        except Exception as e:
            logging.error(f"Error in on_data_received: {e}")
            if self.console:
                self.console.append_to_console(f"Error in Centerline View: {e}")

    def update_plot(self):
        try:
            if not self.primary_gap_values or not self.secondary_gap_values:
                return

            # Update the scatter plot
            self.plot_item.setData(self.primary_gap_values, self.secondary_gap_values)
            self.plot_widget.setTitle(f"{self.channel_names[self.channel_index]} vs {self.channel_names[self.secondary_channel_index]}")
            self.plot_widget.setLabel('bottom', f"{self.channel_names[self.channel_index]} Gap")
            self.plot_widget.setLabel('left', f"{self.channel_names[self.secondary_channel_index]} Gap")
            self.plot_widget.getPlotItem().autoRange()

            logging.debug(f"Updated plot with {len(self.primary_gap_values)} points: Primary Gaps = {self.primary_gap_values[:5]}, Secondary Gaps = {self.secondary_gap_values[:5]}")
            if self.console:
                self.console.append_to_console(f"Updated plot with {len(self.primary_gap_values)} points")
        except Exception as e:
            logging.error(f"Error updating Centerline plot: {e}")
            if self.console:
                self.console.append_to_console(f"Error updating Centerline plot: {e}")

    def secondary_channel_changed(self):
        try:
            selected_channel = self.secondary_channel_combo.currentText()
            self.secondary_channel_index = self.channel_names.index(selected_channel)
            self.primary_gap_values.clear()
            self.secondary_gap_values.clear()
            self.plot_item.clear()
            logging.debug(f"Secondary channel changed to {selected_channel}. Plot data reset.")
            if self.console:
                self.console.append_to_console(f"Secondary channel changed to {selected_channel}. Plot data reset.")
        except Exception as e:
            logging.error(f"Error changing secondary channel: {e}")
            if self.console:
                self.console.append_to_console(f"Error changing secondary channel: {e}")

    def close(self):
        self.update_timer.stop()