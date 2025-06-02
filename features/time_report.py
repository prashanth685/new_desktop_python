from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QPushButton, QScrollArea, QGridLayout)
from PyQt5.QtCore import Qt, pyqtSignal, QEvent, QObject
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor
import pyqtgraph as pg
from pyqtgraph import PlotWidget, mkPen, AxisItem, InfiniteLine, SignalProxy
from datetime import datetime, timedelta
import numpy as np
import logging
from PyQt5.QtCore import QRect

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class QRangeSlider(QWidget):
    """Custom dual slider widget for selecting a time range."""
    valueChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(30)
        self.setMinimumWidth(300)
        self.min_value = 0
        self.max_value = 1000
        self.left_value = 0
        self.right_value = 1000
        self.dragging = None
        self.setMouseTracking(True)
        self.setStyleSheet("""
            QWidget {
                background-color: #34495e;
            }
        """)

    def setRange(self, min_val, max_val):
        self.min_value = min_val
        self.max_value = max_val
        self.left_value = max(self.min_value, min(self.left_value, self.max_value))
        self.right_value = max(self.min_value, min(self.right_value, self.max_value))
        self.update()

    def setValues(self, left, right):
        self.left_value = max(self.min_value, min(left, self.max_value))
        self.right_value = max(self.min_value, min(right, self.max_value))
        self.update()
        self.valueChanged.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        groove_rect = QRect(int(10), int(10), int(self.width() - 20), int(8))
        painter.setPen(QPen(QColor("#1a73e8")))
        painter.setBrush(QColor("#34495e"))
        painter.drawRoundedRect(groove_rect, 4, 4)
        left_pos = int(self._value_to_pos(self.left_value))
        right_pos = int(self._value_to_pos(self.right_value))
        selected_rect = QRect(left_pos, int(10), int(right_pos - left_pos), int(8))
        painter.setBrush(QColor("#90caf9"))
        painter.drawRoundedRect(selected_rect, 4, 4)
        painter.setPen(QPen(QColor("#1a73e8")))
        painter.setBrush(QColor("#42a5f5" if self.dragging == 'left' else "#1a73e8"))
        painter.drawEllipse(left_pos - 9, 6, 18, 18)
        painter.setBrush(QColor("#42a5f5" if self.dragging == 'right' else "#1a73e8"))
        painter.drawEllipse(right_pos - 9, 6, 18, 18)

    def _value_to_pos(self, value):
        if self.max_value == self.min_value:
            return 10
        return 10 + (self.width() - 20) * (value - self.min_value) / (self.max_value - self.min_value)

    def _pos_to_value(self, pos):
        if self.width() <= 20:
            return self.min_value
        value = self.min_value + (pos - 10) / (self.width() - 20) * (self.max_value - self.min_value)
        return max(self.min_value, min(self.max_value, value))

    def mousePressEvent(self, event):
        pos = event.pos().x()
        left_pos = self._value_to_pos(self.left_value)
        right_pos = self._value_to_pos(self.right_value)
        if abs(pos - left_pos) < abs(pos - right_pos) and abs(pos - left_pos) < 10:
            self.dragging = 'left'
        elif abs(pos - right_pos) <= abs(pos - left_pos) and abs(pos - right_pos) < 10:
            self.dragging = 'right'
        self.update()

    def mouseMoveEvent(self, event):
        if self.dragging:
            pos = event.pos().x()
            value = self._pos_to_value(pos)
            if self.dragging == 'left':
                self.left_value = max(self.min_value, min(value, self.right_value - 1))
            elif self.dragging == 'right':
                self.right_value = max(self.left_value + 1, min(value, self.max_value))
            self.update()
            self.valueChanged.emit()

    def mouseReleaseEvent(self, event):
        self.dragging = None
        self.update()

    def getValues(self):
        return self.left_value, self.right_value

class TimeAxisItem(AxisItem):
    """Custom axis to display datetime on x-axis."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
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
        self.min_time = None
        self.max_time = None
        self.use_full_range = True  # Flag to indicate full range plotting
        self.initUI()
        self.refresh_filenames()

    def initUI(self):
        """Initialize the UI with filename selector, QRangeSlider, and pyqtgraph subplots."""
        self.widget = QWidget()
        layout = QVBoxLayout()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border-radius: 8px;
                padding: 5px;
            }
            QScrollBar:vertical {
                background: white;
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: black;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_content.setStyleSheet("background-color: #2c3e50; border-radius: 5px; padding: 10px;")

        header = QLabel(f"TIME REPORT FOR {self.project_name.upper()}")
        header.setStyleSheet("color: white; font-size: 26px; font-weight: bold; padding: 8px;")
        scroll_layout.addWidget(header, alignment=Qt.AlignCenter)

        file_layout = QHBoxLayout()
        file_label = QLabel(f"Select Saved File (Model: {self.model_name or 'None'}, Channel: {self.channel or 'All'}):")
        file_label.setStyleSheet("color: white; font-size: 16px; font: bold")
        self.filename_combo = QComboBox()
        self.filename_combo.setFixedSize(250, 40)
        self.filename_combo.setStyleSheet("""
            QComboBox {
                background-color: #fdfdfd;
                color: #212121;
                border: 2px solid #90caf9;
                border-radius: 8px;
                padding: 10px 40px 10px 14px;
                font-size: 16px;
                font-weight: 600;
                min-width: 220px;
                box-shadow: inset 0 0 5px rgba(0, 0, 0, 0.05);
            }
            QComboBox:hover {
                border: 2px solid #42a5f5;
                background-color: #f5faff;
            }
            QComboBox:focus {
                border: 2px solid #1e88e5;
                background-color: #ffffff;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 36px;
                border-left: 1px solid #e0e0e0;
                background-color: #e3f2fd;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #90caf9;
                border-radius: 4px;
                padding: 5px;
                selection-background-color: #e3f2fd;
                selection-color: #0d47a1;
                font-size: 15px;
                outline: 0;
            }
            QComboBox::item {
                padding: 10px 8px;
                border: none;
            }
            QComboBox::item:selected {
                background-color: #bbdefb;
                color: #0d47a1;
            }
        """)
        self.filename_combo.currentTextChanged.connect(self.on_filename_selected)
        file_layout.addWidget(file_label)
        file_layout.addWidget(self.filename_combo)
        file_layout.addStretch()
        scroll_layout.addLayout(file_layout)

        slider_layout = QGridLayout()
        slider_label = QLabel("Drag Time Range:")
        slider_label.setStyleSheet("color: white; font-size: 14px; font: bold")
        slider_label.setFixedWidth(150)
        self.time_slider = QRangeSlider(self.widget)
        self.time_slider.valueChanged.connect(self.update_from_slider)
        slider_layout.addWidget(slider_label, 0, 0, 1, 1, Qt.AlignLeft | Qt.AlignVCenter)
        slider_layout.addWidget(self.time_slider, 0, 1, 1, 1)
        slider_layout.setColumnStretch(1, 1)
        scroll_layout.addLayout(slider_layout)

        time_info_layout = QHBoxLayout()
        self.start_time_label = QLabel("File Start Time: N/A")
        self.start_time_label.setStyleSheet("color: white; font-size: 14px; font: bold")
        self.stop_time_label = QLabel("File Stop Time: N/A")
        self.stop_time_label.setStyleSheet("color: white; font-size: 14px; font: bold")
        time_info_layout.addWidget(self.start_time_label)
        time_info_layout.addWidget(self.stop_time_label)
        time_info_layout.addStretch()
        scroll_layout.addLayout(time_info_layout)

        apply_button = QPushButton("Apply Changes")
        apply_button.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                padding: 15px;
                font-size: 15px;
                border-radius: 50%;
                font-weight: bold;
            }
            QPushButton:pressed {
                background-color: #155ab6;
            }
        """)
        apply_button.clicked.connect(self.plot_data)
        apply_button.setEnabled(False)
        self.apply_button = apply_button
        scroll_layout.addWidget(apply_button, alignment=Qt.AlignCenter)

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
        return self.widget

    def refresh_filenames(self):
        try:
            self.filenames = self.db.get_distinct_filenames(self.project_name, self.model_name)
            self.filename_combo.clear()
            if not self.filenames:
                self.filename_combo.addItem("No Files Available")
                self.start_time_label.setText("File Start Time: N/A")
                self.stop_time_label.setText("File Stop Time: N/A")
                self.time_slider.setEnabled(False)
                self.apply_button.setEnabled(False)
                if self.console:
                    self.console.append_to_console("No saved files found for this project.")
            else:
                self.filename_combo.addItems(self.filenames)
                self.time_slider.setEnabled(True)
                self.apply_button.setEnabled(True)
                self.update_time_labels(self.filename_combo.currentText())
                if self.console:
                    self.console.append_to_console(f"Refreshed filenames: {len(self.filenames)} found")
        except Exception as e:
            logging.error(f"Error refreshing filenames: {str(e)}")
            self.filename_combo.addItem("Error Loading Files")
            self.start_time_label.setText("File Start Time: N/A")
            self.stop_time_label.setText("File Stop Time: N/A")
            self.time_slider.setEnabled(False)
            self.apply_button.setEnabled(False)
            if self.console:
                self.console.append_to_console(f"Error refreshing filenames: {str(e)}")

    def on_filename_selected(self, filename):
        self.selected_filename = filename
        self.use_full_range = True  # Reset to full range on file selection
        self.update_time_labels(filename)
        self.clear_plots()
        if filename and filename not in ["No Files Available", "Error Loading Files"]:
            self.apply_button.setEnabled(True)
        else:
            self.apply_button.setEnabled(False)
            self.start_time = None
            self.end_time = None
            self.min_time = None
            self.max_time = None

    def update_time_labels(self, filename):
        if not filename or filename in ["No Files Available", "Error Loading Files"]:
            self.start_time_label.setText("File Start Time: N/A")
            self.stop_time_label.setText("File Stop Time: N/A")
            self.time_slider.setEnabled(False)
            self.apply_button.setEnabled(False)
            self.min_time = None
            self.max_time = None
            return

        try:
            messages = self.db.get_timeview_messages(
                self.project_name,
                model_name=self.model_name,
                filename=filename
            )
            if not messages:
                self.start_time_label.setText("File Start Time: N/A")
                self.stop_time_label.setText("File Stop Time: N/A")
                self.time_slider.setEnabled(False)
                self.apply_button.setEnabled(False)
                self.min_time = None
                self.max_time = None
                if self.console:
                    self.console.append_to_console(f"No data found for file: {filename}")
                return

            created_times = [datetime.fromisoformat(msg['createdAt'].replace('Z', '+00:00')).timestamp() for msg in messages]
            self.min_time = min(created_times)
            self.max_time = max(created_times)
            self.start_time = self.min_time
            self.end_time = self.max_time
            self.start_time_label.setText(f"File Start Time: {datetime.fromtimestamp(self.min_time).strftime('%H:%M:%S')}")
            self.stop_time_label.setText(f"File Stop Time: {datetime.fromtimestamp(self.max_time).strftime('%H:%M:%S')}")
            self.time_slider.setRange(0, 1000)
            self.time_slider.setValues(0, 1000)
            self.time_slider.setEnabled(True)
            self.apply_button.setEnabled(True)
            self.use_full_range = True
        except Exception as e:
            logging.error(f"Error updating time labels for {filename}: {str(e)}")
            self.start_time_label.setText("File Start Time: N/A")
            self.stop_time_label.setText("File Stop Time: N/A")
            self.time_slider.setEnabled(False)
            self.apply_button.setEnabled(False)
            self.min_time = None
            self.max_time = None
            if self.console:
                self.console.append_to_console(f"Error loading time data for {filename}: {str(e)}")

    def update_from_slider(self):
        if not self.min_time or not self.max_time:
            return

        try:
            left_pos, right_pos = self.time_slider.getValues()
            if left_pos >= right_pos:
                return

            time_range = self.max_time - self.min_time
            self.start_time = self.min_time + (left_pos / 1000.0) * time_range
            self.end_time = self.min_time + (right_pos / 1000.0) * time_range
            self.start_time_label.setText(f"File Start Time: {datetime.fromtimestamp(self.start_time).strftime('%H:%M:%S')}")
            self.stop_time_label.setText(f"File Stop Time: {datetime.fromtimestamp(self.end_time).strftime('%H:%M:%S')}")
            self.use_full_range = (left_pos == 0 and right_pos == 1000)  # Check if full range is selected
        except Exception as e:
            logging.error(f"Error updating from slider: {str(e)}")
            if self.console:
                self.console.append_to_console(f"Error updating from slider: {str(e)}")

    def clear_plots(self):
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
        if not self.selected_filename or self.selected_filename in ["No Files Available", "Error Loading Files"]:
            self.clear_plots()
            if self.console:
                self.console.append_to_console("No valid file selected to plot.")
            return

        try:
            messages = self.db.get_timeview_messages(
                self.project_name,
                model_name=self.model_name,
                filename=self.selected_filename
            )
            if not messages:
                self.clear_plots()
                if self.console:
                    self.console.append_to_console(f"No data found for filename {self.selected_filename}")
                return

            # Use full range if use_full_range is True, else use slider-defined range
            if self.use_full_range:
                self.start_time = self.min_time
                self.end_time = self.max_time
                self.start_time_label.setText(f"File Start Time: {datetime.fromtimestamp(self.start_time).strftime('%H:%M:%S')}")
                self.stop_time_label.setText(f"File Stop Time: {datetime.fromtimestamp(self.end_time).strftime('%H:%M:%S')}")
                self.time_slider.setValues(0, 1000)

            if self.start_time >= self.end_time:
                self.clear_plots()
                if self.console:
                    self.console.append_to_console("Error: Start time must be before end time.")
                return

            # Filter messages by time range
            filtered_messages = []
            for msg in messages:
                created_at = datetime.fromisoformat(msg['createdAt'].replace('Z', '+00:00')).timestamp()
                if created_at >= self.start_time and created_at <= self.end_time:
                    filtered_messages.append(msg)

            if not filtered_messages:
                self.clear_plots()
                if self.console:
                    self.console.append_to_console(f"No data within time range for filename {self.selected_filename}")
                return

            # Use the latest message
            msg = filtered_messages[-1]
            channel_data = msg['message']['channel_data']
            tacho_freq = msg['message']['tacho_freq']
            tacho_trigger = msg['message']['tacho_trigger']
            self.sample_rate = msg.get('samplingRate', 4096)
            channel_samples = msg.get('samplingSize', 4096)
            tacho_samples = len(tacho_freq)

            # Validate data
            if len(channel_data) != self.num_channels or len(tacho_freq) != tacho_samples or len(tacho_trigger) != tacho_samples:
                self.clear_plots()
                if self.console:
                    self.console.append_to_console(f"Data length mismatch in {self.selected_filename}")
                return

            # Generate time arrays
            created_at = datetime.fromisoformat(msg['createdAt'].replace('Z', '+00:00')).timestamp()
            channel_time_step = 1.0 / self.sample_rate
            tacho_time_step = 1.0 / self.sample_rate
            self.channel_times = np.array([created_at - (channel_samples - 1) * channel_time_step + i * channel_time_step for i in range(channel_samples)])
            self.tacho_times = np.array([created_at - (tacho_samples - 1) * tacho_time_step + i * tacho_time_step for i in range(tacho_samples)])

            # Filter data within time range
            channel_mask = (self.channel_times >= self.start_time) & (self.channel_times <= self.end_time)
            tacho_mask = (self.tacho_times >= self.start_time) & (self.tacho_times <= self.end_time)
            self.channel_times = self.channel_times[channel_mask]
            self.tacho_times = self.tacho_times[tacho_mask]

            # Update data
            for ch in range(self.num_channels):
                self.data[ch] = np.array(channel_data[ch])[channel_mask]
            self.data[self.num_channels] = np.array(tacho_freq)[tacho_mask]
            self.data[self.num_channels + 1] = np.array(tacho_trigger)[tacho_mask]

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
                    self.plot_widgets[ch].setXRange(self.start_time, self.end_time, padding=0)
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

            if self.console:
                self.console.append_to_console(f"Time Report ({self.model_name}): Plotted {self.num_plots} plots for {self.selected_filename}")
        except Exception as e:
            logging.error(f"Error plotting data: {str(e)}")
            self.clear_plots()
            if self.console:
                self.console.append_to_console(f"Error plotting data: {str(e)}")

    def mouse_enter(self, idx):
        self.active_line_idx = idx
        self.vlines[idx].setVisible(True)

    def mouse_leave(self, idx):
        self.active_line_idx = None
        for vline in self.vlines:
            vline.setVisible(False)

    def mouse_moved(self, evt, idx):
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