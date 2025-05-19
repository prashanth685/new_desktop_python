from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
import pyqtgraph as pg
import numpy as np
from datetime import datetime
import logging
import time

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
        self.tag_to_channel = {}
        self.start_time = time.time()
        self.window_duration = 60.0  # 60 seconds window
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

        # Fetch tags from tags_collection
        try:
            tags = list(self.db.tags_collection.find({"project_name": self.project_name, "model_name": self.model_name, "email": self.db.email}))
            if not tags:
                if self.console:
                    self.console.append_to_console(f"No tags found for project {self.project_name}, model {self.model_name}")
                logging.warning(f"No tags found for project {self.project_name}, model {self.model_name}")
                self.tag_to_channel = {"dummy_tag": 0}
                self.number_of_channels = 1
            else:
                self.number_of_channels = len(tags)
                for idx, tag in enumerate(tags):
                    tag_name = tag["tag_name"]
                    self.tag_to_channel[tag_name] = idx
                logging.debug(f"Tag to channel mapping: {self.tag_to_channel}")
        except Exception as e:
            logging.error(f"Error fetching tags from tagcreated collection: {str(e)}")
            if self.console:
                self.console.append_to_console(f"Error fetching tags: {str(e)}")
            self.tag_to_channel = {"dummy_tag": 0}
            self.number_of_channels = 1

        # Initialize data and time buffers for each channel
        self.data_buffers = [[] for _ in range(self.number_of_channels)]
        self.time_buffers = [[] for _ in range(self.number_of_channels)]

        # Configure pyqtgraph
        pg.setConfigOption('background', 'k')
        pg.setConfigOption('foreground', 'w')

        # Create a plot for each tag
        for tag_name, channel_idx in self.tag_to_channel.items():
            plot_widget = pg.PlotWidget()
            plot_widget.setTitle(f"Tag: {tag_name}")
            plot_widget.setLabel('left', 'Value (m/s)')
            plot_widget.setLabel('bottom', 'Time (s)')
            plot_widget.showGrid(x=True, y=True)
            plot_widget.setXRange(-self.window_duration, 0)
            self.plots.append(plot_widget)
            layout.addWidget(plot_widget)
            logging.debug(f"Created plot for Tag {tag_name} (Channel {channel_idx})")

        # Load initial data from timeview_messages
        if self.model_name:
            messages = self.db.get_timeview_messages(self.project_name, self.model_name)
            if not messages:
                if self.console:
                    self.console.append_to_console(f"No timeview messages found for project {self.project_name}, model {self.model_name}")
                logging.warning(f"No timeview messages found for project {self.project_name}, model {self.model_name}")
                self.load_dummy_data()
            else:
                logging.debug(f"Found {len(messages)} timeview messages")
                self.load_initial_data(messages)
        else:
            self.load_dummy_data()

        logging.debug("Finished initializing UI for TimeViewFeature")

    def load_dummy_data(self):
        current_time = time.time()
        for tag_name, channel_idx in self.tag_to_channel.items():
            for t in np.linspace(-self.window_duration, 0, 100):
                self.time_buffers[channel_idx].append(t)
                self.data_buffers[channel_idx].append(np.sin(2 * np.pi * t / self.window_duration) + channel_idx)
            logging.debug(f"Added dummy data for tag {tag_name}, channel {channel_idx}")
        self.update_plots()

    def load_initial_data(self, messages):
        current_time = time.time()
        time_threshold = current_time - self.window_duration

        for msg in messages:
            try:
                timestamp = datetime.fromisoformat(msg["createdAt"]).timestamp()
                if timestamp < time_threshold:
                    logging.debug(f"Skipping message, too old: {msg['createdAt']}")
                    continue

                topic = msg.get("topic")
                if topic not in self.tag_to_channel:
                    logging.debug(f"Topic {topic} not in tag_to_channel mapping, skipping")
                    continue

                channel_idx = self.tag_to_channel[topic]
                values = msg.get("message", [])
                if not values:
                    logging.warning(f"No values in message for topic {topic}")
                    continue

                value = float(values[0]) if isinstance(values, list) and len(values) > 0 else float(values)
                time_offset = timestamp - current_time
                self.data_buffers[channel_idx].append(value)
                self.time_buffers[channel_idx].append(time_offset)
                logging.debug(f"Loaded data point for topic {topic} at time offset {time_offset}: {value}")

            except Exception as e:
                logging.error(f"Error processing message {msg}: {str(e)}")
                if self.console:
                    self.console.append_to_console(f"Error processing message for topic {topic}: {str(e)}")

        self.update_plots()

    def get_widget(self):
        logging.debug("Returning widget from TimeViewFeature")
        return self.widget

    def on_data_received(self, tag_name, model_name, values):
        logging.debug(f"Received data for tag {tag_name}, model {model_name}: {values}")
        if self.console:
            self.console.append_to_console(f"Time View ({self.model_name}): Received data for {tag_name} - {values}")

        if tag_name not in self.tag_to_channel:
            logging.warning(f"Tag {tag_name} not found in tag_to_channel mapping")
            if self.console:
                self.console.append_to_console(f"Tag {tag_name} not found in known tags")
            return

        channel_idx = self.tag_to_channel[tag_name]
        if not values:
            logging.warning(f"No values received for tag {tag_name}")
            if self.console:
                self.console.append_to_console(f"No values received for tag {tag_name}")
            return

        try:
            value = float(values[0]) if isinstance(values, list) and len(values) > 0 else float(values)
        except (ValueError, TypeError) as e:
            logging.error(f"Invalid value format for tag {tag_name}: {values}, error: {str(e)}")
            if self.console:
                self.console.append_to_console(f"Invalid value format for tag {tag_name}: {str(e)}")
            return

        current_time = time.time()
        time_offset = current_time - self.start_time

        self.data_buffers[channel_idx].append(value)
        self.time_buffers[channel_idx].append(time_offset)

        # Remove old data points
        while self.time_buffers[channel_idx] and (time_offset - self.time_buffers[channel_idx][0]) > self.window_duration:
            self.time_buffers[channel_idx].pop(0)
            self.data_buffers[channel_idx].pop(0)

        # Normalize time offsets to be between -window_duration and 0
        if self.time_buffers[channel_idx]:
            current_time = self.time_buffers[channel_idx][-1]
            for i in range(len(self.time_buffers[channel_idx])):
                self.time_buffers[channel_idx][i] = self.time_buffers[channel_idx][i] - current_time

        self.update_plots()
        logging.debug(f"Updated plot for tag {tag_name} with new data: {value}")

    def update_plots(self):
        for channel_idx, plot in enumerate(self.plots):
            plot.clear()
            if self.time_buffers[channel_idx] and self.data_buffers[channel_idx]:
                times = np.array(self.time_buffers[channel_idx])
                data = np.array(self.data_buffers[channel_idx])
                plot.plot(times, data, pen='g')
                plot.setXRange(-self.window_duration, 0)
                logging.debug(f"Plotted Channel {channel_idx} (Tag {list(self.tag_to_channel.keys())[channel_idx]}): {len(times)} points, time range {times[0]:.2f} to {times[-1]:.2f}")
            else:
                logging.debug(f"No data to plot for Channel {channel_idx} (Tag {list(self.tag_to_channel.keys())[channel_idx] if channel_idx < len(self.tag_to_channel) else 'Unknown'})")

    def cleanup(self):
        self.plots.clear()
        self.data_buffers.clear()
        self.time_buffers.clear()
        self.tag_to_channel.clear()
        if self.widget:
            self.widget.deleteLater()
            self.widget = None
            logging.debug("Cleaned up TimeViewFeature resources")