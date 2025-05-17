from PyQt5.QtWidgets import QLabel

class MQTTStatus(QLabel):
    def __init__(self, parent):
        super().__init__("MQTT Connection 🔴", parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        self.setToolTip("MQTT Connection Status")
        self.setStyleSheet("""
            QLabel {
                background-color: black;
                color: #FFFFFF;
                font-size: 14px;
                font:bold;
                padding: 2px 8px;
                border-radius: 0px;
            }
        """)

    def update_mqtt_status_indicator(self):
        status_icon = "🔴" if self.parent.mqtt_connected else "🟢"
        self.setText(f"MQTT Connection status {status_icon}")
        self.setStyleSheet("""
            QLabel {
                background-color: black;
                color: #FFFFFF;
                font-size: 14px;
                font:bold;
                padding: 2px 8px;
                border-radius: 0px;
            }
        """)