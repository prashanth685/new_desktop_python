from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton, QHBoxLayout, QMessageBox
from PyQt5.QtCore import Qt, pyqtSignal
import logging

# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class ProjectStructureWidget(QWidget):
    project_selected = pyqtSignal(str)  # Signal to emit when a project is selected to open

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.db = parent.db
        self.initUI()
        self.load_projects()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(layout)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #f8f9fa;
                border: 1px solid #ced4da;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }
            QTreeWidget::item {
                padding: 5px;
            }
            QTreeWidget::item:hover {
                background-color: #e9ecef;
            }
        """)
        self.tree.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.tree)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.open_button = QPushButton("Open")
        self.open_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        self.open_button.clicked.connect(self.open_project)
        self.open_button.setEnabled(False)  # Disabled until a project is selected
        button_layout.addWidget(self.open_button)

        back_button = QPushButton("Back")
        back_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                min-width: 100px;
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

        layout.addLayout(button_layout)

    def load_projects(self):
        try:
            projects = self.db.load_projects()
            self.tree.clear()
            for project in projects:
                project_item = QTreeWidgetItem(self.tree, [f"📁 {project}"])
                project_item.setData(0, Qt.UserRole, project)  # Store project name in UserRole
                # Add a dummy child to make the item expandable
                QTreeWidgetItem(project_item, ["Loading..."])
            if not projects:
                QMessageBox.information(self, "Info", "No projects available.")
        except Exception as e:
            logging.error(f"Error loading projects: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to load projects: {str(e)}")

    def on_item_clicked(self, item, column):
        # Check if the clicked item is a project (top-level item)
        if item.parent() is None:  # Top-level item (project)
            project_name = item.data(0, Qt.UserRole)
            if item.childCount() == 1 and item.child(0).text(0) == "Loading...":
                # Remove the dummy "Loading..." child
                item.takeChild(0)
                # Load the project structure
                try:
                    project_data = self.db.get_project_data(project_name)
                    models = project_data.get("models", [])
                    for model in models:
                        model_name = model.get("name", "Unnamed Model")
                        model_item = QTreeWidgetItem(item, [f"📁 {model_name}"])
                        channels = model.get("channels", [])
                        for channel in channels:
                            channel_name = channel.get("channel_name", "Unnamed Channel")
                            QTreeWidgetItem(model_item, [f"📄 {channel_name}"])
                    item.setExpanded(True)
                except Exception as e:
                    logging.error(f"Error loading project structure for {project_name}: {str(e)}")
                    QMessageBox.warning(self, "Error", f"Failed to load project structure: {str(e)}")
            # Enable the Open button and store the selected project
            self.selected_project = project_name
            self.open_button.setEnabled(True)
        else:
            # If a child item (model or channel) is clicked, find the parent project
            parent_item = item
            while parent_item.parent() is not None:
                parent_item = parent_item.parent()
            project_name = parent_item.data(0, Qt.UserRole)
            self.selected_project = project_name
            self.open_button.setEnabled(True)

    def open_project(self):
        if hasattr(self, 'selected_project') and self.selected_project:
            if self.selected_project in self.parent.open_dashboards:
                self.parent.open_dashboards[self.selected_project].raise_()
                self.parent.open_dashboards[self.selected_project].activateWindow()
                return
            self.project_selected.emit(self.selected_project)
        else:
            QMessageBox.warning(self, "Error", "Please select a project to open!")

    def back_to_select(self):
        self.parent.display_select_project()