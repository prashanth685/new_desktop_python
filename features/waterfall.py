from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import math

class WaterfallFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.channel = channel
        self.model_name = model_name
        self.console = console
        self.widget = None

        # Waterfall specific attributes
        self.max_lines = 50  # Max number of lines in the waterfall
        self.data_history = [[] for _ in range(4)]  # Holds previous FFT magnitude lines for 4 main channels
        self.phase_history = [[] for _ in range(4)]  # Holds previous FFT phase lines for 4 main channels
        self.scaling_factor = 3.3 / 65535.0  # Scaling factor for voltage conversion
        self.sample_rate = 4096  # Matches MQTTHandler default
        self.samples_per_channel = 4096  # Matches MQTTHandler

        self.initUI()

    def initUI(self):
        self.widget = QWidget()
        layout = QVBoxLayout()
        self.widget.setLayout(layout)

        label = QLabel(f"FFT Waterfall Plot for Model: {self.model_name}, Channels: 1-4")
        layout.addWidget(label)

        # Matplotlib figure
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111, projection='3d')  # 3D for waterfall
        layout.addWidget(self.canvas)

        if not self.model_name and self.console:
            self.console.append_to_console("No model selected in FFTViewFeature.")
        if not self.channel and self.console:
            self.console.append_to_console("No channel selected in FFTViewFeature.")

    def get_widget(self):
        return self.widget

    def on_data_received(self, tag_name, model_name, values, sample_rate):
        if self.model_name != model_name:
            return  # Ignore data for other models
        if self.console:
            self.console.append_to_console(
                f"FFT View ({self.model_name} - Channels 1-4): Received data for {tag_name} - {len(values)} channels, sample_rate={sample_rate}"
            )

        # Update sample rate from MQTT data
        self.sample_rate = sample_rate if sample_rate > 0 else self.sample_rate

        # Expecting values to contain at least 4 lists: 4 main channels (ignore tacho freq and trigger)
        if len(values) < 4:
            if self.console:
                self.console.append_to_console(f"Insufficient channels received: {len(values)}")
            return

        channel_data = values[:4]  # First 4 lists are main channel data

        # Verify data length
        for ch_data in channel_data:
            if len(ch_data) != self.samples_per_channel:
                if self.console:
                    self.console.append_to_console(f"Invalid channel data length: got {len(ch_data)}, expected {self.samples_per_channel}")
                return

        # Apply scaling factor to channel data (convert ADC counts to volts)
        channel_data = [np.array(ch) * self.scaling_factor for ch in channel_data]

        # Calculate target length (next power of 2)
        sample_count = self.samples_per_channel
        target_length = 2 ** math.ceil(math.log2(sample_count))

        fft_magnitudes = []
        fft_phases = []
        frequencies = []

        for i in range(4):
            # Zero-pad data if necessary
            padded_data = np.pad(channel_data[i], (0, target_length - sample_count), mode='constant') if target_length > sample_count else channel_data[i]

            # Compute FFT
            fft_result = np.fft.fft(padded_data)
            N = len(padded_data)

            # Single-sided FFT magnitude scaled for correct amplitude peak
            fft_magnitude = (2.0 / N) * np.abs(fft_result[:N // 2])
            fft_magnitude[0] /= 2  # DC component no doubling
            if N % 2 == 0:
                fft_magnitude[-1] /= 2  # Nyquist component no doubling if even length

            fft_phase = np.angle(fft_result[:N // 2], deg=True)
            freqs = np.array([j * self.sample_rate / N for j in range(N // 2)])

            fft_magnitudes.append(fft_magnitude)
            fft_phases.append(fft_phase)
            frequencies.append(freqs)

        # Store FFT data in history
        for ch in range(4):
            self.data_history[ch].append(fft_magnitudes[ch])
            self.phase_history[ch].append(fft_phases[ch])  # Store phases (not plotted)
            if len(self.data_history[ch]) > self.max_lines:
                self.data_history[ch].pop(0)
                self.phase_history[ch].pop(0)  # Keep phase history in sync

        self.update_waterfall_plot(frequencies[0])  # All channels use same frequency bins

    def update_waterfall_plot(self, frequencies):
        self.ax.clear()
        self.ax.set_title(f"Waterfall FFT Plot (4 Channels, Model: {self.model_name})")
        self.ax.set_xlabel("Frequency (Hz)")
        self.ax.set_ylabel("Time (Older to Newer)")
        self.ax.set_zlabel("Amplitude (V)")
        self.ax.grid(True)

        colors = ['blue', 'red', 'green', 'purple']

        for ch in range(4):
            num_lines = len(self.data_history[ch])
            for idx, fft_line in enumerate(self.data_history[ch]):
                x = frequencies
                y = np.full_like(x, idx + ch * (self.max_lines + 2))  # Offset channels vertically
                z = fft_line
                self.ax.plot(x, y, z, color=colors[ch], label=f'Channel {ch+1}' if idx == 0 else None)

        self.ax.legend(loc='upper right')
        self.figure.tight_layout()

        # Set 3D view angle (elevation 20°, azimuth -45°)
        self.ax.view_init(elev=20, azim=-45)

        self.canvas.draw()
