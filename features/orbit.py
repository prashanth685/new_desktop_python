from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class OrbitFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.channel = channel
        self.model_name = model_name
        self.console = console  # Store the console instance
        self.widget = None
        self.selected_channel = channel if channel in [1, 2, 3, 4] else 1  # Default to channel 1 if invalid
        self.initUI()

    def initUI(self):
        self.widget = QWidget()
        layout = QVBoxLayout()
        self.widget.setLayout(layout)

        # Label for FFT View
        label = QLabel(f"FFT View for Model: {self.model_name}, Channel: {self.selected_channel}")
        layout.addWidget(label)

        # Channel selection dropdown
        self.channel_combo = QComboBox()
        self.channel_combo.addItems(["Channel 1", "Channel 2", "Channel 3", "Channel 4"])
        self.channel_combo.setCurrentIndex(self.selected_channel - 1)  # Set default channel
        self.channel_combo.currentIndexChanged.connect(self.on_channel_changed)
        layout.addWidget(self.channel_combo)

        # Matplotlib canvas for FFT plot
        self.figure = Figure(figsize=(5, 4))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title(f"FFT Plot - Channel {self.selected_channel}")
        self.ax.set_xlabel("Frequency (Hz)")
        self.ax.set_ylabel("Amplitude")
        self.ax.grid(True)

        if not self.model_name and self.console:
            self.console.append_to_console("No model selected in FFTViewFeature.")
        if not self.channel and self.console:
            self.console.append_to_console("No channel selected in FFTViewFeature.")

    def on_channel_changed(self, index):
        """Handle channel selection change."""
        self.selected_channel = index + 1
        self.ax.set_title(f"FFT Plot - Channel {self.selected_channel}")
        self.canvas.draw()
        if self.console:
            self.console.append_to_console(f"Selected Channel {self.selected_channel} for FFT View.")

    def calculate_fft(self, data, sample_rate):
        """Calculate FFT for the given data."""
        n = len(data)
        fft_data = np.fft.fft(data)
        freqs = np.fft.fftfreq(n, 1/sample_rate)
        # Take only positive frequencies
        positive_freqs = freqs[:n//2]
        fft_magnitude = np.abs(fft_data)[:n//2] / n  # Normalize amplitude
        return positive_freqs, fft_magnitude

    def on_data_received(self, tag_name, model_name, values, sample_rate):
        """Handle incoming data and update FFT plot."""
        if self.model_name != model_name:
            return  # Ignore data for other models

        if self.console:
            self.console.append_to_console(
                f"FFT View ({self.model_name} - Channel {self.selected_channel}): "
                f"Received data for {tag_name} - {len(values)} channels"
            )

        # Ensure we have valid channel data
        if not values or len(values) < self.selected_channel:
            if self.console:
                self.console.append_to_console(f"No data for Channel {self.selected_channel}")
            return

        # Extract data for the selected channel (0-based index for list)
        channel_data = values[self.selected_channel - 1]

        # Calculate FFT
        freqs, fft_magnitude = self.calculate_fft(channel_data, sample_rate)

        # Update plot
        self.ax.clear()
        self.ax.plot(freqs, fft_magnitude, 'b-')
        self.ax.set_title(f"FFT Plot - Channel {self.selected_channel}")
        self.ax.set_xlabel("Frequency (Hz)")
        self.ax.set_ylabel("Amplitude")
        self.ax.grid(True)
        self.figure.tight_layout()
        self.canvas.draw()

    def get_widget(self):
        return self.widget