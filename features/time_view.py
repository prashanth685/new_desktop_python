# import numpy as np
# from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
# from pyqtgraph import PlotWidget, mkPen, AxisItem
# from datetime import datetime
# import time
# import logging

# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


# class TimeAxisItem(AxisItem):
#     """Custom axis to display datetime on x-axis."""
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

#     def tickStrings(self, values, scale, spacing):
#         """Convert timestamps to 'YYYY-MM-DD\nHH:MM:SS' format."""
#         return [datetime.fromtimestamp(v).strftime('%Y-%m-%d\n%H:%M:%S') for v in values]
    


# class TimeViewFeature:
#     def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None):
#         self.parent = parent
#         self.db = db
#         self.project_name = project_name
#         self.channel = channel
#         self.model_name = model_name
#         self.console = console
#         self.widget = None
#         self.plot_widgets = []
#         self.plots = []
#         self.data = []
#         self.times = []
#         self.sample_rate = 4096  # Default
#         self.num_channels = 4  # Default, updated from project data
#         self.initUI()
#         self.load_project_data()

#     def load_project_data(self):
#         """Load project data to determine number of channels."""
#         try:
#             project_data = self.db.get_project_data(self.project_name)
#             if project_data and "models" in project_data and self.model_name in project_data["models"]:
#                 model_data = project_data["models"][self.model_name]
#                 self.num_channels = len(model_data.get("channels", []))
#                 logging.debug(f"Loaded project data: {self.num_channels} channels for model {self.model_name}")
#             else:
#                 logging.warning(f"No valid model data found for {self.model_name}")
#                 if self.console:
#                     self.console.append_to_console(f"No valid model data for {self.model_name}")
#         except Exception as e:
#             logging.error(f"Error loading project data: {str(e)}")
#             if self.console:
#                 self.console.append_to_console(f"Error loading project data: {str(e)}")

#     def initUI(self):
#         """Initialize the UI with pyqtgraph subplots."""
#         self.widget = QWidget()
#         layout = QVBoxLayout()
#         self.widget.setLayout(layout)

#         layout.addWidget(QLabel(f"Time View for Model: {self.model_name}, Channels: {self.channel or 'All'}"))

#         # Create a subplot for each channel
#         colors = ['r', 'g', 'b', 'y']
#         for i in range(self.num_channels):
#             plot_widget = PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')}, background='w')
#             plot_widget.setLabel('left', f'CH{i+1} Value')
#             plot_widget.setLabel('bottom', 'Time')
#             plot_widget.showGrid(x=True, y=True)
#             plot_widget.addLegend()
#             pen = mkPen(color=colors[i % len(colors)], width=2)
#             plot = plot_widget.plot([], [], pen=pen)
#             self.plots.append(plot)
#             self.plot_widgets.append(plot_widget)
#             layout.addWidget(plot_widget)
#             self.data.append([])

#         if not self.model_name and self.console:
#             self.console.append_to_console("No model selected in TimeViewFeature.")
#         if not self.channel and self.console:
#             self.console.append_to_console("No channel selected in TimeViewFeature.")

#     def get_widget(self):
#         """Return the widget containing the plots."""
#         return self.widget

#     def on_data_received(self, tag_name, model_name, values, sample_rate):
#         """Handle incoming MQTT data and update the plots."""
#         logging.debug(f"on_data_received called with tag_name={tag_name}, model_name={model_name}, "
#                      f"values_len={len(values) if values else 0}, sample_rate={sample_rate}")
#         if self.model_name != model_name:
#             logging.debug(f"Ignoring data for model {model_name}, expected {self.model_name}")
#             return
#         try:
#             self.sample_rate = sample_rate
#             num_samples = len(values[0]) if values and len(values) > 0 else 0
#             if num_samples == 0:
#                 logging.warning("Received empty data values")
#                 if self.console:
#                     self.console.append_to_console("Received empty data values")
#                 return

#             # Generate timestamps for the 1-second window
#             current_time = time.time()
#             time_step = 1.0 / sample_rate
#             self.times = np.array([current_time - 1.0 + i * time_step for i in range(num_samples)])

#             # Update data for each channel
#             for ch in range(min(self.num_channels, len(values))):
#                 self.data[ch] = np.array(values[ch][:num_samples])

#             # Update each subplot
#             for ch in range(self.num_channels):
#                 if ch < len(values) and len(self.data[ch]) > 0:
#                     self.plots[ch].setData(self.times, self.data[ch])
#                     self.plot_widgets[ch].setXRange(self.times[0], self.times[-1], padding=0)
#                     self.plot_widgets[ch].enableAutoRange(axis='y')

#             logging.debug(f"Updated plots for {model_name}, {num_samples} samples, {self.num_channels} channels")
#             if self.console:
#                 self.console.append_to_console(
#                     f"Time View ({self.model_name}): Updated plots with {num_samples} samples"
#                 )
#         except Exception as e:
#             logging.error(f"Error updating plots: {str(e)}")
#             if self.console:
#                 self.console.append_to_console(f"Error updating plots: {str(e)}")





# import numpy as np
# from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
# from PyQt5.QtCore import QObject, QEvent
# from pyqtgraph import PlotWidget, mkPen, AxisItem, InfiniteLine, SignalProxy
# from datetime import datetime
# import time
# import logging

# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


# class TimeAxisItem(AxisItem):
#     """Custom axis to display datetime on x-axis."""
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

#     def tickStrings(self, values, scale, spacing):
#         """Convert timestamps to 'YYYY-MM-DD\nHH:MM:SS' format."""
#         return [datetime.fromtimestamp(v).strftime('%Y-%m-%d\n%H:%M:%S') for v in values]


# class MouseTracker(QObject):
#     """Event filter to track mouse enter/leave on plot viewport."""
#     def __init__(self, parent, idx, feature):
#         super().__init__(parent)
#         self.idx = idx
#         self.feature = feature

#     def eventFilter(self, obj, event):
#         if event.type() == QEvent.Enter:
#             self.feature.mouse_enter(self.idx)
#         elif event.type() == QEvent.Leave:
#             self.feature.mouse_leave(self.idx)
#         return False


# class TimeViewFeature:
#     def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None):
#         self.parent = parent
#         self.db = db
#         self.project_name = project_name
#         self.channel = channel
#         self.model_name = model_name
#         self.console = console

#         self.widget = None
#         self.plot_widgets = []
#         self.plots = []
#         self.data = []
#         self.times = []
#         self.sample_rate = 4096  # Default
#         self.num_channels = 4  # Default, updated from project data

#         # For synchronized vertical lines on hover
#         self.vlines = []
#         self.proxies = []
#         self.trackers = []

#         self.active_line_idx = None  # which subplot mouse is over

#         self.initUI()
#         self.load_project_data()

#     def load_project_data(self):
#         """Load project data to determine number of channels."""
#         try:
#             project_data = self.db.get_project_data(self.project_name)
#             if project_data and "models" in project_data and self.model_name in project_data["models"]:
#                 model_data = project_data["models"][self.model_name]
#                 self.num_channels = len(model_data.get("channels", []))
#                 logging.debug(f"Loaded project data: {self.num_channels} channels for model {self.model_name}")
#             else:
#                 logging.warning(f"No valid model data found for {self.model_name}")
#                 if self.console:
#                     self.console.append_to_console(f"No valid model data for {self.model_name}")
#         except Exception as e:
#             logging.error(f"Error loading project data: {str(e)}")
#             if self.console:
#                 self.console.append_to_console(f"Error loading project data: {str(e)}")

#     def initUI(self):
#         """Initialize the UI with pyqtgraph subplots."""
#         self.widget = QWidget()
#         layout = QVBoxLayout()
#         self.widget.setLayout(layout)

#         layout.addWidget(QLabel(f"Time View for Model: {self.model_name}, Channels: {self.channel or 'All'}"))

#         colors = ['r', 'g', 'b', 'y']
#         for i in range(self.num_channels):
#             plot_widget = PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')}, background='w')
#             plot_widget.setLabel('left', f'CH{i+1} Value')
#             plot_widget.setLabel('bottom', 'Time')
#             plot_widget.showGrid(x=True, y=True)
#             plot_widget.addLegend()
#             pen = mkPen(color=colors[i % len(colors)], width=2)
#             plot = plot_widget.plot([], [], pen=pen)
#             self.plots.append(plot)
#             self.plot_widgets.append(plot_widget)
#             self.data.append([])

#             # Add vertical line for hover sync, initially hidden
#             vline = InfiniteLine(angle=90, movable=False, pen=mkPen('r', width=1))
#             vline.setVisible(False)
#             plot_widget.addItem(vline)
#             self.vlines.append(vline)

#             # Setup mouse move proxy for this plot
#             proxy = SignalProxy(plot_widget.scene().sigMouseMoved, rateLimit=60, slot=lambda evt, idx=i: self.mouse_moved(evt, idx))
#             self.proxies.append(proxy)

#             # Install event filter on viewport for enter/leave detection
#             tracker = MouseTracker(plot_widget.viewport(), i, self)
#             plot_widget.viewport().installEventFilter(tracker)
#             self.trackers.append(tracker)

#             layout.addWidget(plot_widget)

#         if not self.model_name and self.console:
#             self.console.append_to_console("No model selected in TimeViewFeature.")
#         if not self.channel and self.console:
#             self.console.append_to_console("No channel selected in TimeViewFeature.")

#     def get_widget(self):
#         """Return the widget containing the plots."""
#         return self.widget

#     def on_data_received(self, tag_name, model_name, values, sample_rate):
#         """Handle incoming MQTT data and update the plots."""
#         logging.debug(f"on_data_received called with tag_name={tag_name}, model_name={model_name}, "
#                       f"values_len={len(values) if values else 0}, sample_rate={sample_rate}")
#         if self.model_name != model_name:
#             logging.debug(f"Ignoring data for model {model_name}, expected {self.model_name}")
#             return
#         try:
#             self.sample_rate = sample_rate
#             num_samples = len(values[0]) if values and len(values) > 0 else 0
#             if num_samples == 0:
#                 logging.warning("Received empty data values")
#                 if self.console:
#                     self.console.append_to_console("Received empty data values")
#                 return

#             # Generate timestamps for the 1-second window
#             current_time = time.time()
#             time_step = 1.0 / sample_rate
#             self.times = np.array([current_time - 1.0 + i * time_step for i in range(num_samples)])

#             # Update data for each channel
#             for ch in range(min(self.num_channels, len(values))):
#                 self.data[ch] = np.array(values[ch][:num_samples])

#             # Update each subplot
#             for ch in range(self.num_channels):
#                 if ch < len(values) and len(self.data[ch]) > 0:
#                     self.plots[ch].setData(self.times, self.data[ch])
#                     self.plot_widgets[ch].setXRange(self.times[0], self.times[-1], padding=0)
#                     self.plot_widgets[ch].enableAutoRange(axis='y')

#             logging.debug(f"Updated plots for {model_name}, {num_samples} samples, {self.num_channels} channels")
#             if self.console:
#                 self.console.append_to_console(
#                     f"Time View ({self.model_name}): Updated plots with {num_samples} samples"
#                 )
#         except Exception as e:
#             logging.error(f"Error updating plots: {str(e)}")
#             if self.console:
#                 self.console.append_to_console(f"Error updating plots: {str(e)}")

#     def mouse_enter(self, idx):
#         """Called when mouse enters plot idx viewport."""
#         self.active_line_idx = idx
#         # Show vertical line on that plot
#         self.vlines[idx].setVisible(True)
#         logging.debug(f"Mouse entered plot {idx}")

#     def mouse_leave(self, idx):
#         """Called when mouse leaves plot idx viewport."""
#         self.active_line_idx = None
#         # Hide all vertical lines
#         for vline in self.vlines:
#             vline.setVisible(False)
#         logging.debug(f"Mouse left plot {idx}")

#     def mouse_moved(self, evt, idx):
#         """Update vertical lines on mouse move."""
#         if self.active_line_idx is None:
#             # Mouse not inside any plot viewport
#             return

#         # Get mouse point in plot coordinates
#         pos = evt[0]  # Pyqtgraph wraps event arguments in a tuple
#         if not self.plot_widgets[idx].sceneBoundingRect().contains(pos):
#             return

#         mouse_point = self.plot_widgets[idx].plotItem.vb.mapSceneToView(pos)
#         x = mouse_point.x()

#         # Clamp x within the data range if possible
#         if len(self.times) > 0:
#             if x < self.times[0]:
#                 x = self.times[0]
#             elif x > self.times[-1]:
#                 x = self.times[-1]

#         # Update vertical line position for all plots
#         for vline in self.vlines:
#             vline.setPos(x)
#             vline.setVisible(True)






import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import QObject, QEvent, Qt
from pyqtgraph import PlotWidget, mkPen, AxisItem, InfiniteLine, SignalProxy
from datetime import datetime
import time
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class TimeAxisItem(AxisItem):
    """Custom axis to display datetime on x-axis."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        """Convert timestamps to 'YYYY-MM-DD\nHH:MM:SS' format."""
        return [datetime.fromtimestamp(v).strftime('%Y-%m-%d\n%H:%M:%S') for v in values]

class MouseTracker(QObject):
    """Event filter to track mouse enter/leave on plot viewport."""
    def __init__(self, parent, idx, feature):
        super().__init__(parent)
        self.idx = idx
        self.feature = feature

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Enter:
            self.feature.mouse_enter(self.idx)
        elif event.type() == QEvent.Leave:
            self.feature.mouse_leave(self.idx)
        return False

class TimeViewFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None):
        super().__init__()
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.channel = channel
        self.model_name = model_name
        self.console = console

        self.widget = None
        self.plot_widgets = []
        self.plots = []
        self.data = []
        self.channel_times = []  # Timestamps for channel data
        self.tacho_times = []   # Timestamps for tacho data
        self.sample_rate = 4096  # Default
        self.num_channels = 4    # Plot 4 channels
        self.num_plots = 6       # 4 channels + tacho freq + tacho trigger
        self.channel_samples = 4096  # Samples per channel
        self.tacho_samples = 4096    # Samples for tacho data

        # For synchronized vertical lines on hover
        self.vlines = []
        self.proxies = []
        self.trackers = []

        # For tacho trigger strip lines
        self.trigger_lines = []

        self.active_line_idx = None  # which subplot mouse is over

        self.initUI()
        self.load_project_data()

    def load_project_data(self):
        """Load project data to determine number of channels."""
        try:
            project_data = self.db.get_project_data(self.project_name)
            if project_data and "models" in project_data and self.model_name in project_data["models"]:
                model_data = project_data["models"][self.model_name]
                available_channels = len(model_data.get("channels", []))
                self.num_channels = min(available_channels, 4)  # Use up to 4 channels
                logging.debug(f"Loaded project data: {self.num_channels} channels for model {self.model_name}")
            else:
                logging.warning(f"No valid model data found for {self.model_name}")
                if self.console:
                    self.console.append_to_console(f"No valid model data for {self.model_name}")
        except Exception as e:
            logging.error(f"Error loading project data: {str(e)}")
            if self.console:
                self.console.append_to_console(f"Error loading project data: {str(e)}")

    def initUI(self):
        """Initialize the UI with pyqtgraph subplots."""
        self.widget = QWidget()
        layout = QVBoxLayout()
        self.widget.setLayout(layout)

        layout.addWidget(QLabel(f"Time View for Model: {self.model_name}, Channels: {self.channel or 'All'}"))

        colors = ['r', 'g', 'b', 'y', 'c', 'm']  # Colors for 4 channels, tacho freq, tacho trigger
        for i in range(self.num_plots):
            plot_widget = PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')}, background='w')
            if i < self.num_channels:
                plot_widget.setLabel('left', f'CH{i+1} Value')
            elif i == self.num_channels:
                plot_widget.setLabel('left', 'Tacho Frequency')
            else:
                plot_widget.setLabel('left', 'Tacho Trigger')
                plot_widget.setYRange(-0.5, 1.5, padding=0)  # Binary data range
            plot_widget.setLabel('bottom', 'Time')
            plot_widget.showGrid(x=True, y=True)
            plot_widget.addLegend()
            pen = mkPen(color=colors[i % len(colors)], width=2)
            plot = plot_widget.plot([], [], pen=pen)
            self.plots.append(plot)
            self.plot_widgets.append(plot_widget)
            self.data.append([])

            # Add vertical line for hover sync, initially hidden
            vline = InfiniteLine(angle=90, movable=False, pen=mkPen('r', width=1))
            vline.setVisible(False)
            plot_widget.addItem(vline)
            self.vlines.append(vline)

            # Initialize trigger lines for tacho trigger subplot
            if i == self.num_plots - 1:  # Tacho trigger plot
                self.trigger_lines = []
            else:
                self.trigger_lines.append(None)  # Placeholder for non-trigger plots

            # Setup mouse move proxy for this plot
            proxy = SignalProxy(plot_widget.scene().sigMouseMoved, rateLimit=60, slot=lambda evt, idx=i: self.mouse_moved(evt, idx))
            self.proxies.append(proxy)

            # Install event filter on viewport for enter/leave detection
            tracker = MouseTracker(plot_widget.viewport(), i, self)
            plot_widget.viewport().installEventFilter(tracker)
            self.trackers.append(tracker)

            layout.addWidget(plot_widget)

        if not self.model_name and self.console:
            self.console.append_to_console("No model selected in TimeViewFeature.")
        if not self.channel and self.console:
            self.console.append_to_console("No channel selected in TimeViewFeature.")

    def get_widget(self):
        """Return the widget containing the plots."""
        return self.widget

    def on_data_received(self, tag_name, model_name, values, sample_rate):
        """Handle incoming MQTT data and update the plots."""
        logging.debug(f"on_data_received called with tag_name={tag_name}, model_name={model_name}, "
                     f"values_len={len(values) if values else 0}, sample_rate={sample_rate}")
        if self.model_name != model_name:
            logging.debug(f"Ignoring data for model {model_name}, expected {self.model_name}")
            return
        try:
            # Expect 6 sublists (4 channels + tacho freq + tacho trigger)
            if not values or len(values) < 6:
                logging.warning(f"Received insufficient data: {len(values)} sublists, expected 6")
                if self.console:
                    self.console.append_to_console(f"Received insufficient data: {len(values)} sublists")
                return

            self.sample_rate = sample_rate
            channel_samples = len(values[0]) if values and len(values) > 0 else 0
            if channel_samples != self.channel_samples:
                logging.warning(f"Unexpected channel sample count: {channel_samples}, expected {self.channel_samples}")
                if self.console:
                    self.console.append_to_console(f"Unexpected channel sample count: {channel_samples}")
                return

            # Validate tacho data lengths
            tacho_freq_samples = len(values[4]) if len(values) > 4 else 0
            tacho_trigger_samples = len(values[5]) if len(values) > 5 else 0
            if tacho_freq_samples != self.tacho_samples or tacho_trigger_samples != self.tacho_samples:
                logging.warning(f"Tacho data length mismatch: freq={tacho_freq_samples}, trigger={tacho_trigger_samples}, expected={self.tacho_samples}")
                if self.console:
                    self.console.append_to_console(f"Tacho data length mismatch: freq={tacho_freq_samples}, trigger={tacho_trigger_samples}")
                return

            # Generate timestamps for channel and tacho data (4096 samples, 1-second window)
            current_time = time.time()
            time_step = 1.0 / sample_rate
            self.channel_times = np.array([current_time - 1.0 + i * time_step for i in range(channel_samples)])
            self.tacho_times = np.array([current_time - 1.0 + i * time_step for i in range(self.tacho_samples)])

            # Update channel data (first 4 channels from values[0:4])
            for ch in range(self.num_channels):
                self.data[ch] = np.array(values[ch][:channel_samples])
                logging.debug(f"Channel {ch+1} data: {len(self.data[ch])} samples")

            # Update tacho frequency and trigger data (values[4] and values[5])
            self.data[self.num_channels] = np.array(values[4][:self.tacho_samples])
            self.data[self.num_channels + 1] = np.array(values[5][:self.tacho_samples])
            logging.debug(f"Tacho freq data: {len(self.data[self.num_channels])} samples")
            logging.debug(f"Tacho trigger data: {len(self.data[self.num_channels + 1])} samples, first 10: {self.data[self.num_channels + 1][:10]}")

            # Update each subplot
            for ch in range(self.num_plots):
                times = self.tacho_times if ch >= self.num_channels else self.channel_times
                if ch < len(self.data) and len(self.data[ch]) > 0 and len(times) > 0:
                    self.plots[ch].setData(times, self.data[ch])
                    self.plot_widgets[ch].setXRange(times[0], times[-1], padding=0)
                    if ch < self.num_channels:
                        self.plot_widgets[ch].enableAutoRange(axis='y')
                    elif ch == self.num_channels:
                        self.plot_widgets[ch].enableAutoRange(axis='y')  # Tacho freq
                    else:
                        self.plot_widgets[ch].setYRange(-0.5, 1.5, padding=0)  # Tacho trigger
                else:
                    logging.warning(f"No data for plot {ch}, data_len={len(self.data[ch])}, times_len={len(times)}")
                    if self.console:
                        self.console.append_to_console(f"No data for plot {ch}")

            # Add strip lines for tacho trigger (value == 1)
            if len(self.data[self.num_channels + 1]) > 0:
                # Clear previous trigger lines
                if self.trigger_lines[self.num_plots - 1] is not None:
                    for line in self.trigger_lines[self.num_plots - 1]:
                        self.plot_widgets[self.num_plots - 1].removeItem(line)
                self.trigger_lines[self.num_plots - 1] = []

                # Find indices where trigger is 1
                trigger_indices = np.where(self.data[self.num_plots - 1] == 1)[0]
                logging.debug(f"Tacho trigger indices (value=1): {len(trigger_indices)} points")
                for idx in trigger_indices:
                    if idx < len(self.tacho_times):
                        line = InfiniteLine(
                            pos=self.tacho_times[idx],
                            angle=90,
                            movable=False,
                            pen=mkPen('k', width=2, style=Qt.SolidLine)
                        )
                        self.plot_widgets[self.num_plots - 1].addItem(line)
                        self.trigger_lines[self.num_plots - 1].append(line)

            logging.debug(f"Updated {self.num_plots} plots: {channel_samples} channel samples, {self.tacho_samples} tacho samples")
            if self.console:
                self.console.append_to_console(
                    f"Time View ({self.model_name}): Updated {self.num_plots} plots with {channel_samples} channel samples, {self.tacho_samples} tacho samples"
                )
        except Exception as e:
            logging.error(f"Error updating plots: {str(e)}")
            if self.console:
                self.console.append_to_console(f"Error updating plots: {str(e)}")

    def mouse_enter(self, idx):
        """Called when mouse enters plot idx viewport."""
        self.active_line_idx = idx
        self.vlines[idx].setVisible(True)
        logging.debug(f"Mouse entered plot {idx}")

    def mouse_leave(self, idx):
        """Called when mouse leaves plot idx viewport."""
        self.active_line_idx = None
        for vline in self.vlines:
            vline.setVisible(False)
        logging.debug(f"Mouse left plot {idx}")

    def mouse_moved(self, evt, idx):
        """Update vertical lines on mouse move."""
        if self.active_line_idx is None:
            return

        pos = evt[0]
        if not self.plot_widgets[idx].sceneBoundingRect().contains(pos):
            return

        mouse_point = self.plot_widgets[idx].plotItem.vb.mapSceneToView(pos)
        x = mouse_point.x()

        times = self.tacho_times if idx >= self.num_channels else self.channel_times
        if len(times) > 0:
            if x < times[0]:
                x = times[0]
            elif x > times[-1]:
                x = times[-1]

        for vline in self.vlines:
            vline.setPos(x)
            vline.setVisible(True)