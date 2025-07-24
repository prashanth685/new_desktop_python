from PyQt5.QtWidgets import (
    QToolBar, QToolButton, QWidget, QSizePolicy,
    QMessageBox, QLabel, QVBoxLayout
)
from PyQt5.QtGui import QColor

from PyQt5.QtCore import QSize, Qt
import logging

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
                background-color: #3C3F41;
                border: none; 
                padding: 5px; 
                spacing: 10px; 
            }
            QToolButton {
                color: white;
                font-size: 11px;
                font-weight: bold;
                border: none;
                border-radius: 5px;
                padding: 5px;
            }
            QToolButton:hover {
                background-color: #4a90e2;
            }
            QToolButton:pressed {
                background-color: #357abd;
            }
        """)
        self.setMovable(False)
        self.setFloatable(False)

        def add_action(feature_name, text_icon, color, tooltip):
            # Create a button
            button = QToolButton()
            button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            button.setToolTip(tooltip)
            button.setFixedSize(64, 64)

            # Use emoji as icon via QLabel
            icon_label = QLabel(text_icon)
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setStyleSheet(f"font-size: 24px; color: {color};")
            icon_label.setFixedSize(24, 24)

            # Text label with proper alignment
            text_label = QLabel(feature_name)
            text_label.setWordWrap(True)
            text_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
            text_label.setStyleSheet(f"font-size: 10px; color: white; font-weight: bold;")
            text_label.setFixedSize(60, 24)

            # Layout to stack icon and label
            layout = QVBoxLayout()
            layout.setContentsMargins(0, 4, 0, 4)
            layout.setSpacing(2)
            layout.addWidget(icon_label, alignment=Qt.AlignHCenter)
            layout.addWidget(text_label, alignment=Qt.AlignHCenter)
            layout.setAlignment(Qt.AlignCenter)

            # Container widget for button content
            content = QWidget()
            content.setLayout(layout)
            button.setLayout(layout)
            button.clicked.connect(lambda _, name=feature_name: self.validate_and_display(name))

            self.addWidget(button)
            spacer = QWidget()
            spacer.setFixedWidth(8)
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
            ("Polar Plot", "❄️", "#7986cb", "Access Polar Plot Feature"),       
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

        # Check if a model is selected; if not, attempt to auto-select one
        selected_model = self.parent.tree_view.get_selected_model()
        if not selected_model and feature_name in model_based_features:
            # Try to auto-select the first model
            project_data = self.parent.db.get_project_data(self.parent.current_project)
            if project_data and "models" in project_data and project_data["models"]:
                first_model = project_data["models"][0].get("name")
                if first_model:
                    self.parent.tree_view.selected_model = first_model
                    # Update tree view selection
                    for i in range(self.parent.tree_view.tree.topLevelItemCount()):
                        project_item = self.parent.tree_view.tree.topLevelItem(i)
                        for j in range(project_item.childCount()):
                            model_item = project_item.child(j)
                            if model_item.data(0, Qt.UserRole).get("type") == "model" and \
                               model_item.data(0, Qt.UserRole).get("name") == first_model:
                                self.parent.tree_view.tree.setCurrentItem(model_item)
                                model_item.setBackground(0, QColor("#4a90e2"))
                                logging.info(f"Auto-selected model for feature {feature_name}: {first_model}")
                                self.parent.console.append_to_console(f"Auto-selected model for feature {feature_name}: {first_model}")
                                break
                    selected_model = first_model

        # Validate model selection for model-based features
        if feature_name in model_based_features:
            if not selected_model:
                QMessageBox.warning(self, "Selection Required", "No models available. Please create a model first.")
                return
        else:
            # For channel-based features, ensure a channel is selected
            if not self.parent.tree_view.get_selected_channel():
                # Try to auto-select the first channel of the selected model
                selected_model = self.parent.tree_view.get_selected_model()
                if selected_model:
                    project_data = self.parent.db.get_project_data(self.parent.current_project)
                    for model in project_data.get("models", []):
                        if model.get("name") == selected_model and model.get("channels"):
                            first_channel = model["channels"][0].get("channelName", f"Channel_1")
                            tag_name = model.get("tagName", first_channel)
                            self.parent.tree_view.selected_channel = tag_name
                            # Update tree view selection
                            for i in range(self.parent.tree_view.tree.topLevelItemCount()):
                                project_item = self.parent.tree_view.tree.topLevelItem(i)
                                for j in range(project_item.childCount()):
                                    model_item = project_item.child(j)
                                    if model_item.data(0, Qt.UserRole).get("name") == selected_model:
                                        for k in range(model_item.childCount()):
                                            channel_item = model_item.child(k)
                                            if channel_item.data(0, Qt.UserRole).get("channel_name") == first_channel:
                                                self.parent.tree_view.tree.setCurrentItem(channel_item)
                                                channel_item.setBackground(0, QColor("#28a745"))
                                                self.parent.tree_view.selected_channel_item = channel_item
                                                logging.info(f"Auto-selected channel for feature {feature_name}: {first_channel}")
                                                self.parent.console.append_to_console(f"Auto-selected channel for feature {feature_name}: {first_channel}")
                                                break
                                        break
                            if self.parent.tree_view.get_selected_channel():
                                break
                if not self.parent.tree_view.get_selected_channel():
                    QMessageBox.warning(self, "Selection Required", "Please select a channel from the tree view first.")
                    return

        # Proceed to display the feature
        self.parent.display_feature_content(feature_name, self.parent.current_project)