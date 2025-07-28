from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QHBoxLayout
import pyqtgraph as pg
import numpy as np
import logging

class OrbitFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None, channel_count=4):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.selected_channel = channel
        self.model_name = model_name
        self.console = console
        self.channel_count = channel_count
        self.widget = None
        self.plot_widgets = []
        self.plot_items = []
        self.data_plots = []
        self.time_plot_widgets = []
        self.time_plots = []
        self.channel_data = [[] for _ in range(channel_count)]
        self.primary_channel = 0
        self.secondary_channel = 1
        self.sample_rate = None
        self.samples_per_channel = None
        self.current_time = 0.0
        self.initUI()
        if self.console:
            self.console.append_to_console(f"Initialized OrbitFeature for {self.model_name}/{self.selected_channel or 'No Channel'} with {self.channel_count} channels")

    def initUI(self):
        self.widget = QWidget()
        main_layout = QVBoxLayout()
        self.widget.setLayout(main_layout)

        # Primary channel selection combo box
        primary_label = QLabel("Primary Channel:")
        self.primary_combo = QComboBox()
        self.primary_combo.setStyleSheet("""
            QComboBox {
                font-size: 16px;
                padding: 5px;
                background-color: white;
            }
            QComboBox QAbstractItemView {
                font-size: 16px;
                background-color: white;
            }
        """)
        self.primary_combo.currentIndexChanged.connect(self.on_primary_combo_changed)

        # Secondary channel selection combo box
        secondary_label = QLabel("Secondary Channel:")
        self.secondary_combo = QComboBox()
        self.secondary_combo.setStyleSheet("""
            QComboBox {
                font-size: 16px;
                padding: 5px;
                background-color: white;
            }
            QComboBox QAbstractItemView {
                font-size: 16px;
                background-color: white;
            }
        """)
        self.secondary_combo.currentIndexChanged.connect(self.on_secondary_combo_changed)

        # Add combo boxes to layout
        combo_layout = QHBoxLayout()
        combo_layout.addWidget(primary_label)
        combo_layout.addWidget(self.primary_combo)
        combo_layout.addWidget(secondary_label)
        combo_layout.addWidget(self.secondary_combo)
        main_layout.addLayout(combo_layout)

        # Layout for plots
        self.plot_layout = QHBoxLayout()
        main_layout.addLayout(self.plot_layout)

        # Initialize plots
        self.load_channel_data()
        self.recreate_plots()

        if not self.model_name and self.console:
            self.console.append_to_console("No model selected in OrbitFeature.")

    def load_channel_data(self):
        try:
            if not self.db.is_connected():
                self.db.reconnect()
            project_data = self.db.get_project_data(self.project_name)
            if not project_data:
                if self.console:
                    self.console.append_to_console(f"Project {self.project_name} not found")
                return
            model = next((m for m in project_data.get("models", []) if m["name"] == self.model_name), None)
            if not model:
                if self.console:
                    self.console.append_to_console(f"Model {self.model_name} not found")
                return
            channels = [ch.get("channelName", f"Channel_{i+1}") for i, ch in enumerate(model.get("channels", []))]
            if len(channels) != self.channel_count:
                if self.console:
                    self.console.append_to_console(f"Warning: Model {self.model_name} has {len(channels)} channels, expected {self.channel_count}")
            self.primary_combo.clear()
            self.secondary_combo.clear()
            self.primary_combo.addItems(channels)
            self.secondary_combo.addItems(channels)
            if self.selected_channel and self.selected_channel in channels:
                idx = channels.index(self.selected_channel)
                self.primary_channel = idx
                self.secondary_channel = (idx + 1) % len(channels) if len(channels) > 1 else idx
                self.primary_combo.setCurrentIndex(self.primary_channel)
                self.secondary_combo.setCurrentIndex(self.secondary_channel)
                if self.console:
                    self.console.append_to_console(f"Set primary channel to {self.selected_channel} (index {idx}), secondary to index {self.secondary_channel}")
        except Exception as e:
            if self.console:
                self.console.append_to_console(f"Error loading channel data: {str(e)}")
            logging.error(f"Error loading channel data for OrbitFeature: {str(e)}")

    def get_channel_index(self, channel_name):
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

    def on_primary_combo_changed(self, index):
        self.primary_channel = index
        self.recreate_plots()
        if self.console:
            self.console.append_to_console(f"Selected primary channel: Channel {self.primary_channel + 1}")

    def on_secondary_combo_changed(self, index):
        self.secondary_channel = index
        self.recreate_plots()
        if self.console:
            self.console.append_to_console(f"Selected secondary channel: Channel {self.secondary_channel + 1}")

    def recreate_plots(self):
        for plot_widget in self.plot_widgets + self.time_plot_widgets:
            plot_widget.deleteLater()
        self.plot_widgets = []
        self.plot_items = []
        self.data_plots = []
        self.time_plot_widgets = []
        self.time_plots = []

        while self.plot_layout.count():
            item = self.plot_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                item.layout().deleteLater()

        plot_widget = pg.PlotWidget()
        plot_widget.setBackground('w')
        plot_widget.setFixedSize(500, 500)
        self.plot_layout.addWidget(plot_widget)
        plot_item = plot_widget.getPlotItem()
        plot_item.setTitle(f"Orbit Plot (Ch {self.secondary_channel + 1} vs Ch {self.primary_channel + 1})")
        plot_item.setLabel('bottom', f"Channel {self.primary_channel + 1}")
        plot_item.setLabel('left', f"Channel {self.secondary_channel + 1}")
        plot_item.showGrid(x=True, y=True)
        plot_item.setAspectLocked(True)
        plot_item.enableAutoRange('xy', True)
        data_plot = plot_item.plot(pen=pg.mkPen('b', width=2))
        self.plot_widgets.append(plot_widget)
        self.plot_items.append(plot_item)
        self.data_plots.append(data_plot)

        time_colors = ['r', 'g', 'b', 'y', 'c', 'm', 'k', 'b', '#FF4500', '#32CD32', '#00CED1', '#FFD700', '#FF69B4', '#8A2BE2', '#FF6347', '#20B2AA', '#ADFF2F', '#9932CC', '#FF7F50', '#00FA9A', '#9400D3']
        for ch in [self.primary_channel, self.secondary_channel]:
            time_plot_widget = pg.PlotWidget()
            time_plot_widget.setBackground('w')
            time_plot_widget.setFixedSize(500, 500)
            self.plot_layout.addWidget(time_plot_widget)
            time_plot_item = time_plot_widget.getPlotItem()
            time_plot_item.setTitle(f"Channel {ch + 1} Time Domain")
            time_plot_item.setLabel('bottom', "Time (s)")
            time_plot_item.setLabel('left', f"Channel {ch + 1} Value")
            time_plot_item.showGrid(x=True, y=True)
            time_plot = time_plot_item.plot(pen=pg.mkPen(time_colors[ch % len(time_colors)], width=2))
            self.time_plot_widgets.append(time_plot_widget)
            self.time_plots.append(time_plot)

    def on_data_received(self, tag_name, model_name, values, sample_rate):
        if self.model_name != model_name:
            return

        try:
            if len(values) < self.channel_count:
                if self.console:
                    self.console.append_to_console(f"Received {len(values)} channels, expected at least {self.channel_count}")
                return

            if self.console:
                self.console.append_to_console(
                    f"Orbit View ({self.model_name}): Received data for {tag_name} - {len(values)} channels"
                )

            self.sample_rate = sample_rate
            self.samples_per_channel = len(values[0])

            for i in range(min(self.channel_count, len(values))):
                self.channel_data[i] = np.array(values[i][:self.samples_per_channel])

            data_lengths = [len(self.channel_data[i]) for i in range(min(self.channel_count, len(values)))]
            if len(set(data_lengths)) != 1:
                if self.console:
                    self.console.append_to_console(f"Mismatched data lengths: {data_lengths}")
                return

            x_data = self.channel_data[self.primary_channel]
            y_data = self.channel_data[self.secondary_channel]
            if self.data_plots:
                self.data_plots[0].setData(x_data, y_data)

            time = np.linspace(self.current_time, self.current_time + self.samples_per_channel / self.sample_rate, self.samples_per_channel, endpoint=False)
            self.current_time += self.samples_per_channel / self.sample_rate
            for i, ch in enumerate([self.primary_channel, self.secondary_channel]):
                if i < len(self.time_plots):
                    self.time_plots[i].setData(time, self.channel_data[ch])
        except Exception as e:
            if self.console:
                self.console.append_to_console(f"Error processing orbit data: {str(e)}")
            logging.error(f"Error processing orbit data: {str(e)}")

    def update_selected_channel(self, channel_name):
        try:
            self.selected_channel = channel_name
            channel_idx = self.get_channel_index(channel_name)
            if channel_idx is not None:
                self.primary_channel = channel_idx
                channels = [self.primary_combo.itemText(i) for i in range(self.primary_combo.count())]
                self.secondary_channel = (channel_idx + 1) % len(channels) if len(channels) > 1 else channel_idx
                self.primary_combo.setCurrentIndex(self.primary_channel)
                self.secondary_combo.setCurrentIndex(self.secondary_channel)
                if self.console:
                    self.console.append_to_console(f"Updated selected channel to: {self.selected_channel} (index {self.primary_channel}, secondary index {self.secondary_channel})")
            else:
                if self.console:
                    self.console.append_to_console(f"Channel {channel_name} not found, keeping current selection")
            self.recreate_plots()
        except Exception as e:
            if self.console:
                self.console.append_to_console(f"Error in update_selected_channel for {channel_name}: {str(e)}")
            logging.error(f"Error in update_selected_channel for {channel_name}: {str(e)}")

    def get_widget(self):
        return self.widget

    def cleanup(self):
        for plot_widget in self.plot_widgets + self.time_plot_widgets:
            plot_widget.deleteLater()
        self.plot_widgets = []
        self.time_plot_widgets = []
        self.data_plots = []
        self.time_plots = []

    def refresh_channel_properties(self):
        self.load_channel_data()