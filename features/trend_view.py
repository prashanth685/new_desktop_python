from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
import pyqtgraph as pg

class TrendViewFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.channel = channel
        self.model_name = model_name
        self.console = console
        self.widget = None
        self.data_x = []
        self.data_y = []
        self.plot_curve = None
        self.initUI()

    def initUI(self):
        self.widget = QWidget()
        layout = QVBoxLayout(self.widget)

        self.label = QLabel(f"Trend View for Model: {self.model_name}, Channel: {self.channel}")
        layout.addWidget(self.label)

        # pyqtgraph PlotWidget
        self.plot_widget = pg.PlotWidget(title="Trend Data")
        self.plot_widget.setLabel('left', 'Value')
        self.plot_widget.setLabel('bottom', 'Sample Index')
        layout.addWidget(self.plot_widget)

        # Create a plot curve object for real-time updates
        self.plot_curve = self.plot_widget.plot(pen=pg.mkPen(color='b', width=2))

        if not self.model_name and self.console:
            self.console.append_to_console("No model selected in TrendViewFeature.")
        if not self.channel and self.console:
            self.console.append_to_console("No channel selected in TrendViewFeature.")

    def get_widget(self):
        return self.widget

    def on_data_received(self, tag_name, model_name, values):
        if self.model_name != model_name:
            return  # Ignore unrelated data

        if not isinstance(values, list):
            values = [values]

        start_index = len(self.data_x)
        self.data_x.extend(range(start_index, start_index + len(values)))
        self.data_y.extend(values)

        self.update_plot()

        if self.console:
            self.console.append_to_console(
                f"Trend View ({self.model_name} - {self.channel}): Received data for {tag_name} - {values}"
            )

    def update_plot(self):
        self.plot_curve.setData(self.data_x, self.data_y)
