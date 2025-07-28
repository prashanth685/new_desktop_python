from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import numpy as np
import math
import logging

class WaterfallFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None, channel_count=None):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.selected_channel = channel
        self.model_name = model_name
        self.console = console
        self.widget = None
        
        # Validate channel_count
        try:
            self.channel_count = int(channel_count) if channel_count is not None else self.get_channel_count_from_db()
            if self.channel_count <= 0:
                raise ValueError(f"Invalid channel count: {self.channel_count}")
        except (ValueError, TypeError) as e:
            self.channel_count = self.get_channel_count_from_db()
            if self.console:
                self.console.append_to_console(f"Invalid channel_count {channel_count}: {str(e)}. Using {self.channel_count} from database.")
            logging.error(f"Invalid channel_count {channel_count}: {str(e)}. Using {self.channel_count} from database.")

        self.max_lines = 1  # Number of FFT lines to display
        self.data_history = [[] for _ in range(self.channel_count)]  # Holds FFT magnitudes
        self.phase_history = [[] for _ in range(self.channel_count)]  # Holds FFT phases
        self.scaling_factor = 3.3 / 65535.0  # Scaling factor for voltage conversion
        self.sample_rate = 4096  # Default sample rate
        self.samples_per_channel = 4096  # Default samples per channel
        self.selected_channel_index = None  # Index of selected channel, if any

        self.initUI()
        if self.console:
            self.console.append_to_console(
                f"Initialized WaterfallFeature for {self.model_name}/{self.selected_channel or 'All Channels'} with {self.channel_count} channels"
            )

    def get_channel_count_from_db(self):
        """Retrieve channel count from database if not provided."""
        try:
            if not self.db.is_connected():
                self.db.reconnect()
            project_data = self.db.get_project_data(self.project_name)
            if not project_data:
                if self.console:
                    self.console.append_to_console(f"Project {self.project_name} not found in database")
                return 1  # Fallback to minimal count
            model = next((m for m in project_data.get("models", []) if m["name"] == self.model_name), None)
            if not model:
                if self.console:
                    self.console.append_to_console(f"Model {self.model_name} not found")
                return 1
            channels = model.get("channels", [])
            return max(1, len(channels))  # Ensure at least 1 channel
        except Exception as e:
            if self.console:
                self.console.append_to_console(f"Error retrieving channel count from database: {str(e)}")
            logging.error(f"Error retrieving channel count from database: {str(e)}")
            return 1

    def initUI(self):
        self.widget = QWidget()
        layout = QVBoxLayout()
        self.widget.setLayout(layout)

        # Matplotlib figure
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111, projection='3d')  # 3D for waterfall
        layout.addWidget(self.canvas)

        # Add Matplotlib navigation toolbar
        self.toolbar = NavigationToolbar(self.canvas, self.widget)
        layout.addWidget(self.toolbar)

        if not self.model_name and self.console:
            self.console.append_to_console("No model selected in WaterfallFeature.")
        if not self.selected_channel and self.console:
            self.console.append_to_console("No specific channel selected in WaterfallFeature; processing all channels.")

    def get_channel_index(self, channel_name):
        """Retrieve the index of the given channel name from the database."""
        try:
            if not channel_name:
                if self.console:
                    self.console.append_to_console("get_channel_index: No channel name provided")
                return None
            project_data = self.db.get_project_data(self.project_name)
            model = next((m for m in project_data.get("models", []) if m["name"] == self.model_name), None)
            if not model:
                if self.console:
                    self.console.append_to_console(f"get_channel_index: Model {self.model_name} not found")
                return None
            channels = [ch.get("channelName", f"Channel_{i+1}") for i, ch in enumerate(model.get("channels", []))]
            if channel_name in channels:
                idx = channels.index(channel_name)
                if self.console:
                    self.console.append_to_console(f"get_channel_index: Found channel {channel_name} at index {idx}")
                return idx
            if self.console:
                self.console.append_to_console(f"get_channel_index: Channel {channel_name} not found in {channels}")
            return None
        except Exception as e:
            if self.console:
                self.console.append_to_console(f"Error in get_channel_index for {channel_name}: {str(e)}")
            logging.error(f"Error in get_channel_index for {channel_name}: {str(e)}")
            return None

    def update_selected_channel(self, channel_name):
        """Update the selected channel for the waterfall plot."""
        try:
            self.selected_channel = channel_name
            self.selected_channel_index = self.get_channel_index(channel_name) if channel_name else None
            if self.console:
                if self.selected_channel_index is not None:
                    self.console.append_to_console(f"Updated WaterfallFeature to channel: {channel_name} (index {self.selected_channel_index})")
                else:
                    self.console.append_to_console(f"Channel {channel_name} not found; processing all {self.channel_count} channels")
            self.update_waterfall_plot(None)  # Force redraw with current data
        except Exception as e:
            if self.console:
                self.console.append_to_console(f"Error in update_selected_channel for {channel_name}: {str(e)}")
            logging.error(f"Error in update_selected_channel for {channel_name}: {str(e)}")

    def get_widget(self):
        return self.widget

    def on_data_received(self, tag_name, model_name, values, sample_rate):
        if self.model_name != model_name:
            return  # Ignore data for other models
        if self.console:
            self.console.append_to_console(
                f"Waterfall View ({self.model_name}): Received data for {tag_name} - {len(values)} channels, sample_rate={sample_rate}"
            )

        # Validate channel count
        expected_channels = 1 if self.selected_channel_index is not None else self.channel_count
        if len(values) < expected_channels:
            if self.console:
                self.console.append_to_console(f"Insufficient channels received: {len(values)}, expected at least {expected_channels}")
            return

        # Update sample rate
        self.sample_rate = sample_rate if sample_rate > 0 else self.sample_rate

        # Select channels to process
        if self.selected_channel_index is not None:
            channel_indices = [self.selected_channel_index]
        else:
            channel_indices = range(min(self.channel_count, len(values)))

        # Verify data length for each channel
        for ch_idx in channel_indices:
            if len(values[ch_idx]) != self.samples_per_channel:
                if self.console:
                    self.console.append_to_console(
                        f"Invalid channel data length for channel {ch_idx + 1}: got {len(values[ch_idx])}, expected {self.samples_per_channel}"
                    )
                return

        # Apply scaling factor to channel data
        channel_data = [np.array(values[ch_idx], dtype=np.float32) * self.scaling_factor for ch_idx in channel_indices]

        # Calculate target length (next power of 2)
        sample_count = self.samples_per_channel
        target_length = 2 ** math.ceil(math.log2(sample_count))

        fft_magnitudes = []
        fft_phases = []
        frequencies = []

        for i, ch_idx in enumerate(channel_indices):
            # Zero-pad data if necessary
            padded_data = np.pad(channel_data[i], (0, target_length - sample_count), mode='constant') if target_length > sample_count else channel_data[i]

            # Compute FFT
            fft_result = np.fft.fft(padded_data)
            N = len(padded_data)

            # Single-sided FFT magnitude scaled for amplitude peak
            half = N // 2
            magnitudes = (2.0 / N) * np.abs(fft_result[:half])  # Scale for single-sided FFT
            magnitudes[0] /= 2  # DC component
            if N % 2 == 0:
                magnitudes[-1] /= 2  # Nyquist component

            fft_phase = np.angle(fft_result[:half], deg=True)

            # Frequency axis
            freqs = np.array([i * self.sample_rate / N for i in range(half)])

            fft_magnitudes.append(magnitudes)
            fft_phases.append(fft_phase)
            frequencies.append(freqs)

        # Store FFT data in history
        for i, ch_idx in enumerate(channel_indices):
            self.data_history[ch_idx].append(fft_magnitudes[i])
            self.phase_history[ch_idx].append(fft_phases[i])
            if len(self.data_history[ch_idx]) > self.max_lines:
                self.data_history[ch_idx].pop(0)
                self.phase_history[ch_idx].pop(0)

        self.update_waterfall_plot(frequencies[0] if frequencies else None)

    def update_waterfall_plot(self, frequencies):
        self.ax.clear()
        title = f"Waterfall FFT Plot (Model: {self.model_name}"
        if self.selected_channel_index is not None:
            title += f", Channel: {self.selected_channel or 'Unknown'})"
        else:
            title += f", {self.channel_count} Channels)"
        self.ax.set_title(title)
        self.ax.set_xlabel("Frequency (Hz)")
        self.ax.set_ylabel("Channel/Time")
        self.ax.set_zlabel("Amplitude (V)")
        self.ax.grid(True)

        colors = ['blue', 'red', 'green', 'purple', 'orange', 'cyan', 'magenta', 'yellow', 'black', 'brown']
        max_amplitude = 0

        # Determine channels to plot
        if self.selected_channel_index is not None:
            channel_indices = [self.selected_channel_index]
        else:
            channel_indices = range(self.channel_count)

        for ch_idx in channel_indices:
            num_lines = len(self.data_history[ch_idx])
            for idx, fft_line in enumerate(self.data_history[ch_idx]):
                x = frequencies if frequencies is not None else np.arange(len(fft_line))
                y = np.full_like(x, num_lines - idx - 1 + ch_idx * (self.max_lines + 2))
                z = fft_line
                label = f"Channel {ch_idx + 1}" if self.selected_channel_index is None else self.selected_channel
                self.ax.plot(x, y, z, color=colors[ch_idx % len(colors)], label=label if idx == num_lines - 1 else None)
                max_amplitude = max(max_amplitude, np.max(z))

        # Set axis limits
        self.ax.set_ylim(-1, len(channel_indices) * (self.max_lines + 2))
        self.ax.set_xlim(frequencies[0] if frequencies is not None else 0, frequencies[-1] if frequencies is not None else len(fft_line) - 1)
        self.ax.set_zlim(0, max_amplitude * 1.1 if max_amplitude > 0 else 1.0)

        self.ax.legend(loc='upper right')
        self.figure.tight_layout()

        # Set 3D view angle
        self.ax.view_init(elev=20, azim=-45)

        self.canvas.draw()

    def cleanup(self):
        """Clean up resources."""
        try:
            self.canvas.figure.clear()
            self.canvas.deleteLater()
            self.toolbar.deleteLater()
            self.widget.deleteLater()
            if self.console:
                self.console.append_to_console(f"Cleaned up WaterfallFeature for {self.model_name}/{self.selected_channel or 'All Channels'}")
        except Exception as e:
            if self.console:
                self.console.append_to_console(f"Error cleaning up WaterfallFeature: {str(e)}")
            logging.error(f"Error cleaning up WaterfallFeature: {str(e)}")

    def refresh_channel_properties(self):
        """Refresh channel properties from the database."""
        try:
            if not self.db.is_connected():
                self.db.reconnect()
            project_data = self.db.get_project_data(self.project_name)
            model = next((m for m in project_data.get("models", []) if m["name"] == self.model_name), None)
            if model:
                channels = [ch.get("channelName", f"Channel_{i+1}") for i, ch in enumerate(model.get("channels", []))]
                new_channel_count = len(channels)
                if new_channel_count != self.channel_count:
                    if self.console:
                        self.console.append_to_console(
                            f"Channel count updated from {self.channel_count} to {new_channel_count} for model {self.model_name}"
                        )
                    self.channel_count = new_channel_count
                    self.data_history = [self.data_history[i] if i < len(self.data_history) else [] for i in range(self.channel_count)]
                    self.phase_history = [self.phase_history[i] if i < len(self.phase_history) else [] for i in range(self.channel_count)]
                if self.selected_channel and self.selected_channel in channels:
                    self.selected_channel_index = channels.index(self.selected_channel)
                    if self.console:
                        self.console.append_to_console(
                            f"Refreshed channel properties: Set channel {self.selected_channel} to index {self.selected_channel_index}"
                        )
                else:
                    self.selected_channel_index = None
                    if self.console:
                        self.console.append_to_console("Refreshed channel properties: No specific channel selected")
            else:
                if self.console:
                    self.console.append_to_console(f"Model {self.model_name} not found during refresh")
        except Exception as e:
            if self.console:
                self.console.append_to_console(f"Error refreshing channel properties: {str(e)}")
            logging.error(f"Error refreshing channel properties: {str(e)}")