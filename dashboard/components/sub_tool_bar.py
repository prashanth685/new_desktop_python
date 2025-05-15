from PyQt5.QtWidgets import QToolBar, QAction, QWidget, QHBoxLayout, QLabel, QSizePolicy
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon

class SubToolBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        self.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #eceff1, stop:1 #cfd8dc);")
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)
        self.setLayout(layout)

        self.current_feature_label = QLabel("")
        self.current_feature_label.setStyleSheet("color: #333; font-size: 16px; font-weight: bold;")
        layout.addWidget(self.current_feature_label)

        self.toolbar = QToolBar("Controls")
        self.toolbar.setFixedHeight(100)
        layout.addWidget(self.toolbar)
        self.update_subtoolbar()

    def update_subtoolbar(self):
        self.toolbar.clear()
        self.toolbar.setStyleSheet("""
            QToolBar { 
                background: transparent; 
                border: none; 
                padding: 5px; 
                spacing: 10px; 
            }
            QToolButton { 
                border: none; 
                padding: 8px; 
                border-radius: 5px; 
                background-color: #90a4ae; 
                font-size: 24px; 
                color: white; 
                transition: background-color 0.3s ease; 
            }
            QToolButton:hover { 
                background-color: #4a90e2; 
            }
            QToolButton:pressed { 
                background-color: #357abd; 
            }
            QToolButton:focus { 
                outline: none; 
                border: 1px solid #4a90e2; 
            }
            QToolButton:disabled { 
                background-color: #546e7a; 
                color: #b0bec5; 
            }
        """)
        self.toolbar.setIconSize(QSize(25, 25))
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)

        def add_action(text_icon, color, callback, tooltip, enabled, background_color):
            action = QAction(text_icon, self)
            action.triggered.connect(callback)
            action.setToolTip(tooltip)
            action.setEnabled(enabled)
            self.toolbar.addAction(action)
            button = self.toolbar.widgetForAction(action)
            if button:
                button.setStyleSheet(f"""
                    QToolButton {{ 
                        color: {color}; 
                        font-size: 24px; 
                        border: none; 
                        padding: 8px; 
                        border-radius: 5px; 
                        background-color: {background_color}; 
                        transition: background-color 0.3s ease; 
                    }}
                    QToolButton:hover {{ background-color: #4a90e2; }}
                    QToolButton:pressed {{ background-color: #357abd; }}
                    QToolButton:disabled {{ background-color: #546e7a; color: #b0bec5; }}
                """)

        is_time_view = self.parent.current_feature == "Time View"
        add_action("▶", "#ffffff", self.parent.start_saving, "Start Saving Data (Time View)", is_time_view and not self.parent.is_saving, "#43a047")
        add_action("⏸", "#ffffff", self.parent.stop_saving, "Stop Saving Data (Time View)", is_time_view and self.parent.is_saving, "#ef5350")
        self.toolbar.addSeparator()

        connect_bg = "#43a047" if self.parent.mqtt_connected else "#90a4ae"
        disconnect_bg = "#ef5350" if not self.parent.mqtt_connected else "#90a4ae"
        add_action("🟢", "#ffffff", self.parent.connect_mqtt, "Connect to MQTT", not self.parent.mqtt_connected, connect_bg)
        add_action("🔴", "#ffffff", self.parent.disconnect_mqtt, "Disconnect from MQTT", self.parent.mqtt_connected, disconnect_bg)
        self.toolbar.addSeparator()

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)

        add_action(
            "🧮", "#ffffff",
            lambda: self.parent.main_section.arrange_layout(prompt_for_layout=True),
            "Select and Arrange Sub-Windows in Grid Layout (1x2, 1x3, 2x2, 3x3)",
            True, "#90a4ae"
        )