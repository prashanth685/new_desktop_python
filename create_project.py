from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout,QFormLayout, QLineEdit, QPushButton, QLabel, QMessageBox, QScrollArea
from PyQt5.QtCore import Qt
import logging

# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class CreateProjectWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.db = parent.db
        self.models = []
        self.initUI()

    def initUI(self):
        self.setStyleSheet("background-color: #f5f7fa;")
        
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(40, 40, 40, 40)
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
                background: #e9ecef;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #adb5bd;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #6c757d;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        main_layout.addWidget(scroll_area)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_layout.setAlignment(Qt.AlignCenter)
        scroll_layout.setSpacing(20)
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)

        card_widget = QWidget()
        card_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 15px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                padding: 30px;
            }
        """)
        card_layout = QVBoxLayout()
        card_layout.setSpacing(15)
        card_widget.setLayout(card_layout)
        scroll_layout.addWidget(card_widget)

        title_label = QLabel("Create New Project")
        title_label.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #343a40;
            margin-bottom: 20px;
        """)
        card_layout.addWidget(title_label, alignment=Qt.AlignCenter)

        project_form = QFormLayout()
        project_form.setSpacing(10)
        project_form.setLabelAlignment(Qt.AlignRight)
        project_form.setFormAlignment(Qt.AlignCenter)
        self.project_name_input = QLineEdit()
        self.project_name_input.setPlaceholderText("Enter project name")
        self.project_name_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ced4da;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                min-width: 400px;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border: 1px solid #007bff;
                box-shadow: 0 0 5px rgba(0, 123, 255, 0.5);
            }
        """)
        project_form.addRow("Project Name:", self.project_name_input)
        card_layout.addLayout(project_form)

        self.model_layout = QVBoxLayout()
        self.model_layout.setSpacing(15)
        self.model_inputs = []
        self.add_model_input()
        card_layout.addWidget(QLabel("Models and Channels:"))
        card_layout.addLayout(self.model_layout)

        add_model_button = QPushButton("Add Another Model")
        add_model_button.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                font-weight: bold;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
            QPushButton:pressed {
                background-color: #117a8b;
            }
        """)
        add_model_button.clicked.connect(self.add_model_input)
        card_layout.addWidget(add_model_button, alignment=Qt.AlignCenter)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)

        create_button = QPushButton("Create")
        create_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """)
        create_button.clicked.connect(self.create_project)
        button_layout.addWidget(create_button)

        back_button = QPushButton("Back")
        back_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #4b5359;
            }
        """)
        back_button.clicked.connect(self.back_to_select)
        button_layout.addWidget(back_button)

        card_layout.addLayout(button_layout)

    def add_model_input(self):
        model_widget = QWidget()
        model_widget.setStyleSheet("background-color: #f8f9fa; border-radius: 10px; padding: 15px;")
        model_layout = QFormLayout()
        model_layout.setSpacing(10)
        model_layout.setLabelAlignment(Qt.AlignRight)
        model_layout.setFormAlignment(Qt.AlignCenter)
        model_widget.setLayout(model_layout)

        model_name_input = QLineEdit()
        model_name_input.setPlaceholderText("Enter model name")
        model_name_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ced4da;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                min-width: 400px;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border: 1px solid #007bff;
                box-shadow: 0 0 5px rgba(0, 123, 255, 0.5);
            }
        """)
        model_layout.addRow("Model Name:", model_name_input)

        tag_name_input = QLineEdit()
        tag_name_input.setPlaceholderText("Enter tag name for model")
        tag_name_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ced4da;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                min-width: 400px;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border: 1px solid #007bff;
                box-shadow: 0 0 5px rgba(0, 123, 255, 0.5);
            }
        """)
        model_layout.addRow("Tag Name:", tag_name_input)

        channel_layout = QVBoxLayout()
        channel_layout.setSpacing(10)
        channel_inputs = []
        channel_container = QWidget()
        channel_container.setLayout(channel_layout)

        def add_channel_input():
            channel_widget = QWidget()
            channel_form = QFormLayout()
            channel_form.setSpacing(10)
            channel_form.setLabelAlignment(Qt.AlignRight)
            channel_form.setFormAlignment(Qt.AlignCenter)
            channel_widget.setLayout(channel_form)

            channel_name_input = QLineEdit()
            channel_name_input.setPlaceholderText("Enter channel name")
            channel_name_input.setStyleSheet("""
                QLineEdit {
                    border: 1px solid #ced4da;
                    border-radius: 8px;
                    padding: 12px;
                    font-size: 16px;
                    min-width: 400px;
                    background-color: #ffffff;
                }
                QLineEdit:focus {
                    border: 1px solid #007bff;
                    box-shadow: 0 0 5px rgba(0, 123, 255, 0.5);
                }
            """)
            channel_form.addRow("Channel Name:", channel_name_input)

            remove_channel_button = QPushButton("Remove Channel")
            remove_channel_button.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border-radius: 8px;
                    padding: 10px;
                    font-size: 14px;
                    font-weight: bold;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
                QPushButton:pressed {
                    background-color: #bd2130;
                }
            """)
            remove_channel_button.clicked.connect(lambda: remove_channel(channel_widget))
            channel_form.addRow("", remove_channel_button)

            channel_inputs.append((channel_widget, channel_name_input))
            channel_layout.addWidget(channel_widget)

        def remove_channel(channel_widget):
            if len(channel_inputs) > 1:
                for widget, _ in channel_inputs:
                    if widget == channel_widget:
                        channel_inputs.remove((widget, _))
                        widget.deleteLater()
                        break

        add_channel_button = QPushButton("Add Channel")
        add_channel_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        add_channel_button.clicked.connect(add_channel_input)
        model_layout.addRow("Channels:", channel_container)
        model_layout.addRow("", add_channel_button)

        remove_model_button = QPushButton("Remove Model")
        remove_model_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
        """)
        remove_model_button.clicked.connect(lambda: self.remove_model_input(model_widget))
        model_layout.addRow("", remove_model_button)

        add_channel_input()
        self.model_inputs.append((model_widget, model_name_input, tag_name_input, channel_inputs))
        self.model_layout.addWidget(model_widget)

    def remove_model_input(self, model_widget):
        if len(self.model_inputs) > 1:
            for widget, _, _, _ in self.model_inputs:
                if widget == model_widget:
                    self.model_inputs.remove((widget, _, _, _))
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