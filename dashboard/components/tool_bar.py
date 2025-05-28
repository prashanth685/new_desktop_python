from PyQt5.QtWidgets import QToolBar, QAction, QWidget, QSizePolicy, QMessageBox
from PyQt5.QtCore import QSize

class ToolBar(QToolBar):
    def __init__(self, parent):
        super().__init__("Features", parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        self.setFixedHeight(80)
        self.update_toolbar()

    def update_toolbar(self):
        self.clear()
        self.setStyleSheet("""
            QToolBar { 
                background-color:#2C3E50;
                border: none; 
                padding: 5px; 
                spacing: 10px; 
            }
            QToolButton { 
                border: none; 
                border-radius: 6px; 
                font-size: 35px; 
                color: #eceff1; 
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
        """)
        self.setIconSize(QSize(30, 30))
        self.setMovable(False)
        self.setFloatable(False)

        def add_action(feature_name, text_icon, color, tooltip):
            action = QAction(text_icon, self)
            action.triggered.connect(lambda: self.validate_and_display(feature_name))
            action.setToolTip(tooltip)
            self.addAction(action)
            button = self.widgetForAction(action)
            if button:
                button.setStyleSheet(f"""
                    QToolButton {{ 
                        color: {color}; 
                        font-size: 35px; 
                        border: none; 
                        border-radius: 6px; 
                        transition: background-color 0.3s ease; 
                    }}
                    QToolButton:hover {{ background-color: #4a90e2; }}
                    QToolButton:pressed {{ background-color: #357abd; }}
                """)

        feature_actions = [
            ("Time View", "⏱️", "#ffb300", "Access Time View Feature"),
            ("Tabular View", "📋", "#64b5f6", "Access Tabular View Feature"),
            ("Time Report", "📄", "#4db6ac", "Access Time Report Feature"),
            ("FFT", "📈", "#ba68c8", "Access FFT View Feature"),
            ("Waterfall", "🌊", "#4dd0e1", "Access Waterfall Feature"),
            ("Orbit", "🪐", "#f06292", "Access Orbit Feature"),
            ("Trend View", "📉", "#aed581", "Access Trend View Feature"),
            ("Multiple Trend View", "📊", "#ff8a65", "Access Multiple Trend View Feature"),
            ("Bode Plot", "🔍", "#7986cb", "Access Bode Plot Feature"),
            ("History Plot", "🕰️", "#ef5350", "Access History Plot Feature"),
            ("Report", "📝", "#ab47bc", "Access Report Feature"),
        ]

        for feature_name, text_icon, color, tooltip in feature_actions:
            add_action(feature_name, text_icon, color, tooltip)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.addWidget(spacer)
    
    def validate_and_display(self,feature_name):
        model_based_features = {"Time View", "Time Report"}
        
        # If feature is model-based
        if feature_name in model_based_features:
            if not self.parent.tree_view.get_selected_model():
                QMessageBox.warning(self, "Selection Required", "Please select a model from the tree view first.")
                return
        else:
            if not self.parent.tree_view.get_selected_channel():
                QMessageBox.warning(self, "Selection Required", "Please select a channel from the tree view first.")
                return
        
        # If validation passes, proceed to display the feature
        self.parent.display_feature_content(feature_name, self.parent.current_project)