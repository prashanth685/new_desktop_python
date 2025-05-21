from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QTabWidget, QListWidget, QLineEdit, QLabel, QMessageBox, QListWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal

class ProjectStructureWidget(QWidget):
    project_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.db = parent.db  # Assumes parent has a database connection
        self.initUI()
        self.load_projects()

    def initUI(self):
        main_layout = QHBoxLayout(self)

        # Left Panel - Project Selection (15%)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)

        # Select Project Label
        left_layout.addWidget(QLabel("<h2>Select Project</h2>"))

        # Search Bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search Projects")
        self.search_bar.setStyleSheet("""
            QLineEdit {
                border: 2px solid #d3d3d3;
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
                background-color: #f0f0f0;
            }
        """)
        self.search_bar.textChanged.connect(self.filter_projects)
        left_layout.addWidget(self.search_bar)

        # Project List
        self.project_list = QListWidget()
        self.project_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #d3d3d3;
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
            }
            QListWidget::item:hover {
                background-color: #e0e0e0;
            }
        """)
        self.project_list.itemClicked.connect(self.on_project_selected)
        left_layout.addWidget(self.project_list)

        # Buttons
        button_layout = QVBoxLayout()
        self.open_button = QPushButton("Open")
        self.open_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """)
        self.open_button.clicked.connect(self.open_project)
        self.open_button.setEnabled(False)

        back_button = QPushButton("Back")
        back_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
        """)
        back_button.clicked.connect(self.back_to_select)

        button_layout.addWidget(self.open_button)
        button_layout.addWidget(back_button)
        left_layout.addLayout(button_layout)

        # Right Panel - Project Structure (85%)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)

        # Project Structure Label
        right_layout.addWidget(QLabel("<h2>Project Structure</h2>"))

        # Tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #d3d3d3;
                border-radius: 5px;
            }
            QTabBar::tab {
                padding: 8px 16px;
                font-size: 14px;
            }
            QTabBar::tab:selected {
                color: purple;
                border-bottom: 2px solid purple;
            }
        """)
        self.tab_widget.addTab(QWidget(), "Folder View")  # Placeholder
        self.tab_widget.addTab(self.create_tree_view(), "Tree View")

        right_layout.addWidget(self.tab_widget)

        # Add panels to main layout with stretch factors for 15%/85%
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        main_layout.setStretch(0, 15)  # 15% for left panel
        main_layout.setStretch(1, 85)  # 85% for right panel

    def create_tree_view(self):
        tree = QTreeWidget()
        tree.setHeaderHidden(True)
        tree.setStyleSheet("""
            QTreeWidget {
                background-color: white;
                border: 1px solid #d3d3d3;
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
            }
            QTreeWidget::item {
                padding: 3px;
            }
            QTreeWidget::item:hover {
                background-color: #e0e0e0;
            }
        """)
        tree.itemClicked.connect(self.on_structure_item_clicked)
        return tree

    def load_projects(self):
        try:
            projects = self.db.load_projects()
            self.project_list.clear()
            if not projects:
                QMessageBox.information(self, "Info", "No projects available.")
                return
            for project in projects:
                if not project or not isinstance(project, str):
                    continue
                item = QListWidgetItem(f"📁 {project}")
                item.setData(Qt.UserRole, project)
                self.project_list.addItem(item)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load projects: {str(e)}")

    def filter_projects(self, text):
        for index in range(self.project_list.count()):
            item = self.project_list.item(index)
            project_name = item.data(Qt.UserRole)
            item.setHidden(text.lower() not in project_name.lower())

    def on_project_selected(self, item):
        project_name = item.data(Qt.UserRole)
        self.selected_project = project_name
        self.open_button.setEnabled(True)
        self.load_project_structure(project_name)

    def load_project_structure(self, project_name):
        tree = self.tab_widget.widget(1)  # Tree View tab
        tree.clear()
        try:
            project_data = self.db.get_project_data(project_name)
            if not project_data or "models" not in project_data:
                QMessageBox.warning(self, "Error", f"No valid data for project: {project_name}")
                return

            models = project_data.get("models", [])
            if not models:
                tree.addTopLevelItem(QTreeWidgetItem(["No models available"]))
                return

            for model in models:
                model_name = model.get("name", "Unnamed Model")
                model_item = QTreeWidgetItem(tree, [f"📁 {model_name}"])
                channels = model.get("channels", [])
                if not channels:
                    QTreeWidgetItem(model_item, ["No channels available"])
                else:
                    for channel in channels:
                        channel_name = channel.get("channelName", "Unnamed Channel")
                        QTreeWidgetItem(model_item, [f"📄 {channel_name}"])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load project structure: {str(e)}")

    def open_project(self):
        if hasattr(self, 'selected_project') and self.selected_project:
            if self.selected_project in getattr(self.parent, 'open_dashboards', {}):
                self.parent.open_dashboards[self.selected_project].raise_()
                self.parent.open_dashboards[self.selected_project].activateWindow()
                return
            self.project_selected.emit(self.selected_project)
        else:
            QMessageBox.warning(self, "Error", "Please select a project to open!")

    def back_to_select(self):
        self.parent.display_select_project()

    def on_structure_item_clicked(self, item, column):
        item_text = item.text(0)
        QMessageBox.information(self, "Item Clicked", f"You clicked on: {item_text}")