from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

class CenterLineFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.channel = channel
        self.model_name = model_name
        self.console = console
        self.widget = None
        self.figure = None
        self.canvas = None
        self.ax = None
        self.scaling_factor = 3.3 / 65535.0  # Scaling factor for voltage conversion
        self.sample_rate = 4096  # Default sample rate from publish.py
        self.initUI()

    def initUI(self):
        self.widget = QWidget()
        layout = QVBoxLayout()
        self.widget.setLayout(layout)

        label = QLabel(f"Centerline Plot for Model: {self.model_name}, Channel: {self.channel}")
        layout.addWidget(label)

        # Matplotlib figure and canvas setup
        self.figure = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        layout.addWidget(self.canvas)

        # Console messages
        if not self.model_name and self.console:
            self.console.append_to_console("No model selected in CenterLineFeature.")
        if self.channel is None and self.console:
            self.console.append_to_console("No channel selected in CenterLineFeature.")

    def get_widget(self):
        return self.widget

    def on_data_received(self, tag_name, model_name, values, sample_rate):
        if self.model_name != model_name:
            if self.console:
                self.console.append_to_console(f"Ignoring data for model {model_name}, expected {self.model_name}")
            return  # Ignore data for other models

        if self.console:
            self.console.append_to_console(
                f"Centerline View ({self.model_name} - {self.channel}): Received data for {tag_name} - {len(values)} channels"
            )

        # Validate inputs
        if self.channel is None or not isinstance(self.channel, int):
            if self.console:
                self.console.append_to_console(f"Invalid channel index: {self.channel}")
            return
        if not values or self.channel >= len(values) or not values[self.channel]:
            if self.console:
                self.console.append_to_console(f"No valid data for channel {self.channel}")
            return
        if not isinstance(sample_rate, (int, float)) or sample_rate <= 0:
            if self.console:
                self.console.append_to_console(f"Invalid sample rate: {sample_rate}, using default {self.sample_rate}")
            sample_rate = self.sample_rate

        try:
            # Extract the specified channel's data
            channel_data = values[self.channel]

            # Convert to voltage
            voltage_data = [(v - 32768) * self.scaling_factor for v in channel_data]

            # Calculate centerline (mean)
            mean = np.mean(voltage_data)

            # Calculate standard deviation for UCL/LCL
            std = np.std(voltage_data)
            ucl = mean + 3 * std
            lcl = mean - 3 * std

            # Generate time axis
            time = np.arange(len(voltage_data)) / sample_rate

            # Plot the data
            self.ax.clear()
            self.ax.plot(time, voltage_data, label=f"Channel {self.channel} ({tag_name})", color='blue')
            self.ax.axhline(y=mean, color='green', linestyle='--', label=f'Centerline (Mean = {mean:.2f} V)')
            self.ax.axhline(y=ucl, color='red', linestyle='--', label=f'UCL = {ucl:.2f} V')
            self.ax.axhline(y=lcl, color='red', linestyle='--', label=f'LCL = {lcl:.2f} V')
            self.ax.set_title(f"Centerline Control Chart - Model: {self.model_name}, Channel: {self.channel}")
            self.ax.set_xlabel("Time (s)")
            self.ax.set_ylabel("Voltage (V)")
            self.ax.legend()
            self.ax.grid(True)

            # Ensure the canvas is updated
            self.canvas.draw()
            self.canvas.flush_events()

            if self.console:
                self.console.append_to_console(
                    f"Plotted channel {self.channel}: Mean={mean:.2f} V, UCL={ucl:.2f} V, LCL={lcl:.2f} V"
                )

        except Exception as e:
            if self.console:
                self.console.append_to_console(f"Error plotting data: {str(e)}")
            return