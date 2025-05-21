from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
import pyqtgraph as pg
import numpy as np
from datetime import datetime
import logging
import time
import struct

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class TimeViewFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.channel = channel
        self.model_name = model_name
        self.console = console
        self.widget = None
        self.plots = []
        self.data_buffers = []
        self.time_buffers = []
        self.tag_to_idx = {}
        self.start_time = time.time()
        self.window_duration = 1.0
        self.num_channels = 4
        logging.debug(f"Initializing TimeViewFeature with project_name: {project_name}, model_name: {model_name}")
        self.initUI()

    def initUI(self):
        self.widget = QWidget()
        layout = QVBoxLayout()
        self.widget.setLayout(layout)

        label_text = f"Time View for Model: {self.model_name if self.model_name else 'None'}"
        label = QLabel(label_text)
        layout.addWidget(label)
        logging.debug(f"Set label text: {label_text}")

        try:
            project_data = self.db.get_project_data(self.project_name)
            if not project_data or "models" not in project_data or self.model_name not in project_data["models"]:
                if self.console:
                    self.console.append_to_console(f"No model {self.model_name} found for project {self.project_name}")
                logging.error(f"No model {self.model_name} found for project {self.project_name}")
                return
            tag_name = project_data["models"][self.model_name].get("tagName", "")
            if not tag_name:
                if self.console:
                    self.console.append_to_console(f"No tag found for model {self.model_name} in project {self.project_name}")
                logging.error(f"No tag found for model {self.model_name} in project {self.project_name}")
                return
            self.tags = [{"tag_name": tag_name}]
            self.number_of_tags = len(self.tags)
            for idx, tag in enumerate(self.tags):
                self.tag_to_idx[tag["tag_name"]] = idx
            logging.debug(f"Tag to index mapping: {self.tag_to_idx}")
        except Exception as e:
            logging.error(f"Error fetching tags: {str(e)}")
            if self.console:
                self.console.append_to_console(f"Error fetching tags: {str(e)}")
            return

        self.data_buffers = [[[] for _ in range(self.num_channels)] for _ in range(self.number_of_tags)]
        self.time_buffers = [[[] for _ in range(self.num_channels)] for _ in range(self.number_of_tags)]

        pg.setConfigOption('background', 'k')
        pg.setConfigOption('foreground', 'w')

        self.plots = [[None for _ in range(self.num_channels)] for _ in range(self.number_of_tags)]
        for tag_idx in range(self.number_of_tags):
            tag_name = self.tags[tag_idx]["tag_name"]
            for channel in range(self.num_channels):
                plot_widget = pg.PlotWidget()
                plot_widget.setTitle(f"Tag: {tag_name}, Channel: {channel}")
                plot_widget.setLabel('left', 'Value (m/s)')
                plot_widget.setLabel('bottom', 'Time')
                plot_widget.showGrid(x=True, y=True)
                axis = pg.DateAxisItem(orientation='bottom')
                plot_widget.setAxisItems({'bottom': axis})
                self.plots[tag_idx][channel] = plot_widget
                layout.addWidget(plot_widget)
                logging.debug(f"Created plot for Tag {tag_name}, Channel {channel}")

        if self.model_name:
            messages = self.db.get_timeview_messages(self.project_name, self.model_name)
            if not messages:
                if self.console:
                    self.console.append_to_console(f"No timeview messages found for project {self.project_name}, model {self.model_name}")
                logging.warning(f"No timeview messages found for project {self.project_name}, model {self.model_name}")
            else:
                logging.debug(f"Found {len(messages)} timeview messages")
                self.load_initial_data(messages)

        logging.debug("Finished initializing UI")

    def load_initial_data(self, messages):
        current_time = time.time()
        time_threshold = current_time - self.window_duration
        for msg in messages:
            try:
                timestamp = datetime.fromisoformat(msg["createdAt"]).timestamp()
                if timestamp < time_threshold:
                    continue
                tag_name = msg.get("topic")
                if tag_name not in self.tag_to_idx:
                    continue
                tag_idx = self.tag_to_idx[tag_name]
                binary_message = msg.get("message")
                if not binary_message:
                    continue
                header_size = 10
                values = struct.unpack(f"<{header_size}H{16384}H", binary_message)
                frame_index, _, num_channels, sample_rate, _, _, _, _, _, _ = values[:header_size]
                data = values[header_size:]
                samples_per_channel = len(data) // num_channels
                time_per_sample = 1.0 / sample_rate if sample_rate > 0 else 0
                for channel in range(min(self.num_channels, num_channels)):
                    channel_values = data[channel * samples_per_channel:(channel + 1) * samples_per_channel]
                    for i in range(10, len(channel_values)):
                        time_offset = timestamp + (i * time_per_sample)
                        if time_offset >= time_threshold:
                            self.data_buffers[tag_idx][channel].append(float(channel_values[i]))
                            self.time_buffers[tag_idx][channel].append(time_offset)
            except Exception as e:
                logging.error(f"Error processing message {msg}: {str(e)}")
        self.update_plots()

    def get_widget(self):
        logging.debug("Returning widget")
        return self.widget

    def on_data_received(self, tag_name, model_name, values, sample_rate):
        if model_name != self.model_name:
            return
        logging.debug(f"Received data for {tag_name}/{model_name}: {len(values)} channels, sample_rate={sample_rate}")
        if self.console:
            self.console.append_to_console(f"Time View ({self.model_name}): Received data for {tag_name}")

        if tag_name not in self.tag_to_idx:
            logging.warning(f"Tag {tag_name} not found")
            return

        tag_idx = self.tag_to_idx[tag_name]
        if len(values) != self.num_channels:
            logging.warning(f"Expected {self.num_channels} channels, got {len(values)}")
            return

        current_time = time.time()
        time_per_sample = 1.0 / sample_rate if sample_rate > 0 else 0
        time_threshold = current_time - self.window_duration
        num_samples = len(values[0]) if values else 0

        for channel in range(self.num_channels):
            channel_values = values[channel]
            if len(channel_values) != num_samples:
                logging.warning(f"Inconsistent samples for channel {channel}")
                continue

            for i in range(10, num_samples):
                time_offset = current_time + (i * time_per_sample)
                if time_offset >= time_threshold:
                    self.time_buffers[tag_idx][channel].append(time_offset)
                    self.data_buffers[tag_idx][channel].append(float(channel_values[i]))

            while self.time_buffers[tag_idx][channel] and (self.time_buffers[tag_idx][channel][-1] - self.time_buffers[tag_idx][channel][0]) > self.window_duration:
                self.time_buffers[tag_idx][channel].pop(0)
                self.data_buffers[tag_idx][channel].pop(0)

        self.update_plots()

    def update_plots(self):
        for tag_idx in range(self.number_of_tags):
            for channel in range(self.num_channels):
                plot = self.plots[tag_idx][channel]
                plot.clear()
                if self.time_buffers[tag_idx][channel] and self.data_buffers[tag_idx][channel]:
                    times = np.array(self.time_buffers[tag_idx][channel])
                    data = np.array(self.data_buffers[tag_idx][channel])
                    plot.plot(times, data, pen='g')
                    if len(times) > 0:
                        plot.setXRange(times[-1] - self.window_duration, times[-1])
                    logging.debug(f"Plotted Tag {tag_idx}, Channel {channel}: {len(times)} points")

    def cleanup(self):
        for tag_plots in self.plots:
            for plot in tag_plots:
                plot.clear()
        self.plots = []
        self.data_buffers = []
        self.time_buffers = []
        self.tag_to_idx = {}
        if self.widget:
            self.widget.deleteLater()
            self.widget = None
            logging.debug("Cleaned up resources")