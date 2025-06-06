from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QHBoxLayout
import pyqtgraph as pg
import numpy as np
import math
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class OrbitFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.selected_channel = channel  # Selected channel from tree view (e.g., "Channel_1")
        self.model_name = model_name
        self.console = console
        self.widget = None
        self.plot_widgets = []
        self.plot_items = []
        self.data_plots = []
        self.time_plot_widgets = []
        self.time_plots = []
        self.cross_lines = []
        self.channel_data = [[] for _ in range(4)]  # Store data for 4 channels
        self.selected_pairs = []  # Will be set based on selected channel
        self.cross_pair = None
        self.sample_rate = 4096
        self.samples_per_channel = 4096
        self.frequency = 10  # Hz, from MQTTPublisher
        self.amplitude = (46537 - 16390) / 2
        self.offset = (46537 + 16390) / 2
        self.current_time = 0.0
        self.initUI()

    def initUI(self):
        self.widget = QWidget()
        main_layout = QVBoxLayout()
        self.widget.setLayout(main_layout)

        # Label
        label = QLabel(f"Orbit Plot for Model: {self.model_name if self.model_name else 'None'}")
        main_layout.addWidget(label)

        # Channel selection combo box
        self.combo = QComboBox()
        self.update_combo_options()
        self.combo.currentIndexChanged.connect(self.on_combo_changed)
        main_layout.addWidget(self.combo)

        # Layout for plots
        self.plot_layout = QHBoxLayout()
        main_layout.addLayout(self.plot_layout)

        # Initialize with default pair based on selected channel
        self.set_default_pairs()
        self.recreate_plots()

        if not self.model_name and self.console:
            self.console.append_to_console("No model selected in OrbitFeature.")

    def update_combo_options(self):
        """Update combo box options based on selected channel."""
        self.combo.clear()
        channel_idx = self.get_channel_index(self.selected_channel)
        options = []
        if channel_idx is not None:
            # Options for pairs including the selected channel
            other_channels = [i for i in range(4) if i != channel_idx]
            for other in other_channels:
                pair_name = f"Channels {channel_idx+1} & {other+1}"
                options.append(pair_name)
            # Add option for all channels if not already included
            options.append("Channels 1, 2, 3 & 4")
        else:
            # Default options if no channel is selected
            options = [
                "Channels 1 & 2",
                "Channels 3 & 4",
                "Channels 1 & 3",
                "Channels 1 & 4",
                "Channels 2 & 3",
                "Channels 2 & 4",
                "Channels 1, 2, 3 & 4"
            ]
        self.combo.addItems(options)

    def get_channel_index(self, channel_name):
        """Convert channel name to index (0-based)."""
        if not channel_name:
            return None
        try:
            return int(channel_name.split('_')[-1]) - 1
        except:
            return None

    def set_default_pairs(self):
        """Set default channel pairs based on selected channel."""
        channel_idx = self.get_channel_index(self.selected_channel)
        if channel_idx is not None:
            # Default to pairing with the next channel (e.g., Ch1 with Ch2, Ch2 with Ch1 or Ch3)
            if channel_idx == 0:
                self.selected_pairs = [(0, 1)]  # Ch1 vs Ch2
            elif channel_idx == 1:
                self.selected_pairs = [(1, 0)]  # Ch2 vs Ch1
            elif channel_idx == 2:
                self.selected_pairs = [(2, 3)]  # Ch3 vs Ch4
            elif channel_idx == 3:
                self.selected_pairs = [(3, 2)]  # Ch4 vs Ch3
            self.cross_pair = self.selected_pairs[0] if self.selected_pairs[0] in [(0, 2), (0, 3), (1, 2), (1, 3)] else None
        else:
            self.selected_pairs = [(0, 1)]  # Default to Ch1 vs Ch2
            self.cross_pair = None

    def on_combo_changed(self, index):
        """Handle channel pair selection from combo box."""
        channel_idx = self.get_channel_index(self.selected_channel)
        pair_map = {}
        if channel_idx is not None:
            other_channels = [i for i in range(4) if i != channel_idx]
            for i, other in enumerate(other_channels):
                pair_map[i] = [(channel_idx, other)]
            pair_map[len(other_channels)] = [(0, 1), (2, 3)]  # All channels
        else:
            pair_map = {
                0: [(0, 1)],  # Ch1 vs Ch2
                1: [(2, 3)],  # Ch3 vs Ch4
                2: [(0, 2)],  # Ch1 vs Ch3
                3: [(0, 3)],  # Ch1 vs Ch4
                4: [(1, 2)],  # Ch2 vs Ch3
                5: [(1, 3)],  # Ch2 vs Ch4
                6: [(0, 1), (2, 3)]  # All channels
            }
        self.selected_pairs = pair_map.get(index, [(0, 1)])
        self.cross_pair = self.selected_pairs[0] if len(self.selected_pairs) == 1 and self.selected_pairs[0] in [(0, 2), (0, 3), (1, 2), (1, 3)] else None
        self.recreate_plots()
        self.update_plots_with_sine_data()
        if self.console:
            self.console.append_to_console(f"Selected channel pairs: {self.selected_pairs}, cross pair: {self.cross_pair}")

    def recreate_plots(self):
        """Recreate orbit and time-domain plot widgets based on selected pairs."""
        # Clear existing widgets
        for plot_widget in self.plot_widgets + self.time_plot_widgets:
            plot_widget.deleteLater()
        self.plot_widgets = []
        self.plot_items = []
        self.data_plots = []
        self.time_plot_widgets = []
        self.time_plots = []
        self.cross_lines = []

        # Clear plot layout
        while self.plot_layout.count():
            item = self.plot_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                item.layout().deleteLater()

        # Create new plot widgets
        colors = ['b', 'g']
        time_colors = ['r', 'g', 'b', 'y']
        channels_to_plot = set()
        for ch_x, ch_y in self.selected_pairs:
            channels_to_plot.add(ch_x)
            channels_to_plot.add(ch_y)

        # Orbit plots
        for i, (ch_x, ch_y) in enumerate(self.selected_pairs):
            plot_widget = pg.PlotWidget()
            plot_widget.setFixedSize(500, 500)  # Increased size
            self.plot_layout.addWidget(plot_widget)
            plot_item = plot_widget.getPlotItem()
            plot_item.setTitle(f"Orbit Plot (Ch {ch_y+1} vs Ch {ch_x+1})")
            plot_item.setLabel('bottom', f"Channel {ch_x+1}")
            plot_item.setLabel('left', f"Channel {ch_y+1}")
            plot_item.showGrid(x=True, y=True)
            plot_item.setAspectLocked(True)
            plot_item.enableAutoRange('xy', True)
            data_plot = plot_item.plot(pen=pg.mkPen(colors[i % len(colors)], width=2))
            self.plot_widgets.append(plot_widget)
            self.plot_items.append(plot_item)
            self.data_plots.append(data_plot)
            cross_line = None
            if self.cross_pair and (ch_x, ch_y) == self.cross_pair:
                cross_line = pg.InfiniteLine(angle=45, movable=False, pen=pg.mkPen('r', width=2))
                plot_item.addItem(cross_line)
            self.cross_lines.append(cross_line)

        # Time-domain plots for selected channels
        for ch in sorted(channels_to_plot):
            time_plot_widget = pg.PlotWidget()
            time_plot_widget.setFixedSize(500, 500)  # Increased size
            self.plot_layout.addWidget(time_plot_widget)
            time_plot_item = time_plot_widget.getPlotItem()
            time_plot_item.setTitle(f"Channel {ch+1} Time Domain")
            time_plot_item.setLabel('bottom', "Time (s)")
            time_plot_item.setLabel('left', f"Channel {ch+1} Value")
            time_plot_item.showGrid(x=True, y=True)
            time_plot = time_plot_item.plot(pen=pg.mkPen(time_colors[ch % len(time_colors)], width=2))
            self.time_plot_widgets.append(time_plot_widget)
            self.time_plots.append(time_plot)

    def generate_sine_wave(self, num_samples, sample_rate, frequency, amplitude, offset, phase=0.0):
        """Generate a sine wave for a given channel."""
        t = np.linspace(self.current_time, self.current_time + num_samples / sample_rate, num_samples, endpoint=False)
        return offset + amplitude * np.sin(2 * np.pi * frequency * t + phase)

    def update_plots_with_sine_data(self):
        """Generate sine wave data and update plots."""
        self.current_time += 1.0
        phases = [0, np.pi/2, 0, np.pi/2]
        for i in range(4):
            self.channel_data[i] = self.generate_sine_wave(
                self.samples_per_channel, self.sample_rate, self.frequency, self.amplitude, self.offset, phases[i]
            )

        # Update orbit plots
        for i, (ch_x, ch_y) in enumerate(self.selected_pairs):
            x_data = self.channel_data[ch_x]
            y_data = self.channel_data[ch_y]
            self.data_plots[i].setData(x_data, y_data)

            # Verify circular orbit
            if (ch_x, ch_y) in [(0, 1), (2, 3)]:
                radius = np.sqrt((x_data - self.offset)**2 + (y_data - self.offset)**2)
                mean_radius = np.mean(radius)
                std_radius = np.std(radius)
                if std_radius / mean_radius < 0.01:
                    if self.console:
                        self.console.append_to_console(f"Orbit (Ch {ch_x+1}, Ch {ch_y+1}) is circular, radius: {mean_radius:.2f}")
                else:
                    if self.console:
                        self.console.append_to_console(f"Orbit (Ch {ch_x+1}, Ch {ch_y+1}) is not circular, std/mean: {std_radius/mean_radius:.4f}")

        # Update time-domain plots
        channels_to_plot = set(ch for pair in self.selected_pairs for ch in pair)
        time = np.linspace(self.current_time - 1.0, self.current_time, self.samples_per_channel, endpoint=False)
        for i, ch in enumerate(sorted(channels_to_plot)):
            if i < len(self.time_plots):
                self.time_plots[i].setData(time, self.channel_data[ch])

    def on_data_received(self, tag_name, model_name, values, sample_rate):
        """Handle incoming MQTT data and update plots."""
        if self.model_name != model_name:
            return

        if self.console:
            self.console.append_to_console(
                f"Orbit View ({self.model_name}): Received data for {tag_name} - {len(values)} channels"
            )

        if not values or len(values) < 4:
            if self.console:
                self.console.append_to_console("Need at least 4 channels for orbit plot.")
            self.update_plots_with_sine_data()
            return

        for i in range(min(4, len(values))):
            self.channel_data[i] = np.array(values[i][:self.samples_per_channel])

        data_lengths = [len(self.channel_data[i]) for i in range(4)]
        if len(set(data_lengths)) != 1:
            if self.console:
                self.console.append_to_console(f"Mismatched data lengths: {data_lengths}")
            self.update_plots_with_sine_data()
            return

        for i, (ch_x, ch_y) in enumerate(self.selected_pairs):
            x_data = self.channel_data[ch_x]
            y_data = self.channel_data[ch_y]
            self.data_plots[i].setData(x_data, y_data)

            if (ch_x, ch_y) in [(0, 1), (2, 3)]:
                radius = np.sqrt((x_data - self.offset)**2 + (y_data - self.offset)**2)
                mean_radius = np.mean(radius)
                std_radius = np.std(radius)
                if std_radius / mean_radius < 0.01:
                    if self.console:
                        self.console.append_to_console(f"Orbit (Ch {ch_x+1}, Ch {ch_y+1}) is circular, radius: {mean_radius:.2f}")
                else:
                    if self.console:
                        self.console.append_to_console(f"Orbit (Ch {ch_x+1}, Ch {ch_y+1}) is not circular, std/mean: {std_radius/mean_radius:.4f}")

        channels_to_plot = set(ch for pair in self.selected_pairs for ch in pair)
        time = np.linspace(self.current_time, self.current_time + 1.0, self.samples_per_channel, endpoint=False)
        for i, ch in enumerate(sorted(channels_to_plot)):
            if i < len(self.time_plots):
                self.time_plots[i].setData(time, self.channel_data[ch])

    def get_widget(self):
        return self.widget