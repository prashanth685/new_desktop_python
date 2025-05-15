import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QComboBox, QMessageBox, QApplication, QInputDialog, QDialog, QListWidget, QDialogButtonBox,
                             QLineEdit, QFormLayout, QSpinBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
import os
from dashboard.dashboard_window import DashboardWindow
from database import Database
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class CreateProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Project")
        self.setStyleSheet("background-color: #f5f7fa;")
        self.models = []
        self.initUI()

    def initUI(self):
        # Maximize the dialog
        self.showMaximized()

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(40, 40, 40, 40)
        self.setLayout(main_layout)

        # Card widget for content
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
        main_layout.addWidget(card_widget)

        # Title
        title_label = QLabel("Create New Project")
        title_label.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #343a40;
            margin-bottom: 20px;
        """)
        card_layout.addWidget(title_label, alignment=Qt.AlignCenter)

        # Project name
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

        # Model and channels section
        self.model_layout = QVBoxLayout()
        self.model_layout.setSpacing(15)
        self.model_inputs = []
        self.add_model_input()
        card_layout.addWidget(QLabel("Models and Channels:"))
        card_layout.addLayout(self.model_layout)

        # Add model button
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

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setStyleSheet("""
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
            QPushButton:cancel {
                background-color: #6c757d;
            }
            QPushButton:cancel:hover {
                background-color: #5a6268;
            }
            QPushButton:cancel:pressed {
                background-color: #4b5359;
            }
        """)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        card_layout.addWidget(buttons, alignment=Qt.AlignCenter)

    def add_model_input(self):
        model_widget = QWidget()
        model_widget.setStyleSheet("background-color: #f8f9fa; border-radius: 10px; padding: 15px;")
        model_layout = QFormLayout()
        model_layout.setSpacing(10)
        model_layout.setLabelAlignment(Qt.AlignRight)
        model_layout.setFormAlignment(Qt.AlignCenter)
        model_widget.setLayout(model_layout)

        # Model name input
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

        # Tag name input
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

        # Channel inputs
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

        add_channel_input()  # Add initial channel input
        self.model_inputs.append((model_widget, model_name_input, tag_name_input, channel_inputs))
        self.model_layout.addWidget(model_widget)

    def remove_model_input(self, model_widget):
        if len(self.model_inputs) > 1:
            for widget, _, _, _ in self.model_inputs:
                if widget == model_widget:
                    self.model_inputs.remove((widget, _, _, _))
                    widget.deleteLater()
                    break

    def accept(self):
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

        super().accept()

class ProjectSelectionDialog(QDialog):
    def __init__(self, projects, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Existing Project")
        self.setStyleSheet("background-color: #ffffff;")
        self.selected_project = None
        
        layout = QVBoxLayout()
        
        # Project list
        self.project_list = QListWidget()
        self.project_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ced4da;
                border-radius: 8px;
                padding: 10px;
                font-size: 16px;
                background-color: #f8f9fa;
                min-width: 300px;
                min-height: 200px;
            }
            QListWidget::item:selected {
                background-color: #007bff;
                color: white;
            }
        """)
        for project in projects:
            self.project_list.addItem(project)
        self.project_list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.project_list)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border-radius: 8px;
                padding: 10px;
                font-size: 16px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:cancel {
                background-color: #6c757d;
            }
            QPushButton:cancel:hover {
                background-color: #5a6268;
            }
        """)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        self.setMinimumSize(400, 300)
        
    def accept(self):
        selected_items = self.project_list.selectedItems()
        if selected_items:
            self.selected_project = selected_items[0].text()
        super().accept()

class ProjectSelectionWindow(QWidget):
    def __init__(self, db, email, auth_window):
        super().__init__()
        self.db = db
        self.email = email
        self.auth_window = auth_window
        self.open_dashboards = {}  # Track open dashboard windows by project name
        self.initUI()
        self.load_projects()

    def initUI(self):
        self.setWindowTitle('Project Selection - Sarayu Infotech Solutions')
        self.showMaximized()
        self.setStyleSheet("background-color: #e9ecef;")  # Light gray background

        # Main layout for the window
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)
        self.setLayout(main_layout)

        # Card widget to hold the content
        card_widget = QWidget()
        card_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 15px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                padding: 20px;
                max-height: 600px;
            }
        """)
        card_layout = QVBoxLayout()
        card_widget.setLayout(card_layout)

        # Logo
        logo_label = QLabel(self)
        logo_path = "logo.png" if os.path.exists("logo.png") else "icons/placeholder.png"
        pixmap = QPixmap(logo_path)
        if pixmap.isNull():
            logging.warning(f"Could not load logo at {logo_path}")
            pixmap = QPixmap("icons/placeholder.png")
        logo_label.setPixmap(pixmap.scaled(150, 150, Qt.KeepAspectRatio))
        logo_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(logo_label)

        # Title
        title_label = QLabel('Select a Project')
        title_label.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #343a40;
            margin: 15px 0;
        """)
        card_layout.addWidget(title_label, alignment=Qt.AlignCenter)

        # Project combo box
        self.project_combo = QComboBox()
        self.project_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #ced4da;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                background-color: #f8f9fa;
                min-width: 300px;
            }
            QComboBox:hover {
                border: 1px solid #007bff;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url(icons/down_arrow.png);  /* Add a custom arrow icon if available */
                width: 12px;
                height: 12px;
            }
        """)
        self.project_combo.addItem("Select a project...")
        card_layout.addWidget(self.project_combo, alignment=Qt.AlignCenter)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)

        # Create Project button
        create_button = QPushButton('Create Project')
        create_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #218838;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            }
        """)
        create_button.clicked.connect(self.create_project)
        button_layout.addWidget(create_button)

        # Open Project button
        open_button = QPushButton('Open Project')
        open_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #0056b3;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            }
        """)
        open_button.clicked.connect(self.open_project)
        button_layout.addWidget(open_button)

        # Open Existing Project button
        existing_button = QPushButton('Open Existing Project')
        existing_button.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #138496;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            }
        """)
        existing_button.clicked.connect(self.open_existing_project)
        button_layout.addWidget(existing_button)

        # Back to Login button
        back_button = QPushButton('Back to Login')
        back_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #5a6268;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            }
        """)
        back_button.clicked.connect(self.back_to_login)
        button_layout.addWidget(back_button)

        card_layout.addLayout(button_layout)
        main_layout.addWidget(card_widget)

    def load_projects(self):
        """Load projects from the database into the combo box."""
        try:
            if not self.db.is_connected():
                self.db.reconnect()
            self.project_combo.clear()
            self.project_combo.addItem("Select a project...")
            projects = self.db.load_projects()
            for project_name in projects:
                self.project_combo.addItem(project_name)
            logging.info(f"Loaded projects into combo box: {projects}")
            if not projects:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("No Projects")
                msg_box.setText("No projects found. Please create a new project.")
                msg_box.setStyleSheet("""
                    background-color: #ffffff;
                    font: 12pt 'Arial';
                    QLabel {
                        color: #343a40;
                    }
                    QPushButton {
                        background-color: #007bff;
                        color: white;
                        border-radius: 5px;
                        padding: 8px;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        background-color: #0056b3;
                    }
                """)
                msg_box.exec_()
        except Exception as e:
            logging.error(f"Error loading projects: {str(e)}")
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Failed to load projects: {str(e)}")
            msg_box.setStyleSheet("""
                background-color: #ffffff;
                font: 12pt 'Arial';
                QLabel {
                    color: #343a40;
                }
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border-radius: 5px;
                    padding: 8px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            msg_box.exec_()

    def create_project(self):
        """Create a new project with models and channels."""
        try:
            dialog = CreateProjectDialog(self)
            if dialog.exec_():
                project_name = dialog.project_name_input.text().strip()
                models = dialog.models
                # Prepare models without tag_name for database storage
                models_for_db = [{"name": model["name"], "channels": model["channels"]} for model in models]
                success, message = self.db.create_project(project_name, models_for_db)
                if success:
                    # Add the tag for each model
                    for model in models:
                        tag_data = {"tag_name": model["tag_name"]}
                        self.db.add_tag(project_name, model["name"], tag_data)
                    self.load_projects()
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle("Success")
                    msg_box.setText(message)
                    msg_box.setStyleSheet("""
                        background-color: #ffffff;
                        font: 12pt 'Arial';
                        QLabel {
                            color: #343a40;
                        }
                        QPushButton {
                            background-color: #007bff;
                            color: white;
                            border-radius: 5px;
                            padding: 8px;
                            min-width: 80px;
                        }
                        QPushButton:hover {
                            background-color: #0056b3;
                        }
                    """)
                    msg_box.exec_()
                    logging.info(f"Created new project: {project_name} with {len(models)} models")
                    self.project_combo.setCurrentText(project_name)
                else:
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle("Error")
                    msg_box.setText(message)
                    msg_box.setStyleSheet("""
                        background-color: #ffffff;
                        font: 12pt 'Arial';
                        QLabel {
                            color: #343a40;
                        }
                        QPushButton {
                            background-color: #dc3545;
                            color: white;
                            border-radius: 5px;
                            padding: 8px;
                            min-width: 80px;
                        }
                        QPushButton:hover {
                            background-color: #c82333;
                        }
                    """)
                    msg_box.exec_()
        except Exception as e:
            logging.error(f"Error creating project: {str(e)}")
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Failed to create project: {str(e)}")
            msg_box.setStyleSheet("""
                background-color: #ffffff;
                font: 12pt 'Arial';
                QLabel {
                    color: #343a40;
                }
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border-radius: 5px;
                    padding: 8px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            msg_box.exec_()

    def open_project(self):
        """Open the selected project in a new DashboardWindow."""
        project_name = self.project_combo.currentText()
        if project_name == "Select a project..." or not project_name:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText("Please select a project to open!")
            msg_box.setStyleSheet("""
                background-color: #ffffff;
                font: 12pt 'Arial';
                QLabel {
                    color: #343a40;
                }
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border-radius: 5px;
                    padding: 8px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            msg_box.exec_()
            return
        if project_name not in self.db.load_projects():
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Project '{project_name}' not found!")
            msg_box.setStyleSheet("""
                background-color: #ffffff;
                font: 12pt 'Arial';
                QLabel {
                    color: #343a40;
                }
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border-radius: 5px;
                    padding: 8px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            msg_box.exec_()
            self.load_projects()
            return
        try:
            if project_name in self.open_dashboards and self.open_dashboards[project_name].isVisible():
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Info")
                msg_box.setText(f"Project '{project_name}' is already open!")
                msg_box.setStyleSheet("""
                    background-color: #ffffff;
                    font: 12pt 'Arial';
                    QLabel {
                        color: #343a40;
                    }
                    QPushButton {
                        background-color: #007bff;
                        color: white;
                        border-radius: 5px;
                        padding: 8px;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        background-color: #0056b3;
                    }
                """)
                msg_box.exec_()
                self.open_dashboards[project_name].raise_()
                self.open_dashboards[project_name].activateWindow()
                return

            logging.info(f"Opening project: {project_name}")
            dashboard = DashboardWindow(self.db, self.email, project_name, self)
            dashboard.show()
            self.open_dashboards[project_name] = dashboard
        except Exception as e:
            logging.error(f"Error opening Dashboard for project {project_name}: {str(e)}")
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Failed to open dashboard: {str(e)}")
            msg_box.setStyleSheet("""
                background-color: #ffffff;
                font: 12pt 'Arial';
                QLabel {
                    color: #343a40;
                }
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border-radius: 5px;
                    padding: 8px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            msg_box.exec_()

    def open_existing_project(self):
        """Open a dialog to select and open an existing project."""
        try:
            projects = self.db.load_projects()
            if not projects:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("No Projects")
                msg_box.setText("No projects available to open!")
                msg_box.setStyleSheet("""
                    background-color: #ffffff;
                    font: 12pt 'Arial';
                    QLabel {
                        color: #343a40;
                    }
                    QPushButton {
                        background-color: #dc3545;
                        color: white;
                        border-radius: 5px;
                        padding: 8px;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        background-color: #c82333;
                    }
                """)
                msg_box.exec_()
                return
                
            dialog = ProjectSelectionDialog(projects, self)
            if dialog.exec_() and dialog.selected_project:
                project_name = dialog.selected_project
                if project_name in self.open_dashboards and self.open_dashboards[project_name].isVisible():
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle("Info")
                    msg_box.setText(f"Project '{project_name}' is already open!")
                    msg_box.setStyleSheet("""
                        background-color: #ffffff;
                        font: 12pt 'Arial';
                        QLabel {
                            color: #343a40;
                        }
                        QPushButton {
                            background-color: #007bff;
                            color: white;
                            border-radius: 5px;
                            padding: 8px;
                            min-width: 80px;
                        }
                        QPushButton:hover {
                            background-color: #0056b3;
                        }
                    """)
                    msg_box.exec_()
                    self.open_dashboards[project_name].raise_()
                    self.open_dashboards[project_name].activateWindow()
                    return

                logging.info(f"Opening existing project: {project_name}")
                dashboard = DashboardWindow(self.db, self.email, project_name, self)
                dashboard.show()
                self.open_dashboards[project_name] = dashboard
                self.project_combo.setCurrentText(project_name)
        except Exception as e:
            logging.error(f"Error opening existing project: {str(e)}")
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Failed to open project: {str(e)}")
            msg_box.setStyleSheet("""
                background-color: #ffffff;
                font: 12pt 'Arial';
                QLabel {
                    color: #343a40;
                }
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border-radius: 5px;
                    padding: 8px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            msg_box.exec_()

    def back_to_login(self):
        """Return to the login window."""
        try:
            self.auth_window.show()
            self.auth_window.showMaximized()
            self.close()
        except Exception as e:
            logging.error(f"Error returning to login: {str(e)}")
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Failed to return to login: {str(e)}")
            msg_box.setStyleSheet("""
                background-color: #ffffff;
                font: 12pt 'Arial';
                QLabel {
                    color: #343a40;
                }
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border-radius: 5px;
                    padding: 8px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            msg_box.exec_()

    def closeEvent(self, event):
        """Handle window close event."""
        try:
            for dashboard in self.open_dashboards.values():
                if dashboard.isVisible():
                    dashboard.close()
            if self.db.is_connected():
                self.db.close_connection()
        except Exception as e:
            logging.error(f"Error closing database connection: {str(e)}")
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    db = Database(email="user@example.com")
    window = ProjectSelectionWindow(db, "user@example.com", None)
    window.show()
    sys.exit(app.exec_())