from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import QTimer
import pyqtgraph as pg
import numpy as np
import logging
from scipy.fft import fft, fftfreq
import time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class FFTViewFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None, layout="horizontal"):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.channel = channel
        self.model_name = model_name
        self.console = console
        self.widget = None
        self.magnitude_plot_widget = None
        self.phase_plot_widget = None
        self.magnitude_plot_item = None
        self.phase_plot_item = None
        self.sample_rate = 1000  # Default sample rate
        self.channel_index = None
        self.latest_data = None
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_plot)
        self.last_update = 0
        self.update_interval = 200  # Update every 200ms
        self.max_samples = 4096  # Reduced sample size
        self.layout_type = layout  # "horizontal" or "vertical"
        self.initUI()
        self.cache_channel_index()

    def initUI(self):
        self.widget = QWidget()
        main_layout = QVBoxLayout()
        self.widget.setLayout(main_layout)

        # Title label
        label = QLabel(f"FFT View for Model: {self.model_name or 'Unknown'}, Channel: {self.channel or 'Unknown'}")
        label.setStyleSheet("color: #ecf0f1; font-size: 16px; padding: 10px;")
        main_layout.addWidget(label)

        # Plot layout (horizontal or vertical)
        plot_layout = QHBoxLayout() if self.layout_type == "horizontal" else QVBoxLayout()

        # Magnitude Plot
        pg.setConfigOptions(antialias=False)  # Disable for performance
        self.magnitude_plot_widget = pg.PlotWidget()
        self.magnitude_plot_widget.setBackground("white")
        self.magnitude_plot_widget.setTitle("Magnitude Spectrum", color="black", size="12pt")
        self.magnitude_plot_widget.setLabel('left', 'Amplitude (dB)', color='#ecf0f1')
        self.magnitude_plot_widget.setLabel('bottom', 'Frequency (Hz)', color='#ecf0f1')
        self.magnitude_plot_widget.showGrid(x=True, y=True)
        self.magnitude_plot_item = self.magnitude_plot_widget.plot(pen=pg.mkPen(color='#4a90e2', width=2))
        plot_layout.addWidget(self.magnitude_plot_widget)

        # Phase Plot
        self.phase_plot_widget = pg.PlotWidget()
        self.phase_plot_widget.setBackground("white")
        self.phase_plot_widget.setTitle("Phase Spectrum", color="black", size="12pt")
        self.phase_plot_widget.setLabel('left', 'Phase (radians)', color='#ecf0f1')
        self.phase_plot_widget.setLabel('bottom', 'Frequency (Hz)', color='#ecf0f1')
        self.phase_plot_widget.showGrid(x=True, y=True)
        self.phase_plot_item = self.phase_plot_widget.plot(pen=pg.mkPen(color='#e74c3c', width=2))
        plot_layout.addWidget(self.phase_plot_widget)

        main_layout.addLayout(plot_layout)

        if not self.model_name and self.console:
            self.console.append_to_console("No model selected in FFTViewFeature.")
        if not self.channel and self.console:
            self.console.append_to_console("No channel selected in FFTViewFeature.")

        logging.debug(f"Initialized FFTViewFeature for model: {self.model_name}, channel: {self.channel}, layout: {self.layout_type}")

        # Start update timer
        self.update_timer.start(self.update_interval)

    def cache_channel_index(self):
        try:
            project_data = self.db.get_project_data(self.project_name)
            if project_data and "models" in project_data and self.model_name in project_data["models"]:
                channels = project_data["models"][self.model_name].get("channels", [])
                for idx, ch in enumerate(channels):
                    if ch.get("tag_name") == self.channel or ch.get("channel_name") == self.channel:
                        self.channel_index = idx
                        logging.debug(f"Cached channel index {self.channel_index} for channel {self.channel}")
                        return
            logging.warning(f"Channel {self.channel} not found for model {self.model_name}")
        except Exception as e:
            logging.error(f"Error caching channel index: {str(e)}")
            if self.console:
                self.console.append_to_console(f"Error caching channel index: {str(e)}")

    def get_widget(self):
        return self.widget

    def on_data_received(self, tag_name, model_name, values, sample_rate):
        if self.model_name != model_name:
            logging.debug(f"Ignoring data for model {model_name}, expected {self.model_name}")
            return

        if not values or not isinstance(values, list) or self.channel_index is None:
            logging.warning(f"Invalid data or channel index for {tag_name}: {values}")
            return

        try:
            if self.channel_index >= len(values):
                logging.warning(f"Channel index {self.channel_index} out of range for {tag_name}")
                return

            self.sample_rate = sample_rate if sample_rate > 0 else 1000
            self.latest_data = values[self.channel_index][:self.max_samples]  # Limit data size
            logging.debug(f"Received {len(self.latest_data)} samples for {tag_name}/{self.model_name}/{self.channel}")
        except Exception as e:
            logging.error(f"Error processing data for {tag_name}/{self.model_name}/{self.channel}: {str(e)}")
            if self.console:
                self.console.append_to_console(
                    f"Error in FFT View ({self.model_name} - {self.channel}): {str(e)}"
                )

    def update_plot(self):
        if self.latest_data is None:
            return

        try:
            start_time = time.time()
            data = np.array(self.latest_data, dtype=np.float32)  # Use float32 for efficiency
            n = len(data)
            if n < 2:
                logging.warning(f"Data too short for FFT: {n} samples")
                return

            # Perform FFT using scipy
            fft_vals = fft(data, n=self.max_samples)
            freqs = fftfreq(n, 1/self.sample_rate)[:n//2]

            # Magnitude (in dB)
            fft_magnitude = np.abs(fft_vals)[:n//2]
            fft_magnitude_db = 20 * np.log10(fft_magnitude + 1e-10)  # Convert to dB
            self.magnitude_plot_item.setData(freqs, fft_magnitude_db)

            # Phase (in radians)
            fft_phase = np.angle(fft_vals)[:n//2]
            self.phase_plot_item.setData(freqs, fft_phase)

            elapsed = (time.time() - start_time) * 1000  # ms
            if self.console:
                self.console.append_to_console(
                    f"FFT View ({self.model_name} - {self.channel}): "
                    f"Plotted {n} samples, sample_rate={self.sample_rate} Hz, "
                    f"Magnitude and Phase, Time: {elapsed:.2f}ms"
                )
            logging.debug(
                f"FFT plotted for {self.model_name}/{self.channel}: "
                f"{n} samples, {len(freqs)} frequency bins, Time: {elapsed:.2f}ms"
            )
        except Exception as e:
            logging.error(f"Error updating FFT plots: {str(e)}")
            if self.console:
                self.console.append_to_console(f"Error updating FFT plots: {str(e)}")

    def close(self):
        self.update_timer.stop()
        logging.debug(f"Closed FFTViewFeature for {self.model_name}/{self.channel}")