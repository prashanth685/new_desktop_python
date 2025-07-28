from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
import pyqtgraph as pg
import numpy as np
from collections import defaultdict

class BodePlotFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.channel = channel
        self.model_name = model_name
        self.console = console
        self.widget = None
        self.plot_widget = None
        self.mag_plot = None
        self.phase_plot = None
        self.initUI()

    def initUI(self):
        self.widget = QWidget()
        layout = QVBoxLayout()
        self.widget.setLayout(layout)

        label = QLabel(f"Bode Plot for Model: {self.model_name}, Channel: {self.channel}")
        layout.addWidget(label)

        # Create and add the pyqtgraph PlotWidget
        self.plot_widget = pg.PlotWidget()
        layout.addWidget(self.plot_widget)

        # Set up the plot layout with two subplots (magnitude and phase)
        self.plot_widget.getPlotItem().hide()
        self.vb = self.plot_widget.getViewBox()
        self.vb.setBackgroundColor('w')  # White background
        self.layout = pg.GraphicsLayout()
        self.plot_widget.setCentralItem(self.layout)

        # Magnitude plot
        self.mag_plot = self.layout.addPlot(row=0, col=0)
        self.mag_plot.setTitle("Bode Plot - Magnitude")
        self.mag_plot.setLabel('left', "Amplitude")
        self.mag_plot.setLabel('bottom', "Frequency (Hz)")
        self.mag_plot.setLogMode(x=True, y=False)
        self.mag_plot.showGrid(x=True, y=True, alpha=0.3)

        # Phase plot
        self.layout.nextRow()
        self.phase_plot = self.layout.addPlot(row=1, col=0)
        self.phase_plot.setTitle("Bode Plot - Phase")
        self.phase_plot.setLabel('left', "Phase (degrees)")
        self.phase_plot.setLabel('bottom', "Frequency (Hz)")
        self.phase_plot.setLogMode(x=True, y=False)
        self.phase_plot.showGrid(x=True, y=True, alpha=0.3)

        if not self.model_name and self.console:
            self.console.append_to_console("No model selected in BodePlotFeature.")
        if self.channel is None and self.console:
            self.console.append_to_console("No channel selected in BodePlotFeature.")

    def get_widget(self):
        return self.widget

    def find_trigger_indices(self, trigger_data):
        """Find indices where trigger_data == 1 with minimum distance between triggers."""
        indices = []
        min_distance = 5
        for i in range(len(trigger_data)):
            if trigger_data[i] == 1:
                if not indices or i - indices[-1] >= min_distance:
                    indices.append(i)
        return indices

    def process_trigger_segments(self, channel_data, frequency_data, trigger_indices):
        """Process data segments between trigger points."""
        temp_freq = []
        temp_amp = []
        temp_phase = []

        for i in range(len(trigger_indices) - 1):
            start_idx = trigger_indices[i]
            end_idx = trigger_indices[i + 1]
            segment_length = end_idx - start_idx

            if segment_length <= 0 or start_idx < 0 or end_idx > len(channel_data):
                continue

            # Calculate DFT components
            sine_sum = 0.0
            cosine_sum = 0.0
            N = segment_length

            for n in range(segment_length):
                theta = (2 * np.pi * n) / N
                sine_sum += channel_data[start_idx + n] * np.sin(theta)
                cosine_sum += channel_data[start_idx + n] * np.cos(theta)

            sine_component = sine_sum / N
            cosine_component = cosine_sum / N
            amplitude = np.sqrt(sine_component**2 + cosine_component**2) * 4
            phase = np.arctan2(cosine_component, sine_component) * (180.0 / np.pi)
            if phase < 0:
                phase += 360

            # Calculate average frequency for the segment
            count = min(end_idx - start_idx, len(frequency_data) - start_idx)
            if count > 0:
                frequency = np.mean(frequency_data[start_idx:start_idx + count])
            else:
                continue

            # Validate data
            if not (np.isnan(amplitude) or np.isinf(amplitude) or
                    np.isnan(phase) or np.isinf(phase) or
                    np.isnan(frequency) or np.isinf(frequency)):
                temp_freq.append(frequency)
                temp_amp.append(amplitude)
                temp_phase.append(phase)

        return temp_freq, temp_amp, temp_phase

    def on_data_received(self, tag_name, model_name, values, sample_rate=1000, frequency_data=None, trigger_data=None):
        if self.model_name != model_name:
            return  # Ignore data for other models

        if self.console:
            self.console.append_to_console(
                f"Bode Plot ({self.model_name} - {self.channel}): Received data for {tag_name}"
            )

        try:
            # Validate channel and values
            if self.channel is None:
                if self.console:
                    self.console.append_to_console(f"No channel specified for {tag_name}")
                return

            # Convert channel to int if it isn't already
            channel_idx = int(self.channel)

            # Select the appropriate channel data
            if isinstance(values, list) and len(values) > channel_idx >= 0:
                channel_data = np.array(values[channel_idx]) * (3.3 / 65535.0)  # Apply calibration
            else:
                channel_data = np.array(values) * (3.3 / 65535.0)
                if self.console:
                    self.console.append_to_console(f"Invalid channel index {channel_idx} for {tag_name}, using default data")
                return

            if len(channel_data) == 0:
                if self.console:
                    self.console.append_to_console(f"No data received for {tag_name}")
                return

            # Validate frequency and trigger data
            if frequency_data is None or trigger_data is None:
                if self.console:
                    self.console.append_to_console(f"Missing frequency or trigger data for {tag_name}")
                return

            frequency_data = np.array(frequency_data)
            trigger_data = np.array(trigger_data)

            if len(channel_data) != len(frequency_data) or len(channel_data) != len(trigger_data):
                if self.console:
                    self.console.append_to_console(
                        f"Array length mismatch - channel: {len(channel_data)}, "
                        f"frequency: {len(frequency_data)}, trigger: {len(trigger_data)}"
                    )
                return

            # Find trigger indices
            trigger_indices = self.find_trigger_indices(trigger_data)
            if self.console:
                self.console.append_to_console(
                    f"Raw trigger data contains {len(trigger_indices)} ones at indices: {trigger_indices}"
                )

            if len(trigger_indices) < 2:
                if self.console:
                    self.console.append_to_console("Not enough trigger points detected. At least 2 triggers are required.")
                return

            # Process trigger segments
            temp_freq, temp_amp, temp_phase = self.process_trigger_segments(
                channel_data, frequency_data, trigger_indices
            )

            if self.console:
                self.console.append_to_console(
                    f"Processed {len(temp_amp)} individual cycles for Channel {self.channel}"
                )

            # Group by frequency and average
            if temp_freq:
                # Use defaultdict to group by rounded frequency
                freq_groups = defaultdict(list)
                for f, a, p in zip(temp_freq, temp_amp, temp_phase):
                    freq_key = round(f, 2)
                    freq_groups[freq_key].append((a, p))

                # Calculate averages
                avg_frequencies = []
                avg_amplitudes = []
                avg_phases = []
                for freq_key, values in freq_groups.items():
                    amplitudes, phases = zip(*values)
                    avg_frequencies.append(freq_key)
                    avg_amplitudes.append(np.mean(amplitudes))
                    avg_phases.append(np.mean(phases))

                # Sort by frequency
                sorted_data = sorted(zip(avg_frequencies, avg_amplitudes, avg_phases), key=lambda x: x[0])
                avg_frequencies, avg_amplitudes, avg_phases = zip(*sorted_data)

                # Apply moving average smoothing
                window_size = 7
                smoothed_frequencies = []
                smoothed_amplitudes = []
                smoothed_phases = []

                for i in range(len(avg_frequencies)):
                    start_idx = max(0, i - window_size // 2)
                    end_idx = min(len(avg_frequencies) - 1, i + window_size // 2) + 1
                    actual_window_size = end_idx - start_idx

                    smoothed_frequencies.append(np.mean(avg_frequencies[start_idx:end_idx]))
                    smoothed_amplitudes.append(np.mean(avg_amplitudes[start_idx:end_idx]))
                    smoothed_phases.append(np.mean(avg_phases[start_idx:end_idx]))

                # Clear previous plots
                self.mag_plot.clear()
                self.phase_plot.clear()

                # Plot new data
                self.mag_plot.plot(smoothed_frequencies, smoothed_amplitudes, pen='b')
                self.phase_plot.plot(smoothed_frequencies, smoothed_phases, pen='r')

                # Update plot settings
                self.mag_plot.setTitle(f"Bode Plot - Amplitude (Moving Avg)")
                self.phase_plot.setTitle(f"Bode Plot - Phase (Moving Avg)")

                # Set axis limits
                x_min = min(smoothed_frequencies) - 0.1 * (max(smoothed_frequencies) - min(smoothed_frequencies))
                x_max = max(smoothed_frequencies) + 0.1 * (max(smoothed_frequencies) - min(smoothed_frequencies))
                self.mag_plot.setXRange(x_min, x_max)
                self.phase_plot.setXRange(x_min, x_max)

                y_min = min(smoothed_amplitudes) - 0.1 * (max(smoothed_amplitudes) - min(smoothed_amplitudes))
                y_max = max(smoothed_amplitudes) + 0.1 * (max(smoothed_amplitudes) - min(smoothed_amplitudes))
                self.mag_plot.setYRange(y_min, y_max)

                phase_min = max(-360, min(smoothed_phases) - 0.1 * (max(smoothed_phases) - min(smoothed_phases)))
                phase_max = min(360, max(smoothed_phases) + 0.1 * (max(smoothed_phases) - min(smoothed_phases)))
                self.phase_plot.setYRange(phase_min, phase_max)

                self.plot_widget.show()

                if self.console:
                    self.console.append_to_console(
                        f"Plotted {len(smoothed_frequencies)} points after smoothing"
                    )

        except Exception as e:
            if self.console:
                self.console.append_to_console(f"Error in Bode Plot for {tag_name}: {str(e)}")