from PyQt5.QtWidgets import QToolBar, QAction, QWidget, QHBoxLayout, QSizePolicy, QMenu, QComboBox, QLabel
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon

class SubToolBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.selected_layout = "2x2"  # Default layout
        self.filename_combo = None
        self.initUI()

    def initUI(self):
        self.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #eceff1, stop:1 #cfd8dc);")
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.setLayout(layout)

        self.toolbar = QToolBar("Controls")
        self.toolbar.setFixedHeight(100)
        layout.addWidget(self.toolbar)
        self.update_subtoolbar()

    def update_subtoolbar(self):
        self.toolbar.clear()
        self.toolbar.setStyleSheet("""
            QToolBar { 
                border: none; 
                padding: 5px; 
                spacing: 10px; 
            }
            QToolButton { 
                border: none; 
                padding: 8px; 
                border-radius: 5px; 
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

        self.filename_combo = QComboBox()
        self.filename_combo.setStyleSheet("""
            QComboBox {
                background-color: #ffffff;
                color: #212121;
                border: 1px solid #90caf9;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
                font-weight: 500;
                min-width: 200px;
                max-width: 250px;
            }
            QComboBox:hover {
                border: 1px solid #42a5f5;
                background-color: #f5faff;
            }
            QComboBox:focus {
                border: 1px solid #1e88e5;
                background-color: #ffffff;
            }
            QComboBox::drop-down {
                width: 25px;
                border-left: 1px solid #e0e0e0;
                background-color: #e3f2fd;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #90caf9;
                border-radius: 4px;
                padding: 3px;
                selection-background-color: #e3f2fd;
                selection-color: #0d47a1;
                font-size: 14px;
                outline: 0;
            }
            QComboBox::item {
                padding: 4px 6px;
            }
            QComboBox::item:selected {
                background-color: #bbdefb;
                color: #0d47a1;
            }
        """)
        self.filename_combo.setEnabled(False)
        self.refresh_filenames()
        self.toolbar.addWidget(self.filename_combo)
        self.toolbar.addSeparator()

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
                        transition: background-color 0.3s ease; 
                    }}
                    QToolButton:hover {{ background-color: #4a90e2; }}
                    QToolButton:pressed {{ background-color: #357abd; }}
                    QToolButton:disabled {{ background-color: #546e7a; color: #b0bec5; }}
                """)

        is_time_view = self.parent.current_feature == "Time View"
        add_action("▶", "#ffffff", self.parent.start_saving, "Start Saving Data (Time View)", is_time_view and not self.parent.is_saving, "#43a047")
        add_action("⏸", "#ffffff", self.parent.stop_saving, "Stop Saving Data (Time View)", is_time_view and self.parent.is_saving, "")
        self.toolbar.addSeparator()

        connect_bg = "#43a047" if self.parent.mqtt_connected else "#90a4ae"
        disconnect_bg = "#ef5350" if not self.parent.mqtt_connected else "#90a4ae"
        add_action("🔗", "#ffffff", self.parent.connect_mqtt, "Connect to MQTT", not self.parent.mqtt_connected, connect_bg)
        add_action("❌", "#ffffff", self.parent.disconnect_mqtt, "Disconnect from MQTT", self.parent.mqtt_connected, disconnect_bg)
        self.toolbar.addSeparator()

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)

        layout_action = QAction("🖼️", self)
        layout_action.setToolTip("Select Layout")
        layout_action.triggered.connect(self.show_layout_menu)
        self.toolbar.addAction(layout_action)
        layout_button = self.toolbar.widgetForAction(layout_action)
        if layout_button:
            layout_button.setStyleSheet("""
                QToolButton { 
                    color: #ffffff; 
                    font-size: 24px; 
                    border: none; 
                    padding: 8px; 
                    border-radius: 5px; 
                    transition: background-color 0.3s ease; 
                }
                QToolButton:hover { background-color: #4a90e2; }
                QToolButton:pressed { background-color: #357abd; }
            """)

    def refresh_filenames(self):
        if not self.filename_combo:
            return
        self.filename_combo.clear()
        if self.parent.current_feature == "Time View" and hasattr(self.parent.current_widget, 'refresh_filenames'):
            filenames = self.parent.current_widget.refresh_filenames()
            for filename in filenames:
                self.filename_combo.addItem(filename)
            filename_counter = self.parent.current_widget.filename_counter
            self.filename_combo.addItem(f"data{filename_counter}")
            self.filename_combo.setCurrentText(f"data{filename_counter}")

    def show_layout_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #90a4ae;
                color: white;
                border: 1px solid #4a90e2;
                border-radius: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #4a90e2;
            }
        """)

        layouts = ["1x2", "2x2", "3x3"]
        for layout in layouts:
            action = QAction(layout, self)
            action.triggered.connect(lambda checked, l=layout: self.on_layout_selected(l))
            menu.addAction(action)

        # ok_action = QAction("Ok", self)
        # menu.addAction(ok_action)

        # cancel_action = QAction("Cancel", self)
        # menu.addAction(cancel_action)

        layout_button = self.toolbar.widgetForAction(self.toolbar.actions()[-1])
        menu.exec_(layout_button.mapToGlobal(layout_button.rect().bottomLeft()))

    def on_layout_selected(self, layout):
        self.selected_layout = layout
        self.parent.main_section.arrange_layout(layout=self.selected_layout)