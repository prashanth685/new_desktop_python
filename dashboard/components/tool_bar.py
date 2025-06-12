from PyQt5.QtWidgets import (
    QToolBar, QToolButton, QWidget, QSizePolicy,
    QMessageBox, QLabel, QVBoxLayout
)
from PyQt5.QtCore import QSize, Qt


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
                background-color: #2C3E50;
                border: none; 
                padding: 5px; 
                spacing: 10px; 
            }
        """)
        self.setMovable(False)
        self.setFloatable(False)

        def add_action(feature_name, text_icon, color, tooltip):
            # Create a button
            button = QToolButton()
            button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            button.setToolTip(tooltip)
            button.setFixedSize(70, 70)

            # Use emoji as icon via QLabel
            icon_label = QLabel(text_icon)
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setStyleSheet(f"font-size: 28px; color: {color};")

            text_label = QLabel(feature_name)
            text_label.setWordWrap(True)

            text_label.setAlignment(Qt.AlignCenter)
            text_label.setStyleSheet(f"font-size: 11px; color: white;font:bold")

            # Layout to stack icon and label
            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(15)
            layout.addWidget(icon_label)
            layout.addWidget(text_label)

            # Container widget for button content
            content = QWidget()
            content.setLayout(layout)
            button.setLayout(layout)
            button.clicked.connect(lambda _, name=feature_name: self.validate_and_display(name))

            self.addWidget(button)
            spacer = QWidget()
            spacer.setFixedWidth(10)
            self.addWidget(spacer)


        feature_actions = [
            ("Time View", "⏱️", "#ffb300", "Access Time View Feature"),
            ("Tabular View", "📋", "#64b5f6", "Access Tabular View Feature"),
            ("Time Report", "📄", "#4db6ac", "Access Time Report Feature"),
            ("FFT", "📈", "#ba68c8", "Access FFT View Feature"),
            ("Waterfall", "🌊", "#4dd0e1", "Access Waterfall Feature"),
            ("Centerline", "📏", "#4dd0e1", "Access Centerline Feature"),     
            ("Orbit", "🪐", "#f06292", "Access Orbit Feature"),
            ("Trend View", "📉", "#aed581", "Access Trend View Feature"),
            ("Multiple Trend View", "📊", "#ff8a65", "Access Multiple Trend View Feature"),
            ("Bode Plot", "🔍", "#7986cb", "Access Bode Plot Feature"),
            ("History Plot", "🕰️", "#ef5350", "Access History Plot Feature"),
            ("Report", "📝", "#ab47bc", "Access Report Feature"),
        ]

        for feature_name, text_icon, color, tooltip in feature_actions:
            add_action(feature_name, text_icon, color, tooltip)

        # Add a spacer to push buttons to the left
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.addWidget(spacer)

    def validate_and_display(self, feature_name):
        model_based_features = {"Time View", "Time Report"}

        if feature_name in model_based_features:
            if not self.parent.tree_view.get_selected_model():
                QMessageBox.warning(self, "Selection Required", "Please select a model from the tree view first.")
                return
        else:
            if not self.parent.tree_view.get_selected_channel():
                QMessageBox.warning(self, "Selection Required", "Please select a channel from the tree view first.")
                return

        # Proceed to display the feature
        self.parent.display_feature_content(feature_name, self.parent.current_project)



# import os
# from PyQt5.QtWidgets import (
#     QToolBar, QToolButton, QWidget, QSizePolicy, QMessageBox
# )
# from PyQt5.QtCore import QSize, Qt
# from PyQt5.QtGui import QIcon

# class ToolBar(QToolBar):
#     def __init__(self, parent):
#         super().__init__("Features", parent)
#         self.parent = parent
#         self.initUI()

#     def initUI(self):
#         self.setFixedHeight(80)
#         self.update_toolbar()

#     def update_toolbar(self):
#         self.clear()
#         self.setStyleSheet("""
#             QToolBar { 
#                 background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f5f5f5, stop:1 #e0e0e0);
#                 border: none; 
#                 padding: 5px; 
#                 spacing: 10px; 
#             }
#             QToolButton {
#                 color: white;
#                 font-size: 11px;
#                 font-weight: bold;
#             }
#         """)
#         self.setMovable(False)
#         self.setFloatable(False)

#         def add_action(feature_name, icon_filename, tooltip):
#             # Create a button
#             button = QToolButton()
#             button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
#             button.setToolTip(tooltip)
#             button.setFixedSize(70, 70)

#             # Load icon from the specified path
#             icon_path = os.path.join(r"C:\Users\Prashanth S\Desktop\new_one\icons", icon_filename)
#             if not os.path.exists(icon_path):
#                 print(f"Warning: Icon file {icon_path} not found.")
#                 button.setText(feature_name)  # Fallback to text if icon is missing
#             else:
#                 button.setIcon(QIcon(icon_path))
#                 button.setIconSize(QSize(32, 32))  # Adjust icon size

#             # Set button text
#             button.setText(feature_name)

#             # Connect button click to validation function
#             button.clicked.connect(lambda _, name=feature_name: self.validate_and_display(name))

#             self.addWidget(button)
#             spacer = QWidget()
#             spacer.setFixedWidth(10)
#             self.addWidget(spacer)

#         # Define feature actions with corresponding .png icon filenames
#         feature_actions = [
#             ("Time View", "clock.png", "Access Time View Feature"),
#             ("Tabular View", "table.png", "Access Tabular View Feature"),
#             ("Time Report", "report-time.png", "Access Time Report Feature"),
#             ("FFT", "waveform.png", "Access FFT View Feature"),
#             ("Waterfall", "waterfall.png", "Access Waterfall Feature"),
#             ("Centerline", "ruler.png", "Access Centerline Feature"),
#             ("Orbit", "orbit.png", "Access Orbit Feature"),
#             ("Trend View", "trend.png", "Access Trend View Feature"),
#             ("Multiple Trend View", "multi-trend.png", "Access Multiple Trend View Feature"),
#             ("Bode Plot", "bode.png", "Access Bode Plot Feature"),
#             ("History Plot", "history.png", "Access History Plot Feature"),
#             ("Report", "report.png", "Access Report Feature"),
#         ]

#         # Add actions to toolbar
#         for feature_name, icon_filename, tooltip in feature_actions:
#             add_action(feature_name, icon_filename, tooltip)

#         # Add a spacer to push buttons to the left
#         spacer = QWidget()
#         spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
#         self.addWidget(spacer)

#     def validate_and_display(self, feature_name):
#         model_based_features = {"Time View", "Time Report"}

#         if feature_name in model_based_features:
#             if not self.parent.tree_view.get_selected_model():
#                 QMessageBox.warning(self, "Selection Required", "Please select a model from the tree view first.")
#                 return
#         else:
#             if not self.parent.tree_view.get_selected_channel():
#                 QMessageBox.warning(self, "Selection Required", "Please select a channel from the tree view first.")
#                 return

#         # Proceed to display the feature
#         self.parent.display_feature_content(feature_name, self.parent.current_project)