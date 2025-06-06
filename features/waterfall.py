import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from pyqtgraph.opengl import GLViewWidget, GLLinePlotItem
import pyqtgraph as pg
from scipy.fft import fft
from collections import deque

class WaterfallFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.channel = channel
        self.model_name = model_name
        self.console = console
        self.widget = None
        self.sample_rate = 4096  # Default sample rate
        self.max_lines = 50  # Number of spectra to display in waterfall
        self.fft_data = [deque(maxlen=self.max_lines) for _ in range(4)]  # Store FFT data for 4 channels
        self.freqs = None
        self.initUI()

    def initUI(self):
        self.widget = QWidget()
        layout = QVBoxLayout()
        self.widget.setLayout(layout)

        # Create pyqtgraph 3D view
        self.gl_view = GLViewWidget()
        layout.addWidget(self.gl_view)

        # Add grid and axes for better visualization
        grid = pg.opengl.GLGridItem()
        self.gl_view.addItem(grid)

        # Initialize lines for each channel
        self.lines = [[] for _ in range(4)]
        self.channel_colors = [
            pg.glColor('r'),  # Red
            pg.glColor('g'),  # Green
            pg.glColor('b'),  # Blue
            pg.glColor('c'),  # Cyan
        ]

        # Set initial view parameters
        self.gl_view.setCameraPosition(distance=50, elevation=30, azimuth=-60)
        self.gl_view.setWindowTitle(f'FFT Waterfall Plot for Model: {self.model_name}')

        # Add axis labels (using text items)
        self.add_axis_labels()

        if not self.model_name and self.console:
            self.console.append_to_console("No model selected in FFTViewFeature.")
        if not self.channel and self.console:
            self.console.append_to_console("No channel selected in FFTViewFeature.")

    def add_axis_labels(self):
        # Add text labels for axes
        x_label = pg.opengl.GLTextItem(pos=(10, 0, 0), text="Frequency (Hz)", color=(255, 255, 255, 255))
        y_label = pg.opengl.GLTextItem(pos=(0, 10, 0), text="Time (Spectra)", color=(255, 255, 255, 255))
        z_label = pg.opengl.GLTextItem(pos=(0, 0, 2), text="Magnitude", color=(255, 255, 255, 255))
        self.gl_view.addItem(x_label)
        self.gl_view.addItem(y_label)
        self.gl_view.addItem(z_label)

    def get_widget(self):
        return self.widget

    def on_data_received(self, tag_name, model_name, values, sample_rate):
        if self.model_name != model_name:
            return  # Ignore data for other models
        if self.console:
            self.console.append_to_console(f"FFT View ({self.model_name} - {self.channel}): Received data for {tag_name}")

        # Update sample rate
        self.sample_rate = sample_rate if sample_rate > 0 else 4096

        # Process up to 4 channels
        num_channels = min(len(values), 4)
        scaling_factor = 3.3 / 65535.0  # Convert 16-bit ADC to voltage

        for ch in range(num_channels):
            # Convert raw data to voltage
            data = np.array(values[ch], dtype=np.float32) * scaling_factor
            n = len(data)

            # Calculate FFT
            fft_vals = fft(data)
            normalized_magnitude = np.abs(fft_vals)[:n//2] / n
            self.freqs = np.fft.fftfreq(n, d=1/self.sample_rate)[:n//2]

            # Store FFT data
            self.fft_data[ch].append(normalized_magnitude)

        self.update_plot()

    def update_plot(self):
        # Clear existing lines
        for ch_lines in self.lines:
            for line in ch_lines:
                self.gl_view.removeItem(line)
        self.lines = [[] for _ in range(4)]

        max_y = max(len(d) for d in self.fft_data)

        for ch in range(4):
            if not self.fft_data[ch]:
                continue
            x = self.freqs if self.freqs is not None else np.arange(len(self.fft_data[ch][0]))
            for i, mag in enumerate(self.fft_data[ch]):
                # Create 3D points for the line
                y = np.full_like(x, i)  # Time axis (spectra index)
                z = mag  # Magnitude
                pts = np.vstack([x, y, z]).T
                # Create and add line plot
                line = GLLinePlotItem(pos=pts, color=self.channel_colors[ch], width=2, antialias=True)
                self.gl_view.addItem(line)
                self.lines[ch].append(line)

        # Add legend (using text items for simplicity)
        for ch in range(4):
            if self.fft_data[ch]:
                label = pg.opengl.GLTextItem(
                    pos=(0, max_y + 1, ch * 0.5),
                    text=f'Channel {ch+1}',
                    color=self.channel_colors[ch]
                )
                self.gl_view.addItem(label)