# from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QPushButton, QLineEdit
# from PyQt5.QtCore import QObject, QEvent, Qt
# from pyqtgraph import PlotWidget, mkPen, AxisItem, InfiniteLine, SignalProxy
# from datetime import datetime
# import numpy as np
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

# class TimeReportFeature:
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
#         self.channel_times = []
#         self.tacho_times = []
#         self.vlines = []
#         self.proxies = []
#         self.trackers = []
#         self.trigger_lines = []
#         self.active_line_idx = None
#         self.num_channels = 4
#         self.num_plots = 6
#         self.sample_rate = 4096
#         self.filenames = []
#         self.selected_filename = None
#         self.start_time = None
#         self.end_time = None

#         self.initUI()
#         self.refresh_filenames()

#     def initUI(self):
#         """Initialize the UI with filename selector, time range inputs, and pyqtgraph subplots."""
#         self.widget = QWidget()
#         layout = QVBoxLayout()
#         self.widget.setLayout(layout)

#         # Add filename selector
#         layout.addWidget(QLabel(f"Time Report for Model: {self.model_name}, Channel: {self.channel or 'All'}"))
#         self.filename_combo = QComboBox()
#         self.filename_combo.addItem("Select Filename")
#         self.filename_combo.currentIndexChanged.connect(self.on_filename_selected)
#         layout.addWidget(self.filename_combo)

#         # Initialize plots
#         colors = ['r', 'g', 'b', 'y', 'c', 'm']
#         for i in range(self.num_plots):
#             plot_widget = PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')}, background='w')
#             if i < self.num_channels:
#                 plot_widget.setLabel('left', f'CH{i+1} Value')
#             elif i == self.num_channels:
#                 plot_widget.setLabel('left', 'Tacho Frequency')
#             else:
#                 plot_widget.setLabel('left', 'Tacho Trigger')
#                 plot_widget.setYRange(-0.5, 1.5, padding=0)
#             plot_widget.setLabel('bottom', 'Time')
#             plot_widget.showGrid(x=True, y=True)
#             plot_widget.addLegend()
#             pen = mkPen(color=colors[i % len(colors)], width=2)
#             plot = plot_widget.plot([], [], pen=pen)
#             self.plots.append(plot)
#             self.plot_widgets.append(plot_widget)
#             self.data.append([])

#             vline = InfiniteLine(angle=90, movable=False, pen=mkPen('r', width=2))
#             vline.setVisible(False)
#             plot_widget.addItem(vline)
#             self.vlines.append(vline)

#             if i == self.num_plots - 1:
#                 self.trigger_lines = []
#             else:
#                 self.trigger_lines.append(None)

#             proxy = SignalProxy(plot_widget.scene().sigMouseMoved, rateLimit=60, slot=lambda evt, idx=i: self.mouse_moved(evt, idx))
#             self.proxies.append(proxy)

#             tracker = MouseTracker(plot_widget.viewport(), i, self)
#             plot_widget.viewport().installEventFilter(tracker)
#             self.trackers.append(tracker)

#             layout.addWidget(plot_widget)

#         if not self.model_name and self.console:
#             self.console.append_to_console("No model selected in TimeReportFeature.")
#         if not self.channel and self.console:
#             self.console.append_to_console("No channel selected in TimeReportFeature.")

#     def get_widget(self):
#         """Return the widget containing the plots."""
#         return self.widget

#     def refresh_filenames(self):
#         """Retrieve distinct filenames from the database and update combo box."""
#         try:
#             self.filenames = self.db.get_distinct_filenames(self.project_name, self.model_name)
#             self.filename_combo.clear()
#             self.filename_combo.addItem("Select Filename")
#             self.filename_combo.addItems(self.filenames)
#             logging.debug(f"Refreshed filenames: {self.filenames}")
#             if self.console:
#                 self.console.append_to_console(f"Refreshed filenames: {len(self.filenames)} found")
#         except Exception as e:
#             logging.error(f"Error refreshing filenames: {str(e)}")
#             if self.console:
#                 self.console.append_to_console(f"Error refreshing filenames: {str(e)}")

#     def on_filename_selected(self):
#         """Handle filename selection and plot data."""
#         selected = self.filename_combo.currentText()
#         if selected == "Select Filename":
#             self.selected_filename = None
#             self.clear_plots()
#             return
#         self.selected_filename = selected
#         self.plot_data()

#     def apply_time_range(self):
#         """Apply the selected time range and replot data."""
#         start_text = self.start_time_input.text()
#         end_text = self.end_time_input.text()
#         try:
#             if start_text:
#                 self.start_time = datetime.strptime(start_text, '%Y-%m-%d %H:%M:%S').timestamp()
#             else:
#                 self.start_time = None
#             if end_text:
#                 self.end_time = datetime.strptime(end_text, '%Y-%m-%d %H:%M:%S').timestamp()
#             else:
#                 self.end_time = None
#             if self.start_time and self.end_time and self.start_time >= self.end_time:
#                 logging.error("Start time must be before end time")
#                 if self.console:
#                     self.console.append_to_console("Start time must be before end time")
#                 return
#             self.plot_data()
#         except ValueError as e:
#             logging.error(f"Invalid time format: {str(e)}")
#             if self.console:
#                 self.console.append_to_console(f"Invalid time format: {str(e)}")

#     def clear_plots(self):
#         """Clear all plots and data."""
#         for plot in self.plots:
#             plot.setData([], [])
#         for widget in self.plot_widgets:
#             widget.clear()
#             widget.addLegend()
#             widget.showGrid(x=True, y=True)
#             if widget.getAxis('left').labelText == 'Tacho Trigger':
#                 widget.setYRange(-0.5, 1.5, padding=0)
#         self.data = [[] for _ in range(self.num_plots)]
#         self.channel_times = []
#         self.tacho_times = []
#         self.trigger_lines = [None] * (self.num_plots - 1) + [[]]
#         logging.debug("Cleared all plots")

#     def plot_data(self):
#         """Fetch and plot data for the selected filename and time range."""
#         if not self.selected_filename:
#             logging.debug("No filename selected for plotting")
#             return

#         try:
#             messages = self.db.get_timeview_messages(
#                 self.project_name,
#                 model_name=self.model_name,
#                 filename=self.selected_filename
#             )
#             if not messages:
#                 logging.warning(f"No data found for filename {self.selected_filename}")
#                 if self.console:
#                     self.console.append_to_console(f"No data found for filename {self.selected_filename}")
#                 self.clear_plots()
#                 return

#             # Process messages within the time range
#             filtered_messages = []
#             for msg in messages:
#                 created_at = datetime.fromisoformat(msg['createdAt']).timestamp()
#                 if (self.start_time is None or created_at >= self.start_time) and \
#                    (self.end_time is None or created_at <= self.end_time):
#                     filtered_messages.append(msg)

#             if not filtered_messages:
#                 logging.warning(f"No data within time range for filename {self.selected_filename}")
#                 if self.console:
#                     self.console.append_to_console(f"No data within time range for filename {self.selected_filename}")
#                 self.clear_plots()
#                 return

#             # Assume the latest message for simplicity (or aggregate if needed)
#             msg = filtered_messages[-1]
#             channel_data = msg['message']['channel_data']
#             tacho_freq = msg['message']['tacho_freq']
#             tacho_trigger = msg['message']['tacho_trigger']
#             self.sample_rate = msg.get('samplingRate', 4096)
#             channel_samples = msg.get('samplingSize', 4096)
#             tacho_samples = len(tacho_freq)

#             # Validate data
#             if len(channel_data) != self.num_channels or len(tacho_freq) != tacho_samples or len(tacho_trigger) != tacho_samples:
#                 logging.warning(f"Data length mismatch: channels={len(channel_data)}, tacho_freq={len(tacho_freq)}, tacho_trigger={len(tacho_trigger)}")
#                 if self.console:
#                     self.console.append_to_console(f"Data length mismatch in {self.selected_filename}")
#                 self.clear_plots()
#                 return

#             # Generate time arrays
#             created_at = datetime.fromisoformat(msg['createdAt']).timestamp()
#             channel_time_step = 1.0 / self.sample_rate
#             tacho_time_step = 1.0 / self.sample_rate
#             self.channel_times = np.array([created_at - (channel_samples - 1) * channel_time_step + i * channel_time_step for i in range(channel_samples)])
#             self.tacho_times = np.array([created_at - (tacho_samples - 1) * tacho_time_step + i * tacho_time_step for i in range(tacho_samples)])

#             # Update data
#             for ch in range(self.num_channels):
#                 self.data[ch] = np.array(channel_data[ch])
#             self.data[self.num_channels] = np.array(tacho_freq)
#             self.data[self.num_channels + 1] = np.array(tacho_trigger)

#             # Clear existing trigger lines
#             for widget in self.plot_widgets:
#                 widget.clear()
#                 widget.addLegend()
#                 widget.showGrid(x=True, y=True)
#                 if widget.getAxis('left').labelText == 'Tacho Trigger':
#                     widget.setYRange(-0.5, 1.5, padding=0)

#             # Plot data
#             colors = ['r', 'g', 'b', 'y', 'c', 'm']
#             for ch in range(self.num_plots):
#                 times = self.tacho_times if ch >= self.num_channels else self.channel_times
#                 if len(self.data[ch]) > 0 and len(times) > 0:
#                     pen = mkPen(color=colors[ch % len(colors)], width=2)
#                     self.plots[ch] = self.plot_widgets[ch].plot(times, self.data[ch], pen=pen)
#                     self.plot_widgets[ch].setXRange(times[0], times[-1], padding=0)
#                     if ch < self.num_channels:
#                         self.plot_widgets[ch].enableAutoRange(axis='y')
#                     elif ch == self.num_channels:
#                         self.plot_widgets[ch].enableAutoRange(axis='y')
#                     else:
#                         self.plot_widgets[ch].setYRange(-0.5, 1.5, padding=0)
#                     # Re-add vertical line
#                     vline = InfiniteLine(angle=90, movable=False, pen=mkPen('r', width=2))
#                     vline.setVisible(False)
#                     self.plot_widgets[ch].addItem(vline)
#                     self.vlines[ch] = vline
#                 else:
#                     logging.warning(f"No data for plot {ch}")
#                     if self.console:
#                         self.console.append_to_console(f"No data for plot {ch}")

#             # Plot trigger lines
#             if len(self.data[self.num_plots - 1]) > 0:
#                 trigger_indices = np.where(self.data[self.num_plots - 1] == 1)[0]
#                 self.trigger_lines = [None] * (self.num_plots - 1) + [[]]
#                 for idx in trigger_indices:
#                     if idx < len(self.tacho_times):
#                         line = InfiniteLine(
#                             pos=self.tacho_times[idx],
#                             angle=90,
#                             movable=False,
#                             pen=mkPen('k', width=2, style=Qt.SolidLine)
#                         )
#                         self.plot_widgets[self.num_plots - 1].addItem(line)
#                         self.trigger_lines[self.num_plots - 1].append(line)

#             logging.debug(f"Plotted data for {self.selected_filename}: {self.num_plots} plots")
#             if self.console:
#                 self.console.append_to_console(f"Time Report ({self.model_name}): Plotted {self.num_plots} plots for {self.selected_filename}")
#         except Exception as e:
#             logging.error(f"Error plotting data: {str(e)}")
#             if self.console:
#                 self.console.append_to_console(f"Error plotting data: {str(e)}")
#             self.clear_plots()

#     def mouse_enter(self, idx):
#         """Called when mouse enters plot idx viewport."""
#         self.active_line_idx = idx
#         self.vlines[idx].setVisible(True)
#         logging.debug(f"Mouse entered plot {idx}")

#     def mouse_leave(self, idx):
#         """Called when mouse leaves plot idx viewport."""
#         self.active_line_idx = None
#         for vline in self.vlines:
#             vline.setVisible(False)
#         logging.debug(f"Mouse left plot {idx}")

#     def mouse_moved(self, evt, idx):
#         """Update vertical lines on mouse move."""
#         if self.active_line_idx is None:
#             return

#         pos = evt[0]
#         if not self.plot_widgets[idx].sceneBoundingRect().contains(pos):
#             return

#         mouse_point = self.plot_widgets[idx].plotItem.vb.mapSceneToView(pos)
#         x = mouse_point.x()

#         times = self.tacho_times if idx >= self.num_channels else self.channel_times
#         if len(times) > 0:
#             if x < times[0]:
#                 x = times[0]
#             elif x > times[-1]:
#                 x = times[-1]

#         for vline in self.vlines:
#             vline.setPos(x)
#             vline.setVisible(True)






# from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QPushButton, QLineEdit, QScrollArea
# from PyQt5.QtCore import QObject, QEvent, Qt
# from pyqtgraph import PlotWidget, mkPen, AxisItem, InfiniteLine, SignalProxy
# from datetime import datetime
# import numpy as np
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

# class TimeReportFeature:
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
#         self.channel_times = []
#         self.tacho_times = []
#         self.vlines = []
#         self.proxies = []
#         self.trackers = []
#         self.trigger_lines = []
#         self.active_line_idx = None
#         self.num_channels = 4
#         self.num_plots = 6
#         self.sample_rate = 4096
#         self.filenames = []
#         self.selected_filename = None
#         self.start_time = None
#         self.end_time = None

#         self.initUI()
#         self.refresh_filenames()

#     def initUI(self):
#         """Initialize the UI with filename selector, time range inputs, and pyqtgraph subplots."""
#         self.widget = QWidget()
#         layout = QVBoxLayout()

#         # Create a scroll area to contain the plots and controls
#         scroll_area = QScrollArea()
#         scroll_area.setWidgetResizable(True)
#         scroll_content = QWidget()
#         scroll_layout = QVBoxLayout(scroll_content)

#         # Add filename selector
#         scroll_layout.addWidget(QLabel(f"Time Report for Model: {self.model_name}, Channel: {self.channel or 'All'}"))
#         self.filename_combo = QComboBox()
#         self.filename_combo.addItem("Select Filename")
#         self.filename_combo.currentIndexChanged.connect(self.on_filename_selected)
#         scroll_layout.addWidget(self.filename_combo)

#         # Initialize plots
#         colors = ['r', 'g', 'b', 'y', 'c', 'm']
#         for i in range(self.num_plots):
#             plot_widget = PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')}, background='w')
#             # Set plot widget size: height=250, width=100%
#             plot_widget.setFixedHeight(250)
#             plot_widget.setMinimumWidth(0)  # Allow widget to expand to full width
#             if i < self.num_channels:
#                 plot_widget.setLabel('left', f'CH{i+1} Value')
#             elif i == self.num_channels:
#                 plot_widget.setLabel('left', 'Tacho Frequency')
#             else:
#                 plot_widget.setLabel('left', 'Tacho Trigger')
#                 plot_widget.setYRange(-0.5, 1.5, padding=0)
#             plot_widget.setLabel('bottom', 'Time')
#             plot_widget.showGrid(x=True, y=True)
#             plot_widget.addLegend()
#             pen = mkPen(color=colors[i % len(colors)], width=2)
#             plot = plot_widget.plot([], [], pen=pen)
#             self.plots.append(plot)
#             self.plot_widgets.append(plot_widget)
#             self.data.append([])

#             vline = InfiniteLine(angle=90, movable=False, pen=mkPen('r', width=2))
#             vline.setVisible(False)
#             plot_widget.addItem(vline)
#             self.vlines.append(vline)

#             if i == self.num_plots - 1:
#                 self.trigger_lines = []
#             else:
#                 self.trigger_lines.append(None)

#             proxy = SignalProxy(plot_widget.scene().sigMouseMoved, rateLimit=60, slot=lambda evt, idx=i: self.mouse_moved(evt, idx))
#             self.proxies.append(proxy)

#             tracker = MouseTracker(plot_widget.viewport(), i, self)
#             plot_widget.viewport().installEventFilter(tracker)
#             self.trackers.append(tracker)

#             scroll_layout.addWidget(plot_widget)

#         # Set the scroll content widget and add scroll area to main layout
#         scroll_area.setWidget(scroll_content)
#         layout.addWidget(scroll_area)
#         self.widget.setLayout(layout)

#         if not self.model_name and self.console:
#             self.console.append_to_console("No model selected in TimeReportFeature.")
#         if not self.channel and self.console:
#             self.console.append_to_console("No channel selected in TimeReportFeature.")

#     def get_widget(self):
#         """Return the widget containing the plots."""
#         return self.widget

#     def refresh_filenames(self):
#         """Retrieve distinct filenames from the database and update combo box."""
#         try:
#             self.filenames = self.db.get_distinct_filenames(self.project_name, self.model_name)
#             self.filename_combo.clear()
#             self.filename_combo.addItem("Select Filename")
#             self.filename_combo.addItems(self.filenames)
#             logging.debug(f"Refreshed filenames: {self.filenames}")
#             if self.console:
#                 self.console.append_to_console(f"Refreshed filenames: {len(self.filenames)} found")
#         except Exception as e:
#             logging.error(f"Error refreshing filenames: {str(e)}")
#             if self.console:
#                 self.console.append_to_console(f"Error refreshing filenames: {str(e)}")

#     def on_filename_selected(self):
#         """Handle filename selection and plot data."""
#         selected = self.filename_combo.currentText()
#         if selected == "Select Filename":
#             self.selected_filename = None
#             self.clear_plots()
#             return
#         self.selected_filename = selected
#         self.plot_data()

#     def apply_time_range(self):
#         """Apply the selected time range and replot data."""
#         start_text = self.start_time_input.text()
#         end_text = self.end_time_input.text()
#         try:
#             if start_text:
#                 self.start_time = datetime.strptime(start_text, '%Y-%m-%d %H:%M:%S').timestamp()
#             else:
#                 self.start_time = None
#             if end_text:
#                 self.end_time = datetime.strptime(end_text, '%Y-%m-%d %H:%M:%S').timestamp()
#             else:
#                 self.end_time = None
#             if self.start_time and self.end_time and self.start_time >= self.end_time:
#                 logging.error("Start time must be before end time")
#                 if self.console:
#                     self.console.append_to_console("Start time must be before end time")
#                 return
#             self.plot_data()
#         except ValueError as e:
#             logging.error(f"Invalid time format: {str(e)}")
#             if self.console:
#                 self.console.append_to_console(f"Invalid time format: {str(e)}")

#     def clear_plots(self):
#         """Clear all plots and data."""
#         for plot in self.plots:
#             plot.setData([], [])
#         for widget in self.plot_widgets:
#             widget.clear()
#             widget.addLegend()
#             widget.showGrid(x=True, y=True)
#             if widget.getAxis('left').labelText == 'Tacho Trigger':
#                 widget.setYRange(-0.5, 1.5, padding=0)
#         self.data = [[] for _ in range(self.num_plots)]
#         self.channel_times = []
#         self.tacho_times = []
#         self.trigger_lines = [None] * (self.num_plots - 1) + [[]]
#         logging.debug("Cleared all plots")

#     def plot_data(self):
#         """Fetch and plot data for the selected filename and time range."""
#         if not self.selected_filename:
#             logging.debug("No filename selected for plotting")
#             return

#         try:
#             messages = self.db.get_timeview_messages(
#                 self.project_name,
#                 model_name=self.model_name,
#                 filename=self.selected_filename
#             )
#             if not messages:
#                 logging.warning(f"No data found for filename {self.selected_filename}")
#                 if self.console:
#                     self.console.append_to_console(f"No data found for filename {self.selected_filename}")
#                 self.clear_plots()
#                 return

#             # Process messages within the time range
#             filtered_messages = []
#             for msg in messages:
#                 created_at = datetime.fromisoformat(msg['createdAt']).timestamp()
#                 if (self.start_time is None or created_at >= self.start_time) and \
#                    (self.end_time is None or created_at <= self.end_time):
#                     filtered_messages.append(msg)

#             if not filtered_messages:
#                 logging.warning(f"No data within time range for filename {self.selected_filename}")
#                 if self.console:
#                     self.console.append_to_console(f"No data within time range for filename {self.selected_filename}")
#                 self.clear_plots()
#                 return

#             # Assume the latest message for simplicity (or aggregate if needed)
#             msg = filtered_messages[-1]
#             channel_data = msg['message']['channel_data']
#             tacho_freq = msg['message']['tacho_freq']
#             tacho_trigger = msg['message']['tacho_trigger']
#             self.sample_rate = msg.get('samplingRate', 4096)
#             channel_samples = msg.get('samplingSize', 4096)
#             tacho_samples = len(tacho_freq)

#             # Validate data
#             if len(channel_data) != self.num_channels or len(tacho_freq) != tacho_samples or len(tacho_trigger) != tacho_samples:
#                 logging.warning(f"Data length mismatch: channels={len(channel_data)}, tacho_freq={len(tacho_freq)}, tacho_trigger={len(tacho_trigger)}")
#                 if self.console:
#                     self.console.append_to_console(f"Data length mismatch in {self.selected_filename}")
#                 self.clear_plots()
#                 return

#             # Generate time arrays
#             created_at = datetime.fromisoformat(msg['createdAt']).timestamp()
#             channel_time_step = 1.0 / self.sample_rate
#             tacho_time_step = 1.0 / self.sample_rate
#             self.channel_times = np.array([created_at - (channel_samples - 1) * channel_time_step + i * channel_time_step for i in range(channel_samples)])
#             self.tacho_times = np.array([created_at - (tacho_samples - 1) * tacho_time_step + i * tacho_time_step for i in range(tacho_samples)])

#             # Update data
#             for ch in range(self.num_channels):
#                 self.data[ch] = np.array(channel_data[ch])
#             self.data[self.num_channels] = np.array(tacho_freq)
#             self.data[self.num_channels + 1] = np.array(tacho_trigger)

#             # Clear existing trigger lines
#             for widget in self.plot_widgets:
#                 widget.clear()
#                 widget.addLegend()
#                 widget.showGrid(x=True, y=True)
#                 if widget.getAxis('left').labelText == 'Tacho Trigger':
#                     widget.setYRange(-0.5, 1.5, padding=0)

#             # Plot data
#             colors = ['r', 'g', 'b', 'y', 'c', 'm']
#             for ch in range(self.num_plots):
#                 times = self.tacho_times if ch >= self.num_channels else self.channel_times
#                 if len(self.data[ch]) > 0 and len(times) > 0:
#                     pen = mkPen(color=colors[ch % len(colors)], width=2)
#                     self.plots[ch] = self.plot_widgets[ch].plot(times, self.data[ch], pen=pen)
#                     self.plot_widgets[ch].setXRange(times[0], times[-1], padding=0)
#                     if ch < self.num_channels:
#                         self.plot_widgets[ch].enableAutoRange(axis='y')
#                     elif ch == self.num_channels:
#                         self.plot_widgets[ch].enableAutoRange(axis='y')
#                     else:
#                         self.plot_widgets[ch].setYRange(-0.5, 1.5, padding=0)
#                     # Re-add vertical line
#                     vline = InfiniteLine(angle=90, movable=False, pen=mkPen('r', width=2))
#                     vline.setVisible(False)
#                     self.plot_widgets[ch].addItem(vline)
#                     self.vlines[ch] = vline
#                 else:
#                     logging.warning(f"No data for plot {ch}")
#                     if self.console:
#                         self.console.append_to_console(f"No data for plot {ch}")

#             # Plot trigger lines
#             if len(self.data[self.num_plots - 1]) > 0:
#                 trigger_indices = np.where(self.data[self.num_plots - 1] == 1)[0]
#                 self.trigger_lines = [None] * (self.num_plots - 1) + [[]]
#                 for idx in trigger_indices:
#                     if idx < len(self.tacho_times):
#                         line = InfiniteLine(
#                             pos=self.tacho_times[idx],
#                             angle=90,
#                             movable=False,
#                             pen=mkPen('k', width=2, style=Qt.SolidLine)
#                         )
#                         self.plot_widgets[self.num_plots - 1].addItem(line)
#                         self.trigger_lines[self.num_plots - 1].append(line)

#             logging.debug(f"Plotted data for {self.selected_filename}: {self.num_plots} plots")
#             if self.console:
#                 self.console.append_to_console(f"Time Report ({self.model_name}): Plotted {self.num_plots} plots for {self.selected_filename}")
#         except Exception as e:
#             logging.error(f"Error plotting data: {str(e)}")
#             if self.console:
#                 self.console.append_to_console(f"Error plotting data: {str(e)}")
#             self.clear_plots()

#     def mouse_enter(self, idx):
#         """Called when mouse enters plot idx viewport."""
#         self.active_line_idx = idx
#         self.vlines[idx].setVisible(True)
#         logging.debug(f"Mouse entered plot {idx}")

#     def mouse_leave(self, idx):
#         """Called when mouse leaves plot idx viewport."""
#         self.active_line_idx = None
#         for vline in self.vlines:
#             vline.setVisible(False)
#         logging.debug(f"Mouse left plot {idx}")

#     def mouse_moved(self, evt, idx):
#         """Update vertical lines on mouse move."""
#         if self.active_line_idx is None:
#             return

#         pos = evt[0]
#         if not self.plot_widgets[idx].sceneBoundingRect().contains(pos):
#             return

#         mouse_point = self.plot_widgets[idx].plotItem.vb.mapSceneToView(pos)
#         x = mouse_point.x()

#         times = self.tacho_times if idx >= self.num_channels else self.channel_times
#         if len(times) > 0:
#             if x < times[0]:
#                 x = times[0]
#             elif x > times[-1]:
#                 x = times[-1]

#         for vline in self.vlines:
#             vline.setPos(x)
#             vline.setVisible(True)





from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QPushButton, QScrollArea, QHBoxLayout
from PyQt5.QtCore import QObject, QEvent, Qt
from pyqtgraph import PlotWidget, mkPen, AxisItem, InfiniteLine, SignalProxy
from datetime import datetime
import numpy as np
import logging
from PyQt5.QtWidgets import QSlider

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

class TimeReportFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None):
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
        self.channel_times = []
        self.tacho_times = []
        self.vlines = []
        self.proxies = []
        self.trackers = []
        self.trigger_lines = []
        self.active_line_idx = None
        self.num_channels = 4
        self.num_plots = 6
        self.sample_rate = 4096
        self.filenames = []
        self.selected_filename = None
        self.start_time = None
        self.end_time = None
        self.start_slider = None
        self.end_slider = None
        self.min_time = None
        self.max_time = None

        self.initUI()
        self.refresh_filenames()

    def initUI(self):
        """Initialize the UI with filename selector, time range sliders, and pyqtgraph subplots."""
        self.widget = QWidget()
        layout = QVBoxLayout()

        # Create a scroll area to contain the plots and controls
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # Add filename selector
        scroll_layout.addWidget(QLabel(f"Time Report for Model: {self.model_name}, Channel: {self.channel or 'All'}"))
        self.filename_combo = QComboBox()
        self.filename_combo.setFixedSize(250, 100)  # Set width and height to 250
        self.filename_combo.currentIndexChanged.connect(self.on_filename_selected)
        scroll_layout.addWidget(self.filename_combo)

        # Add time range sliders
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Time Range:"))
        self.start_slider = QSlider(Qt.Horizontal)
        self.start_slider.setMinimum(0)
        self.start_slider.setMaximum(1000)
        self.start_slider.valueChanged.connect(self.update_from_sliders)
        slider_layout.addWidget(self.start_slider)

        self.end_slider = QSlider(Qt.Horizontal)
        self.end_slider.setMinimum(0)
        self.end_slider.setMaximum(1000)
        self.end_slider.valueChanged.connect(self.update_from_sliders)
        slider_layout.addWidget(self.end_slider)

        apply_button = QPushButton("Apply Changes")
        apply_button.clicked.connect(self.apply_time_range)
        slider_layout.addWidget(apply_button)
        scroll_layout.addLayout(slider_layout)

        # Initialize plots
        colors = ['r', 'g', 'b', 'y', 'c', 'm']
        for i in range(self.num_plots):
            plot_widget = PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')}, background='w')
            plot_widget.setFixedHeight(250)
            plot_widget.setMinimumWidth(0)
            if i < self.num_channels:
                plot_widget.setLabel('left', f'CH{i+1} Value')
            elif i == self.num_channels:
                plot_widget.setLabel('left', 'Tacho Frequency')
            else:
                plot_widget.setLabel('left', 'Tacho Trigger')
                plot_widget.setYRange(-0.5, 1.5, padding=0)
            plot_widget.setLabel('bottom', 'Time')
            plot_widget.showGrid(x=True, y=True)
            plot_widget.addLegend()
            pen = mkPen(color=colors[i % len(colors)], width=2)
            plot = plot_widget.plot([], [], pen=pen)
            self.plots.append(plot)
            self.plot_widgets.append(plot_widget)
            self.data.append([])

            vline = InfiniteLine(angle=90, movable=False, pen=mkPen('r', width=2))
            vline.setVisible(False)
            plot_widget.addItem(vline)
            self.vlines.append(vline)

            if i == self.num_plots - 1:
                self.trigger_lines = []
            else:
                self.trigger_lines.append(None)

            proxy = SignalProxy(plot_widget.scene().sigMouseMoved, rateLimit=60, slot=lambda evt, idx=i: self.mouse_moved(evt, idx))
            self.proxies.append(proxy)

            tracker = MouseTracker(plot_widget.viewport(), i, self)
            plot_widget.viewport().installEventFilter(tracker)
            self.trackers.append(tracker)

            scroll_layout.addWidget(plot_widget)

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        self.widget.setLayout(layout)

        if not self.model_name and self.console:
            self.console.append_to_console("No model selected in TimeReportFeature.")
        if not self.channel and self.console:
            self.console.append_to_console("No channel selected in TimeReportFeature.")

    def get_widget(self):
        """Return the widget containing the plots."""
        return self.widget

    def refresh_filenames(self):
        """Retrieve distinct filenames from the database and update combo box."""
        try:
            self.filenames = self.db.get_distinct_filenames(self.project_name, self.model_name)
            self.filename_combo.clear()
            # Append timestamp to filenames
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.filenames = [f"{fname}_{timestamp}" for fname in self.filenames]
            self.filename_combo.addItems(self.filenames)
            logging.debug(f"Refreshed filenames: {self.filenames}")
            if self.console:
                self.console.append_to_console(f"Refreshed filenames: {len(self.filenames)} found")
        except Exception as e:
            logging.error(f"Error refreshing filenames: {str(e)}")
            if self.console:
                self.console.append_to_console(f"Error refreshing filenames: {str(e)}")

    def on_filename_selected(self):
        """Handle filename selection and plot data."""
        selected = self.filename_combo.currentText()
        if not selected:
            self.selected_filename = None
            self.clear_plots()
            self.start_slider.setValue(0)
            self.end_slider.setValue(1000)
            self.min_time = None
            self.max_time = None
            return
        # Remove timestamp from selected filename for database query
        self.selected_filename = selected.rsplit('_', 2)[0]
        self.plot_data()

    def update_from_sliders(self):
        """Update time range from sliders."""
        if self.min_time is None or self.max_time is None:
            return

        try:
            start_value = self.start_slider.value()
            end_value = self.end_slider.value()
            if start_value >= end_value:
                return  # Prevent invalid range

            time_range = self.max_time - self.min_time
            self.start_time = self.min_time + (start_value / 1000.0) * time_range
            self.end_time = self.min_time + (end_value / 1000.0) * time_range
        except Exception as e:
            logging.error(f"Error updating from sliders: {str(e)}")
            if self.console:
                self.console.append_to_console(f"Error updating from sliders: {str(e)}")

    def apply_time_range(self):
        """Apply the selected time range from sliders and replot data."""
        try:
            if self.start_time and self.end_time and self.start_time >= self.end_time:
                logging.error("Start time must be before end time")
                if self.console:
                    self.console.append_to_console("Start time must be before end time")
                return
            self.plot_data()
        except Exception as e:
            logging.error(f"Error applying time range: {str(e)}")
            if self.console:
                self.console.append_to_console(f"Error applying time range: {str(e)}")

    def clear_plots(self):
        """Clear all plots and data."""
        for plot in self.plots:
            plot.setData([], [])
        for widget in self.plot_widgets:
            widget.clear()
            widget.addLegend()
            widget.showGrid(x=True, y=True)
            if widget.getAxis('left').labelText == 'Tacho Trigger':
                widget.setYRange(-0.5, 1.5, padding=0)
        self.data = [[] for _ in range(self.num_plots)]
        self.channel_times = []
        self.tacho_times = []
        self.trigger_lines = [None] * (self.num_plots - 1) + [[]]
        logging.debug("Cleared all plots")

    def plot_data(self):
        """Fetch and plot data for the selected filename and time range."""
        if not self.selected_filename:
            logging.debug("No filename selected for plotting")
            return

        try:
            messages = self.db.get_timeview_messages(
                self.project_name,
                model_name=self.model_name,
                filename=self.selected_filename
            )
            if not messages:
                logging.warning(f"No data found for filename {self.selected_filename}")
                if self.console:
                    self.console.append_to_console(f"No data found for filename {self.selected_filename}")
                self.clear_plots()
                return

            # Determine min and max time for sliders
            created_times = [datetime.fromisoformat(msg['createdAt']).timestamp() for msg in messages]
            self.min_time = min(created_times)
            self.max_time = max(created_times)

            # Process messages within the time range
            filtered_messages = []
            for msg in messages:
                created_at = datetime.fromisoformat(msg['createdAt']).timestamp()
                if (self.start_time is None or created_at >= self.start_time) and \
                   (self.end_time is None or created_at <= self.end_time):
                    filtered_messages.append(msg)

            if not filtered_messages:
                logging.warning(f"No data within time range for filename {self.selected_filename}")
                if self.console:
                    self.console.append_to_console(f"No data within time range for filename {self.selected_filename}")
                self.clear_plots()
                return

            # Assume the latest message for simplicity
            msg = filtered_messages[-1]
            channel_data = msg['message']['channel_data']
            tacho_freq = msg['message']['tacho_freq']
            tacho_trigger = msg['message']['tacho_trigger']
            self.sample_rate = msg.get('samplingRate', 4096)
            channel_samples = msg.get('samplingSize', 4096)
            tacho_samples = len(tacho_freq)

            # Validate data
            if len(channel_data) != self.num_channels or len(tacho_freq) != tacho_samples or len(tacho_trigger) != tacho_samples:
                logging.warning(f"Data length mismatch: channels={len(channel_data)}, tacho_freq={len(tacho_freq)}, tacho_trigger={len(tacho_trigger)}")
                if self.console:
                    self.console.append_to_console(f"Data length mismatch in {self.selected_filename}")
                self.clear_plots()
                return

            # Generate time arrays
            created_at = datetime.fromisoformat(msg['createdAt']).timestamp()
            channel_time_step = 1.0 / self.sample_rate
            tacho_time_step = 1.0 / self.sample_rate
            self.channel_times = np.array([created_at - (channel_samples - 1) * channel_time_step + i * channel_time_step for i in range(channel_samples)])
            self.tacho_times = np.array([created_at - (tacho_samples - 1) * tacho_time_step + i * tacho_time_step for i in range(tacho_samples)])

            # Update data
            for ch in range(self.num_channels):
                self.data[ch] = np.array(channel_data[ch])
            self.data[self.num_channels] = np.array(tacho_freq)
            self.data[self.num_channels + 1] = np.array(tacho_trigger)

            # Clear existing plots
            for widget in self.plot_widgets:
                widget.clear()
                widget.addLegend()
                widget.showGrid(x=True, y=True)
                if widget.getAxis('left').labelText == 'Tacho Trigger':
                    widget.setYRange(-0.5, 1.5, padding=0)

            # Plot data
            colors = ['r', 'g', 'b', 'y', 'c', 'm']
            for ch in range(self.num_plots):
                times = self.tacho_times if ch >= self.num_channels else self.channel_times
                if len(self.data[ch]) > 0 and len(times) > 0:
                    pen = mkPen(color=colors[ch % len(colors)], width=2)
                    self.plots[ch] = self.plot_widgets[ch].plot(times, self.data[ch], pen=pen)
                    self.plot_widgets[ch].setXRange(times[0], times[-1], padding=0)
                    if ch < self.num_channels:
                        self.plot_widgets[ch].enableAutoRange(axis='y')
                    elif ch == self.num_channels:
                        self.plot_widgets[ch].enableAutoRange(axis='y')
                    else:
                        self.plot_widgets[ch].setYRange(-0.5, 1.5, padding=0)
                    vline = InfiniteLine(angle=90, movable=False, pen=mkPen('r', width=2))
                    vline.setVisible(False)
                    self.plot_widgets[ch].addItem(vline)
                    self.vlines[ch] = vline
                else:
                    logging.warning(f"No data for plot {ch}")
                    if self.console:
                        self.console.append_to_console(f"No data for plot {ch}")

            # Plot trigger lines
            if len(self.data[self.num_plots - 1]) > 0:
                trigger_indices = np.where(self.data[self.num_plots - 1] == 1)[0]
                self.trigger_lines = [None] * (self.num_plots - 1) + [[]]
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

            logging.debug(f"Plotted data for {self.selected_filename}: {self.num_plots} plots")
            if self.console:
                self.console.append_to_console(f"Time Report ({self.model_name}): Plotted {self.num_plots} plots for {self.selected_filename}")
        except Exception as e:
            logging.error(f"Error plotting data: {str(e)}")
            if self.console:
                self.console.append_to_console(f"Error plotting data: {str(e)}")
            self.clear_plots()

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