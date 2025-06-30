from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QSplitter
from PyQt5.QtCore import Qt
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from datetime import datetime

class TabularViewFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.channel = channel
        self.model_name = model_name
        self.console = console
        self.widget = None
        self.data = None
        self.sample_rate = 4096  # Default sample rate, matching mqtthandler.py
        self.initUI()

    def initUI(self):
        self.widget = QWidget()
        layout = QVBoxLayout()
        self.widget.setLayout(layout)

        # Create splitter for table and plots
        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter)

        # Table setup
        self.table = QTableWidget()
        self.table.setRowCount(1)
        self.table.setColumnCount(14)
        headers = [
            "RPM", "Gap", "Channel Name", "Date Time", "Direct", "1x Amp", "1x Phase",
            "2x Amp", "2x Phase", "nx Amp", "nx Phase", "Vpp", "Vrms", "Twiddle Factor"
        ]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setFixedHeight(100)
        splitter.addWidget(self.table)

        # Plot setup
        self.figure, (self.ax_wave, self.ax_sin, self.ax_cos) = plt.subplots(3, 1, figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        splitter.addWidget(self.canvas)

        # Adjust splitter sizes
        splitter.setSizes([100, 400])

        if not self.model_name and self.console:
            self.console.append_to_console("No model selected in TabularViewFeature.")
        if not self.channel and self.console:
            self.console.append_to_console("No channel selected in TabularViewFeature.")

    def get_widget(self):
        return self.widget

    def calculate_metrics(self, channel_data, tacho_trigger_data):
        metrics = {
            "rpm": 0, "gap": 0, "direct": 0, "one_xa": 0, "one_xp": 0,
            "two_xa": 0, "two_xp": 0, "nx_amp": 0, "nx_phase": 0,
            "vpp": 0, "vrms": 0, "twiddle_factor": 0
        }

        expected_samples = 4096  # As per mqtthandler.py
        if len(channel_data) != expected_samples or len(tacho_trigger_data) != expected_samples:
            if self.console:
                self.console.append_to_console(
                    f"Invalid data length: channel_data={len(channel_data)}, "
                    f"tacho_trigger_data={len(tacho_trigger_data)}, expected={expected_samples}"
                )
            return metrics

        # Basic calculations
        metrics["vpp"] = float(np.max(channel_data) - np.min(channel_data))
        metrics["vrms"] = float(np.sqrt(np.mean(np.square(channel_data))))
        metrics["direct"] = float(np.mean(channel_data))

        # Trigger detection
        threshold = np.mean(tacho_trigger_data) + 0.5 * np.std(tacho_trigger_data)
        trigger_indices = np.where(np.diff((tacho_trigger_data > threshold).astype(int)) > 0)[0]
        
        # RPM calculation
        if len(trigger_indices) >= 2:
            samples_per_rotation = np.mean(np.diff(trigger_indices))
            if samples_per_rotation > 0:
                metrics["rpm"] = (60 * self.sample_rate) / samples_per_rotation
            else:
                if self.console:
                    self.console.append_to_console("Invalid samples per rotation for RPM.")
        else:
            if self.console:
                self.console.append_to_console("Insufficient trigger points for RPM.")

        # Gap calculation
        metrics["gap"] = float(np.mean(tacho_trigger_data))

        # FFT for 1x, 2x, nx
        n = len(channel_data)
        fft_vals = np.fft.fft(channel_data)
        freqs = np.fft.fftfreq(n, 1/self.sample_rate)
        positive_freqs = freqs[:n//2]
        fft_mags = np.abs(fft_vals)[:n//2] * 2 / n
        fft_phases = np.angle(fft_vals)[:n//2]

        fundamental_freq = metrics["rpm"] / 60 if metrics["rpm"] > 0 else 1
        idx_1x = np.argmin(np.abs(positive_freqs - fundamental_freq))
        idx_2x = np.argmin(np.abs(positive_freqs - 2 * fundamental_freq))

        if idx_1x < len(fft_mags):
            metrics["one_xa"] = float(fft_mags[idx_1x])
            metrics["one_xp"] = float(fft_phases[idx_1x])
        if idx_2x < len(fft_mags):
            metrics["two_xa"] = float(fft_mags[idx_2x])
            metrics["two_xp"] = float(fft_phases[idx_2x])

        # nx amplitude and phase
        if len(fft_mags) > 3:
            nx_idx = np.argmax(fft_mags[3:]) + 3
            metrics["nx_amp"] = float(fft_mags[nx_idx]) if nx_idx < len(fft_mags) else 0
            metrics["nx_phase"] = float(fft_phases[nx_idx]) if nx_idx < len(fft_phases) else 0

        # Twiddle factor (use only valid trigger indices)
        valid_trigger_indices = trigger_indices[trigger_indices < len(fft_phases)]
        if len(valid_trigger_indices) >= 2:
            phase_diffs = np.diff(fft_phases[valid_trigger_indices])
            metrics["twiddle_factor"] = float(np.std(phase_diffs)) if len(phase_diffs) > 0 else 0
        else:
            if self.console:
                self.console.append_to_console("Insufficient valid trigger indices for twiddle factor.")

        return metrics

    def update_plots(self, channel_data, tacho_trigger_data):
        self.ax_wave.clear()
        self.ax_sin.clear()
        self.ax_cos.clear()

        expected_samples = 4096
        if len(channel_data) != expected_samples:
            if self.console:
                self.console.append_to_console(f"No valid channel data for plotting: length={len(channel_data)}")
            self.canvas.draw()
            return

        # Time axis
        t = np.arange(len(channel_data)) / self.sample_rate

        # Waveform plot
        self.ax_wave.plot(t, channel_data, label="Channel 1 Waveform")
        self.ax_wave.set_title("Waveform")
        self.ax_wave.set_xlabel("Time (s)")
        self.ax_wave.set_ylabel("Amplitude")
        self.ax_wave.legend()
        self.ax_wave.grid(True)

        # Sin and Cos plots
        if len(tacho_trigger_data) == expected_samples:
            threshold = np.mean(tacho_trigger_data) + 0.5 * np.std(tacho_trigger_data)
            trigger_indices = np.where(np.diff((tacho_trigger_data > threshold).astype(int)) > 0)[0]
            if len(trigger_indices) >= 2:
                samples_per_rotation = np.mean(np.diff(trigger_indices))
                if samples_per_rotation > 0:
                    omega = 2 * np.pi * self.sample_rate / samples_per_rotation
                    phase = omega * t
                    self.ax_sin.plot(t, np.sin(phase), label="sin(θ)")
                    self.ax_cos.plot(t, np.cos(phase), label="cos(θ)")
                    self.ax_sin.set_title("sin(θ)")
                    self.ax_cos.set_title("cos(θ)")
                    self.ax_sin.set_xlabel("Time (s)")
                    self.ax_cos.set_xlabel("Time (s)")
                    self.ax_sin.set_ylabel("Amplitude")
                    self.ax_cos.set_ylabel("Amplitude")
                    self.ax_sin.legend()
                    self.ax_cos.legend()
                    self.ax_sin.grid(True)
                    self.ax_cos.grid(True)
                else:
                    if self.console:
                        self.console.append_to_console("Invalid samples per rotation for phase plots.")
            else:
                if self.console:
                    self.console.append_to_console("Insufficient trigger points for phase plots.")
        else:
            if self.console:
                self.console.append_to_console(f"No valid tacho data for plotting: length={len(tacho_trigger_data)}")

        plt.tight_layout()
        self.canvas.draw()

    def on_data_received(self, tag_name, model_name, values, sample_rate):
        if self.model_name != model_name:
            return
        if self.console:
            self.console.append_to_console(
                f"Tabular View ({self.model_name} - {self.channel}): Received data for {tag_name} - {len(values)} channels"
            )

        if not values or len(values) < 2:
            if self.console:
                self.console.append_to_console("Insufficient data channels received.")
            return

        self.sample_rate = sample_rate
        self.data = values

        # Extract channel 1 and tacho_trigger_data (last channel)
        channel_data = np.array(values[0], dtype=float)
        tacho_trigger_data = np.array(values[-1], dtype=float)

        # Calculate metrics
        metrics = self.calculate_metrics(channel_data, tacho_trigger_data)

        # Update table
        for col, (key, value) in enumerate([
            (0, f"{metrics['rpm']:.2f}"), (1, f"{metrics['gap']:.2f}"),
            (2, self.channel or "N/A"), (3, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            (4, f"{metrics['direct']:.2f}"), (5, f"{metrics['one_xa']:.2f}"),
            (6, f"{metrics['one_xp']:.2f}"), (7, f"{metrics['two_xa']:.2f}"),
            (8, f"{metrics['two_xp']:.2f}"), (9, f"{metrics['nx_amp']:.2f}"),
            (10, f"{metrics['nx_phase']:.2f}"), (11, f"{metrics['vpp']:.2f}"),
            (12, f"{metrics['vrms']:.2f}"), (13, f"{metrics['twiddle_factor']:.2f}")
        ]):
            self.table.setItem(0, col, QTableWidgetItem(value))

        # Update plots
        self.update_plots(channel_data, tacho_trigger_data)