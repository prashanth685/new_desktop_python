from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import QTimer
import pyqtgraph as pg
import numpy as np
import logging
from scipy.fft import fft
import time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class FFTViewFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None, layout="vertical"):
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
        self.sample_rate = 1000  # Hz
        self.channel_index = None
        self.latest_data = None
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_plot)
        self.update_interval = 200  # ms
        self.max_samples = 4096
        self.layout_type = layout
        self.initUI()
        self.cache_channel_index()

    def initUI(self):
        self.widget = QWidget()
        main_layout = QVBoxLayout()
        self.widget.setLayout(main_layout)

        # label = QLabel(f"FFT View for Model: {self.model_name or 'Unknown'}, Channel: {self.channel or 'Unknown'}")
        # label.setStyleSheet("color: #ecf0f1; font-size: 16px; padding: 10px;")
        # main_layout.addWidget(label)

        plot_layout = QHBoxLayout() if self.layout_type == "horizontal" else QVBoxLayout()
        pg.setConfigOptions(antialias=False)

        # Magnitude Plot
        self.magnitude_plot_widget = pg.PlotWidget()
        self.magnitude_plot_widget.setBackground("white")
        self.magnitude_plot_widget.setTitle("Magnitude Spectrum", color="black", size="12pt")
        self.magnitude_plot_widget.setLabel('left', 'Amplitude', color='#000000')
        self.magnitude_plot_widget.setLabel('bottom', 'Frequency (Hz)', color='#000000')
        self.magnitude_plot_widget.showGrid(x=True, y=True)
        self.magnitude_plot_item = self.magnitude_plot_widget.plot(pen=pg.mkPen(color='#4a90e2', width=2))
        plot_layout.addWidget(self.magnitude_plot_widget)

        # Phase Plot
        self.phase_plot_widget = pg.PlotWidget()
        self.phase_plot_widget.setBackground("white")
        self.phase_plot_widget.setTitle("Phase Spectrum", color="black", size="12pt")
        self.phase_plot_widget.setLabel('left', 'Phase', color='#000000')
        self.phase_plot_widget.setLabel('bottom', 'Frequency (Hz)', color='#000000')
        self.phase_plot_widget.showGrid(x=True, y=True)
        self.phase_plot_item = self.phase_plot_widget.plot(pen=pg.mkPen(color='#e74c3c', width=2))
        plot_layout.addWidget(self.phase_plot_widget)

        main_layout.addLayout(plot_layout)
        self.update_timer.start(self.update_interval)

    def cache_channel_index(self):
        try:
            project_data = self.db.get_project_data(self.project_name)
            if project_data and "models" in project_data and self.model_name in project_data["models"]:
                channels = project_data["models"][self.model_name].get("channels", [])
                for idx, ch in enumerate(channels):
                    if ch.get("tag_name") == self.channel or ch.get("channel_name") == self.channel:
                        self.channel_index = idx
                        return
        except Exception as e:
            logging.error(f"Error caching channel index: {e}")
            if self.console:
                self.console.append_to_console(f"Error caching channel index: {e}")

    def get_widget(self):
        return self.widget

    def on_data_received(self, tag_name, model_name, values, sample_rate):
        if self.model_name != model_name or not values or self.channel_index is None:
            return

        try:
            if self.channel_index >= len(values):
                return

            self.sample_rate = sample_rate if sample_rate > 0 else 1000
            scaling_factor = 3.3 / 65535.0
            raw_data = np.array(values[self.channel_index][:self.max_samples], dtype=np.float32)
            self.latest_data = raw_data * scaling_factor
        except Exception as e:
            logging.error(f"Error in on_data_received: {e}")
            if self.console:
                self.console.append_to_console(f"Error in FFT View: {e}")

    def update_plot(self):
        if self.latest_data is None:
            return

        try:
            data = self.latest_data
            n = len(data)
            if n < 2:
                return

            target_length = 2 ** int(np.ceil(np.log2(n)))
            padded_data = np.zeros(target_length)
            padded_data[:n] = data

            fft_result = fft(padded_data)
            half = target_length // 2

            frequencies = np.array([i * self.sample_rate / target_length for i in range(half)])
            magnitudes = np.abs(fft_result[:half]) / target_length
            phases = np.degrees(np.angle(fft_result[:half]))

            self.magnitude_plot_item.setData(frequencies, magnitudes)
            self.phase_plot_item.setData(frequencies, phases)

            if self.console:
                self.console.append_to_console(
                    f"FFT Updated: Samples={n}, FFT Size={target_length}, Fs={self.sample_rate}Hz"
                )
        except Exception as e:
            logging.error(f"Error updating FFT: {e}")
            if self.console:
                self.console.append_to_console(f"Error updating FFT: {e}")

    def close(self):
        self.update_timer.stop()
