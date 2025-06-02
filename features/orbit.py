from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
import pyqtgraph as pg
import numpy as np

class OrbitFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.channel = channel
        self.model_name = model_name
        self.console = console
        self.widget = None
        self.plot_widget = None
        self.plot_item = None
        self.initUI()

    def initUI(self):
        self.widget = QWidget()
        layout = QVBoxLayout()
        self.widget.setLayout(layout)

        # Label
        label = QLabel(f"Orbit Plot for Model: {self.model_name if self.model_name else 'None'}")
        layout.addWidget(label)

        # PyQtGraph PlotWidget
        self.plot_widget = pg.PlotWidget()
        layout.addWidget(self.plot_widget)

        # Configure plot
        self.plot_item = self.plot_widget.getPlotItem()
        self.plot_item.setTitle("Orbit Plot (Channel 2 vs Channel 1)")
        self.plot_item.setLabel('bottom', "X")
        self.plot_item.setLabel('left', "Y")
        self.plot_item.showGrid(x=True, y=True)
        self.plot_item.setAspectLocked(True)  # Lock aspect ratio for circular orbits
        self.plot_item.enableAutoRange('xy', True)

        # Initialize empty plot
        self.data_plot = self.plot_item.plot(pen='b')

        if not self.model_name and self.console:
            self.console.append_to_console("No model selected in OrbitFeature.")

    def on_data_received(self, tag_name, model_name, values, sample_rate):
        """Handle incoming data and update Orbit plot."""
        if self.model_name != model_name:
            return  # Ignore data for other models

        if self.console:
            self.console.append_to_console(
                f"Orbit View ({self.model_name}): Received data for {tag_name} - {len(values)} channels"
            )

        if not values or len(values) < 2:
            if self.console:
                self.console.append_to_console("Need at least 2 channels (X and Y) for orbit plot.")
            return

        # Use Channel 1 (X) and Channel 2 (Y)
        x_data = np.array(values[0])  # Channel 1
        y_data = np.array(values[1])  # Channel 2

        if len(x_data) != len(y_data):
            if self.console:
                self.console.append_to_console("Mismatched lengths between Channel 1 and Channel 2 data.")
            return

        # Update orbit plot
        self.data_plot.setData(x_data, y_data)

    def get_widget(self):
        return self.widget