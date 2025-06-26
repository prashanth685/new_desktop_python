import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem
import pyqtgraph as pg
from datetime import datetime
import math
import logging


class ChannelData:
    def __init__(self, channel_name, date_time, rpm, gap, direct, bandpass, one_xa, one_xp, two_xa, two_xp, nx_amp, nx_phase, vpp, vrms):
        self.channel_name = channel_name
        self.date_time = date_time
        self.rpm = rpm
        self.gap = gap
        self.direct = direct
        self.bandpass = bandpass
        self.one_xa = one_xa
        self.one_xp = one_xp
        self.two_xa = two_xa
        self.two_xp = two_xp
        self.nx_amp = nx_amp
        self.nx_phase = nx_phase
        self.vpp = vpp
        self.vrms = vrms


class TabularViewFeature:
    def __init__(self, parent, mqtt_handler, project_name, channel=None, model_name=None, console=None, channel_names=None):
        self.parent = parent
        self.mqtt_handler = mqtt_handler
        self.project_name = project_name
        self.channel = channel
        self.model_name = model_name
        self.console = console
        self.channel_names = channel_names or ["Channel1", "Channel2", "Channel3", "Channel4"]
        self.tag_name = f"{project_name}/{model_name}" if model_name else project_name
        self.channel1_data = np.array([])
        self.channel1_sine_theta_data = np.array([])
        self.channel1_cosine_theta_data = np.array([])
        self.sine_theta_indices = np.array([])
        self.trigger_data = np.array([])
        self.current_channel_data = []
        self.initUI()
        self.initialize()

    def initUI(self):
        self.widget = QWidget()
        layout = QVBoxLayout()
        self.widget.setLayout(layout)

        self.waiting_label = QLabel("Waiting for data...")
        layout.addWidget(self.waiting_label)

        # Initialize pyqtgraph plots
        self.plot_widget = pg.GraphicsLayoutWidget()
        layout.addWidget(self.plot_widget)

        self.channel1_plot = self.plot_widget.addPlot(row=0, col=0, title="Channel 1 Waveform")
        self.channel1_plot.setLabel('bottom', 'Sample Index')
        self.channel1_plot.setLabel('left', 'Voltage (V)')
        self.channel1_plot.setYRange(0, 3.3)
        self.channel1_plot.setXRange(0, 1)
        self.channel1_curve = self.channel1_plot.plot(pen='b')

        self.sine_theta_plot = self.plot_widget.addPlot(row=1, col=0, title="Channel 1 Sine-Theta Plot")
        self.sine_theta_plot.setLabel('bottom', 'Sample Index')
        self.sine_theta_plot.setLabel('left', 'Sine Theta')
        self.sine_theta_plot.setYRange(-1, 1)
        self.sine_theta_plot.setXRange(0, 1)
        self.sine_theta_curve = self.sine_theta_plot.plot(pen='r')

        self.cosine_theta_plot = self.plot_widget.addPlot(row=2, col=0, title="Channel 1 Cosine-Theta Plot")
        self.cosine_theta_plot.setLabel('bottom', 'Sample Index')
        self.cosine_theta_plot.setLabel('left', 'Cosine Theta')
        self.cosine_theta_plot.setYRange(-1, 1)
        self.cosine_theta_plot.setXRange(0, 1)
        self.cosine_theta_curve = self.cosine_theta_plot.plot(pen='g')

        self.trigger_plot = self.plot_widget.addPlot(row=3, col=0, title="Trigger (Tacho 2) Plot")
        self.trigger_plot.setLabel('bottom', 'Sample Index')
        self.trigger_plot.setLabel('left', 'Trigger Value')
        self.trigger_plot.setYRange(-0.1, 1.1)
        self.trigger_plot.setXRange(0, 1)
        self.trigger_curve = self.trigger_plot.plot(pen=(128, 0, 128))

        # Initialize table with additional columns for Vpp and Vrms
        self.table = QTableWidget()
        self.table.setColumnCount(14)
        self.table.setHorizontalHeaderLabels([
            "Channel Name", "DateTime", "RPM", "Gap", "Direct", "Bandpass",
            "1X Amp", "1X Phase", "2X Amp", "2X Phase", "NX Amp", "NX Phase",
            "Vpp", "Vrms"
        ])
        layout.addWidget(self.table)

        self.cycle_sums_label = QLabel("Cycle Data: (No data available)")
        layout.addWidget(self.cycle_sums_label)

    def get_widget(self):
        return self.widget

    def log(self, message):
        if self.console:
            self.console.append_to_console(message)
        logging.debug(message)

    def initialize(self):
        if not self.model_name or not self.channel:
            self.log("Model or channel not specified in TabularViewFeature.")
            self.waiting_label.setText("Model or channel not specified.")
            return

        if self.channel not in self.channel_names:
            self.log(f"Selected channel {self.channel} not found in channel names: {self.channel_names}")
            self.waiting_label.setText("Selected channel not found.")
            return

        self.mqtt_handler.data_received.connect(self.on_data_received)
        self.mqtt_handler.connection_status.connect(self.on_connection_status)
        self.mqtt_handler.start()
        self.log(f"Initialized TabularViewFeature for {self.project_name}/{self.model_name}/{self.channel}")

    def on_connection_status(self, status):
        self.log(f"MQTT Connection Status: {status}")
        self.waiting_label.setText(status)

    def on_data_received(self, tag_name, model_name, values, sample_rate):
        if model_name != self.model_name or tag_name != self.tag_name:
            self.log(f"Ignoring data for tag {tag_name}/{model_name}, expected {self.tag_name}/{self.model_name}")
            return

        try:
            if len(values) != 6:
                self.log(f"Expected 6 channels (4 main + 2 tacho), got {len(values)}")
                self.waiting_label.setText("Unexpected channel count.")
                return

            main_channels = 4
            samples_per_channel = 4096
            num_tacho_channels = 2
            expected_total = samples_per_channel * (main_channels + num_tacho_channels)

            # Validate data length
            if any(len(ch) != samples_per_channel for ch in values):
                self.log(f"Expected {samples_per_channel} samples per channel, got {[len(ch) for ch in values]}")
                return

            # Calibrate main channel data (scale by 3.3/65535)
            calibrated_data = [np.array(ch) * (3.3 / 65535.0) for ch in values[:main_channels]]
            tacho_freq_data = np.array(values[main_channels])
            self.trigger_data = np.array(values[main_channels + 1])
            self.channel1_data = calibrated_data[0]

            self.log(f"Processed {main_channels + num_tacho_channels} channels ({main_channels} main, {num_tacho_channels} tacho), {samples_per_channel} samples per channel.")

            # Trigger detection
            trigger_indices = np.where(self.trigger_data == 1)[0].tolist()
            self.log(f"Raw trigger data contains {len(trigger_indices)} ones at indices: [{', '.join(map(str, trigger_indices))}]")

            min_distance_between_triggers = 5
            filtered_trigger_indices = [trigger_indices[0]]
            for i in trigger_indices[1:]:
                if i - filtered_trigger_indices[-1] >= min_distance_between_triggers:
                    filtered_trigger_indices.append(i)
            trigger_indices = filtered_trigger_indices
            self.log(f"After filtering, {len(trigger_indices)} trigger points at indices: [{', '.join(map(str, trigger_indices))}]")

            if len(trigger_indices) < 2:
                self.log("Not enough trigger points detected. At least 2 triggers are required.")
                self.waiting_label.setText("Not enough trigger points.")
                return

            # Vibration analysis using DFT
            channel_data_list = []
            sine_theta_values = []
            cosine_theta_values = []
            sine_theta_indices_list = []

            for channel_index in range(main_channels):
                one_x_amplitudes = []
                one_x_phases = []
                two_x_amplitudes = []
                two_x_phases = []
                three_x_amplitudes = []
                three_x_phases = []
                vpps = []
                vrmss = []

                for i in range(len(trigger_indices) - 1):
                    start_index, end_index = trigger_indices[i], trigger_indices[i + 1]
                    segment_length = end_index - start_index
                    if segment_length <= 0:
                        continue

                    segment_data = calibrated_data[channel_index][start_index:end_index]
                    N = segment_length
                    W_N = np.exp(-1j * 2 * np.pi / N)

                    # Calculate Vpp and Vrms for the segment
                    vpp = np.max(segment_data) - np.min(segment_data)
                    vrms = np.sqrt(np.mean(segment_data ** 2))
                    vpps.append(vpp)
                    vrmss.append(vrms)

                    # Generate sine and cosine theta for Channel 1
                    if channel_index == 0:
                        for n in range(segment_length):
                            global_index = start_index + n
                            theta = (2 * np.pi * n) / N
                            sine_theta_values.append(np.sin(theta))
                            cosine_theta_values.append(np.cos(theta))
                            sine_theta_indices_list.append(global_index)

                    # Calculate DFT for k=1, k=2, k=3
                    for k in [1, 2, 3]:
                        X_k = 0
                        for n in range(N):
                            X_k += segment_data[n] * (W_N ** (k * n))
                        # Amplitude is scaled by 2/N for magnitude
                        amplitude = (2 / N) * np.abs(X_k)
                        # Phase in degrees
                        phase = np.angle(X_k, deg=True)

                        if k == 1:
                            one_x_amplitudes.append(amplitude)
                            one_x_phases.append(phase)
                        elif k == 2:
                            two_x_amplitudes.append(amplitude)
                            two_x_phases.append(phase)
                        elif k == 3:
                            three_x_amplitudes.append(amplitude)
                            three_x_phases.append(phase)

                # Compute averages
                one_x_avg_amp = np.mean(one_x_amplitudes) if one_x_amplitudes else 0.0
                one_x_avg_phase = np.mean(one_x_phases) if one_x_phases else 0.0
                two_x_avg_amp = np.mean(two_x_amplitudes) if two_x_amplitudes else 0.0
                two_x_avg_phase = np.mean(two_x_phases) if two_x_phases else 0.0
                three_x_avg_amp = np.mean(three_x_amplitudes) if three_x_amplitudes else 0.0
                three_x_avg_phase = np.mean(three_x_phases) if three_x_phases else 0.0
                vpp_avg = np.mean(vpps) if vpps else 0.0
                vrms_avg = np.mean(vrmss) if vrmss else 0.0

                channel_data_list.append(ChannelData(
                    channel_name=self.channel_names[channel_index],
                    date_time=datetime.now().strftime("%d-%b-%Y %I:%M:%S %p"),
                    rpm="0",
                    gap="0",
                    direct=f"{vpp_avg:.2f}",  # Use Vpp as direct
                    bandpass="0",
                    one_xa=f"{one_x_avg_amp:.2f}",
                    one_xp=f"{one_x_avg_phase:.2f}",
                    two_xa=f"{two_x_avg_amp:.2f}",
                    two_xp=f"{two_x_avg_phase:.2f}",
                    nx_amp=f"{three_x_avg_amp:.2f}",
                    nx_phase=f"{three_x_avg_phase:.2f}",
                    vpp=f"{vpp_avg:.2f}",
                    vrms=f"{vrms_avg:.2f}"
                ))

            self.channel1_sine_theta_data = np.array(sine_theta_values)
            self.channel1_cosine_theta_data = np.array(cosine_theta_values)
            self.sine_theta_indices = np.array(sine_theta_indices_list)

            self.log(f"Computed {len(self.channel1_sine_theta_data)} sine-theta and cosine-theta values for Channel 1.")
            self.current_channel_data = channel_data_list
            self.update_table()
            self.update_plots()

            self.cycle_sums_label.setText(
                f"Trigger Indices: [{', '.join(map(str, trigger_indices))}]\n"
                f"1X Amplitudes (Ch1): [{', '.join(f'{a:.2f}' for a in one_x_amplitudes)}]\n"
                f"1X Phases (Ch1): [{', '.join(f'{p:.2f}' for p in one_x_phases)}]\n"
                f"Vpp (Ch1): [{', '.join(f'{v:.2f}' for v in vpps)}]\n"
                f"Vrms (Ch1): [{', '.join(f'{v:.2f}' for v in vrmss)}]"
            )

            self.log(f"Processed MQTT message for topic {tag_name}: Updated table with 1x, 2x, 3x amplitudes, Vpp, and Vrms.")
            self.waiting_label.setVisible(False)
        except Exception as e:
            self.log(f"Error processing MQTT message: {str(e)}")
            self.waiting_label.setText("Error processing data.")

    def update_plots(self):
        if len(self.channel1_data) > 0:
            indices = np.arange(len(self.channel1_data))
            self.channel1_plot.setXRange(0, max(indices) + 1)
            self.channel1_curve.setData(indices, self.channel1_data)

        if len(self.channel1_sine_theta_data) > 0:
            self.sine_theta_plot.setXRange(0, max(self.sine_theta_indices) + 1)
            self.sine_theta_curve.setData(self.sine_theta_indices, self.channel1_sine_theta_data)

        if len(self.channel1_cosine_theta_data) > 0:
            self.cosine_theta_plot.setXRange(0, max(self.sine_theta_indices) + 1)
            self.cosine_theta_curve.setData(self.sine_theta_indices, self.channel1_cosine_theta_data)

        if len(self.trigger_data) > 0:
            indices = np.arange(len(self.trigger_data))
            self.trigger_plot.setXRange(0, max(indices) + 1)
            self.trigger_curve.setData(indices, self.trigger_data)

    def update_table(self):
        self.table.setRowCount(0)
        for data in self.current_channel_data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(data.channel_name))
            self.table.setItem(row, 1, QTableWidgetItem(data.date_time))
            self.table.setItem(row, 2, QTableWidgetItem(data.rpm))
            self.table.setItem(row, 3, QTableWidgetItem(data.gap))
            self.table.setItem(row, 4, QTableWidgetItem(data.direct))
            self.table.setItem(row, 5, QTableWidgetItem(data.bandpass))
            self.table.setItem(row, 6, QTableWidgetItem(data.one_xa))
            self.table.setItem(row, 7, QTableWidgetItem(data.one_xp))
            self.table.setItem(row, 8, QTableWidgetItem(data.two_xa))
            self.table.setItem(row, 9, QTableWidgetItem(data.two_xp))
            self.table.setItem(row, 10, QTableWidgetItem(data.nx_amp))
            self.table.setItem(row, 11, QTableWidgetItem(data.nx_phase))
            self.table.setItem(row, 12, QTableWidgetItem(data.vpp))
            self.table.setItem(row, 13, QTableWidgetItem(data.vrms))