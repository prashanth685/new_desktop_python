from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QPushButton, QLabel, QMessageBox, QScrollArea,QApplication
import sys
from PyQt5.QtCore import Qt
import logging


app = QApplication(sys.argv)

# 🌐 Global stylesheet for QMessageBox
app.setStyleSheet("""
    QMessageBox {
        background-color: #fefefe;
        color: #1a202c;
        font: 13px "Segoe UI";
        border: 1px solid #cbd5e0;
        padding: 10px;
    }

    QMessageBox QLabel {
        color: #1a202c;
    }

    QMessageBox QPushButton {
        background-color: #3b82f6;
        color: white;
        border: none;
        padding: 6px 12px;
        border-radius: 4px;
        min-width: 80px;
        font-weight: 500;
    }

    QMessageBox QPushButton:hover {
        background-color: #2563eb;
    }

    QMessageBox QPushButton:pressed {
        background-color: #1d4ed8;
    }
""")

class CreateProjectWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.db = parent.db
        self.models = []
        self.initUI()

    def initUI(self):
        self.setStyleSheet("background-color: #f7f7f9;")

        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(40, 20, 40, 20)
        self.setLayout(main_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #e0e4e8;
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #a0a8b2;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #7a8290;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        main_layout.addWidget(scroll_area)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_layout.setAlignment(Qt.AlignCenter)
        scroll_layout.setSpacing(24)
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)

        card_widget = QWidget()
        card_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
                padding: 24px;
            }
        """)
        card_layout = QVBoxLayout()
        card_layout.setSpacing(16)
        card_widget.setLayout(card_layout)
        scroll_layout.addWidget(card_widget)

        title_label = QLabel("Create New Project")
        title_label.setStyleSheet("""
            font-size: 20px;
            font-weight: 600;
            color: #1a202c;
            margin-bottom: 8px;
        """)
        card_layout.addWidget(title_label, alignment=Qt.AlignCenter)

        subtitle_label = QLabel("Start by defining project details and models")
        subtitle_label.setStyleSheet("""
            font-size: 14px;
            color: #6b7280;
            margin-bottom: 16px;
        """)
        card_layout.addWidget(subtitle_label, alignment=Qt.AlignCenter)

        project_details_label = QLabel("Project Details")
        project_details_label.setStyleSheet("""
            font-size: 16px;
            font-weight: 500;
            color: #1a202c;
            margin-top: 16px;
            margin-bottom: 8px;
        """)
        card_layout.addWidget(project_details_label)

        project_form = QFormLayout()
        project_form.setSpacing(12)
        project_form.setLabelAlignment(Qt.AlignLeft)
        project_form.setFormAlignment(Qt.AlignCenter)
        self.project_name_input = QLineEdit()
        self.project_name_input.setPlaceholderText("Project name")
        self.project_name_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
                min-width: 400px;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
                outline: none;
            }
            QLineEdit:hover {
                border-color: #93c5fd;
            }
        """)
        project_form.addRow(self.project_name_input)
        card_layout.addLayout(project_form)

        add_model_button = QPushButton("+ Add Model")
        add_model_button.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
                font-weight: 500;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)
        add_model_button.clicked.connect(self.add_model_input)
        card_layout.addWidget(add_model_button, alignment=Qt.AlignRight)

        self.model_layout = QVBoxLayout()
        self.model_layout.setSpacing(16)
        self.model_inputs = []
        card_layout.addLayout(self.model_layout)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        button_layout.setAlignment(Qt.AlignLeft)

        back_button = QPushButton("Back")
        back_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #6b7280;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
                font-weight: 500;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #f1f5f9;
            }
            QPushButton:pressed {
                background-color: #e2e8f0;
            }
        """)
        back_button.clicked.connect(self.back_to_select)
        button_layout.addWidget(back_button)

        create_button = QPushButton("Create Project")
        create_button.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
                font-weight: 500;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)
        create_button.clicked.connect(self.create_project)
        button_layout.addWidget(create_button)

        card_layout.addLayout(button_layout)

    def add_model_input(self):
        model_widget = QWidget()
        model_widget.setStyleSheet("""
            background-color: #fafafa;
            border-radius: 4px;
            padding: 16px;
            border: 1px solid #e5e7eb;
        """)
        model_layout = QVBoxLayout()
        model_layout.setSpacing(12)
        model_widget.setLayout(model_layout)

        model_header_layout = QHBoxLayout()
        model_header_layout.setSpacing(8)
        model_label = QLabel(f"Model {len(self.model_inputs) + 1}")
        model_label.setStyleSheet("""
            font-size: 16px;
            font-weight: 500;
            color: #1a202c;
        """)
        model_header_layout.addWidget(model_label)

        remove_model_button = QPushButton("Remove Model")
        remove_model_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ef4444;
                border: none;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                color: #dc2626;
            }
            QPushButton:pressed {
                color: #b91c1c;
            }
        """)
        remove_model_button.clicked.connect(lambda: self.remove_model_input(model_widget))
        model_header_layout.addWidget(remove_model_button, alignment=Qt.AlignRight)
        model_layout.addLayout(model_header_layout)

        model_form = QFormLayout()
        model_form.setSpacing(12)
        model_form.setLabelAlignment(Qt.AlignLeft)
        model_form.setFormAlignment(Qt.AlignCenter)

        model_name_input = QLineEdit()
        model_name_input.setPlaceholderText("Model name")
        model_name_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
                min-width: 400px;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
                outline: none;
            }
            QLineEdit:hover {
                border-color: #93c5fd;
            }
        """)
        model_form.addRow(model_name_input)

        tag_name_input = QLineEdit()
        tag_name_input.setPlaceholderText("Tag name")
        tag_name_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
                min-width: 400px;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
                outline: none;
            }
            QLineEdit:hover {
                border-color: #93c5fd;
            }
        """)
        model_form.addRow(tag_name_input)
        model_layout.addLayout(model_form)

        channels_label = QLabel("Channels")
        channels_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 500;
            color: #1a202c;
            margin-top: 8px;
            margin-bottom: 8px;
        """)
        model_layout.addWidget(channels_label)

        # Create a container for channel inputs
        channel_container = QWidget()
        channel_layout = QVBoxLayout()
        channel_layout.setSpacing(12)
        channel_container.setLayout(channel_layout)
        model_layout.addWidget(channel_container)

        # Track channel inputs for this model
        channel_inputs = []

        def add_channel_input():
            channel_widget = QWidget()
            channel_form = QHBoxLayout()
            channel_form.setSpacing(12)
            channel_widget.setLayout(channel_form)

            channel_name_input = QLineEdit()
            channel_name_input.setPlaceholderText("Channel name")
            channel_name_input.setStyleSheet("""
                QLineEdit {
                    border: 1px solid #d1d5db;
                    border-radius: 4px;
                    padding: 8px;
                    font-size: 14px;
                    min-width: 400px;
                    background-color: #ffffff;
                }
                QLineEdit:focus {
                    border-color: #3b82f6;
                    outline: none;
                }
                QLineEdit:hover {
                    border-color: #93c5fd;
                }
            """)
            channel_form.addWidget(channel_name_input)

            remove_channel_button = QPushButton("- Remove")
            remove_channel_button.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #ef4444;
                    border: none;
                    font-size: 14px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    color: #dc2626;
                }
                QPushButton:pressed {
                    color: #b91c1c;
                }
            """)
            remove_channel_button.clicked.connect(lambda: remove_channel(channel_widget))
            channel_form.addWidget(remove_channel_button)

            channel_inputs.append((channel_widget, channel_name_input))
            channel_layout.addWidget(channel_widget)
            channel_container.adjustSize()

        def remove_channel(channel_widget):
            if len(channel_inputs) > 1:
                for widget, _ in channel_inputs:
                    if widget == channel_widget:
                        channel_inputs.remove((widget, _))
                        channel_layout.removeWidget(widget)
                        widget.deleteLater()
                        channel_container.adjustSize()
                        break

        add_channel_button = QPushButton("+ Add Channel")
        add_channel_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #3b82f6;
                border: none;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                color: #2563eb;
            }
            QPushButton:pressed {
                color: #1d4ed8;
            }
        """)
        add_channel_button.clicked.connect(add_channel_input)
        model_layout.addWidget(add_channel_button)

        add_channel_input()  # Add the first channel by default
        self.model_inputs.append((model_widget, model_name_input, tag_name_input, channel_inputs))
        self.model_layout.addWidget(model_widget)

    def remove_model_input(self, model_widget):
        if len(self.model_inputs) > 1:
            for widget, _, _, _ in self.model_inputs:
                if widget == model_widget:
                    self.model_inputs.remove((widget, _, _, _))
                    self.model_layout.removeWidget(widget)
                    widget.deleteLater()
                    break

    def create_project(self):
        project_name = self.project_name_input.text().strip()
        if not project_name:
            QMessageBox.warning(self, "Error", "Project name cannot be empty!")
            return

        self.models = []
        for _, model_name_input, tag_name_input, channel_inputs in self.model_inputs:
            model_name = model_name_input.text().strip()
            tag_name = tag_name_input.text().strip()
            if not model_name:
                QMessageBox.warning(self, "Error", "Model name cannot be empty!")
                return
            if not tag_name:
                QMessageBox.warning(self, "Error", f"Tag name cannot be empty for model '{model_name}'!")
                return

            channels = []
            for _, channel_name_input in channel_inputs:
                channel_name = channel_name_input.text().strip()
                if not channel_name:
                    QMessageBox.warning(self, "Error", f"Channel name cannot be empty for model '{model_name}'!")
                    return
                channels.append({"channel_name": channel_name})

            if not channels:
                QMessageBox.warning(self, "Error", f"At least one channel is required for model '{model_name}'!")
                return

            self.models.append({"name": model_name, "tag_name": tag_name, "channels": channels})

        if not self.models:
            QMessageBox.warning(self, "Error", "At least one model with a tag and channels is required!")
            return

        try:
            models_for_db = [{"name": model["name"], "channels": model["channels"]} for model in self.models]
            success, message = self.db.create_project(project_name, models_for_db)
            if success:
                for model in self.models:
                    tag_data = {"tag_name": model["tag_name"]}
                    self.db.add_tag(project_name, model["name"], tag_data)
                QMessageBox.information(self, "Success", message)
                logging.info(f"Created new project: {project_name} with {len(self.models)} models")
                logging.debug(f"Calling load_project for project: {project_name}")
                self.parent.load_project(project_name)
            else:
                QMessageBox.warning(self, "Error", message)
        except Exception as e:
            logging.error(f"Error creating project: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to create project: {str(e)}")

    def back_to_select(self):
        logging.debug("Returning to project selection UI")
        self.parent.display_select_project()