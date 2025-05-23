from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QTabWidget, QListWidget, QLineEdit, QLabel, QMessageBox, QListWidgetItem, QProgressDialog
)
from PyQt5 import QtCore

from PyQt5.QtCore import Qt, pyqtSignal, QThread, pyqtSignal as Signal, QTimer
import json
import logging
import time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class DatabaseWorker(QThread):
    data_fetched = Signal(str, dict)

    def __init__(self, db, project_name):
        super().__init__()
        self.db = db
        self.project_name = project_name

    def run(self):
        try:
            project_data = self.db.get_project_data(self.project_name)
            self.data_fetched.emit(self.project_name, project_data)
        except Exception as e:
            logging.error(f"Async fetch failed for '{self.project_name}': {str(e)}")

class ProjectStructureWidget(QWidget):
    project_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.db = parent.db
        self.selected_project = None
        self.project_cache = {}
        self.initUI()
        self.load_projects()

    def initUI(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Left Panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.addWidget(QLabel('<h2 style="color: white;">Select Project</h2>'))

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search Projects")
        self.search_bar.setStyleSheet("QLineEdit { border: 2px solid #d3d3d3; border-radius: 5px; padding: 8px; font-size: 14px; background-color: #f0f0f0; }")
        self.search_bar.textChanged.connect(self.filter_projects)
        left_layout.addWidget(self.search_bar)

        self.project_list = QListWidget()
        self.project_list.setStyleSheet("QListWidget { background-color: white; border: 1px solid #d3d3d3; border-radius: 5px; padding: 5px; font-size: 14px; } QListWidget::item:hover { background-color: #e0e0e0; }")
        self.project_list.itemClicked.connect(self.on_project_selected)
        left_layout.addWidget(self.project_list)

        button_layout = QVBoxLayout()
        self.open_button = QPushButton("Open")
        self.open_button.setStyleSheet("QPushButton { background-color: #007bff; color: white; border-radius: 5px; padding: 10px; font-size: 14px; font-weight: bold; } QPushButton:hover { background-color: #0056b3; } QPushButton:pressed { background-color: #004085; }")
        self.open_button.clicked.connect(self.open_project)
        self.open_button.setEnabled(False)
        back_button = QPushButton("Back")
        back_button.setStyleSheet("QPushButton { background-color: #dc3545; color: white; border-radius: 5px; padding: 10px; font-size: 14px; font-weight: bold; } QPushButton:hover { background-color: #c82333; } QPushButton:pressed { background-color: #bd2130; }")
        back_button.clicked.connect(self.back_to_select)
        button_layout.addWidget(self.open_button)
        button_layout.addWidget(back_button)
        left_layout.addLayout(button_layout)

        # Right Panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.addWidget(QLabel('<h2 style="color: white;">Project Structure</h2>'))

        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("QTabWidget::pane { border: 1px solid #d3d3d3; border-radius: 5px; } QTabBar::tab { padding: 8px 16px; font-size: 14px; } QTabBar::tab:selected { color: white; border-bottom: white; }")
        self.tree_view = self.create_tree_view()
        self.tab_widget.addTab(self.tree_view, "Tree View")
        right_layout.addWidget(self.tab_widget)

        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        main_layout.setStretch(0, 15)
        main_layout.setStretch(1, 85)

    def create_tree_view(self):
        tree = QTreeWidget()
        tree.setHeaderHidden(True)
        tree.setStyleSheet("QTreeWidget { background-color: white; border: 1px solid #d3d3d3; border-radius: 5px; padding: 5px; font-size: 14px; } QTreeWidget::item { padding: 3px; } QTreeWidget::item:hover { background-color: #e0e0e0; }")
        tree.itemClicked.connect(self.on_structure_item_clicked)
        tree.itemExpanded.connect(self.on_structure_item_expanded)
        return tree

    def load_projects(self):
        try:
            projects = self.db.load_projects()
            self.project_list.clear()
            self.project_cache.clear()
            if not projects:
                logging.info("No projects available.")
                QMessageBox.information(self, "Info", "No projects available.")
                return
            for project in projects:
                if not project or not isinstance(project, str):
                    logging.warning(f"Invalid project name: {project}")
                    continue
                item = QListWidgetItem(f"📁 {project}")
                item.setSizeHint(QtCore.QSize(100, 40))  # Width can be left flexible, height = 40px
                self.project_list.addItem(item)
                item.setData(Qt.UserRole, project)
                self.project_list.addItem(item)
                try:
                    project_data = self.db.get_project_data(project)
                    self.project_cache[project] = project_data
                except Exception as e:
                    logging.error(f"Failed to preload project data for '{project}': {str(e)}")
            logging.debug(f"Loaded {self.project_list.count()} projects")
        except Exception as e:
            logging.error(f"Failed to load projects: {str(e)}")
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
        logging.debug(f"Selected project: {project_name}")
        self.load_project_structure(project_name)

    def load_project_structure(self, project_name):
        start_time = time.time()
        self.tree_view.clear()
        if project_name in self.project_cache:
            self.populate_tree_view(project_name, self.project_cache[project_name])
            logging.debug(f"Cache hit for '{project_name}', loaded in {time.time() - start_time:.2f} seconds")
            return
        worker = DatabaseWorker(self.db, project_name)
        worker.data_fetched.connect(self.populate_tree_view)
        worker.start()

    def populate_tree_view(self, project_name, project_data):
        self.tree_view.blockSignals(True)
        try:
            if not isinstance(project_data, dict):
                raise TypeError(f"Expected dict, got {type(project_data)}")
            self.project_cache[project_name] = project_data
            models = project_data.get("models", {})
            if not models:
                self.tree_view.addTopLevelItem(QTreeWidgetItem(["No models available"]))
                return

            self.tree_view.clear()
            for model_name, model_data in models.items():
                if not isinstance(model_data, dict):
                    logging.warning(f"Invalid model data for '{model_name}'")
                    continue

                model_display_name = model_data.get("name", model_name) or "Unnamed Model"
                model_item = QTreeWidgetItem([f"📁 {model_display_name}"])
                self.tree_view.addTopLevelItem(model_item)

                channels = model_data.get("channels", [])
                for channel in channels:
                    if not isinstance(channel, dict):
                        continue
                    channel_name = channel.get("channelName", channel.get("channel_name", "Unnamed Channel"))
                    QTreeWidgetItem(model_item, [f"📄 {channel_name}"])

                # Explicitly expand this item
                self.tree_view.expandItem(model_item)

        except Exception as e:
            logging.error(f"Failed to populate tree for '{project_name}': {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to load project structure: {str(e)}")
        finally:
            self.tree_view.blockSignals(False)


    def on_structure_item_expanded(self, item):
        if not item.data(0, Qt.UserRole).get("loaded", False):
            channels = item.data(0, Qt.UserRole).get("channels", [])
            for channel in channels:
                if not isinstance(channel, dict):
                    continue
                channel_name = channel.get("channelName", channel.get("channel_name", "Unnamed Channel"))
                QTreeWidgetItem(item, [f"📄 {channel_name}"])
            item.setData(0, Qt.UserRole, {**item.data(0, Qt.UserRole), "loaded": True})

    def on_structure_item_clicked(self, item, column):
        model_data = item.data(0, Qt.UserRole)
        item_text = item.text(0)
        logging.debug(f"Tree view item clicked: {item_text}")
        if model_data and isinstance(model_data, dict) and "channels" in model_data:
            QMessageBox.information(self, "Model Selected", f"Selected model: {item_text}")

    def open_project(self):
        if not self.selected_project:
            logging.warning("No project selected")
            QMessageBox.warning(self, "Error", "Please select a project to open!")
            return
        progress = QProgressDialog(f"Opening {self.selected_project}...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        QTimer.singleShot(0, lambda: self._open_project_with_progress(progress))

    def _open_project_with_progress(self, progress):
        try:
            self.open_button.setEnabled(False)
            open_dashboards = getattr(self.parent, 'open_dashboards', {})
            if self.selected_project in open_dashboards:
                dashboard = open_dashboards[self.selected_project]
                dashboard.raise_()
                dashboard.activateWindow()
            else:
                self.project_selected.emit(self.selected_project)
        finally:
            progress.close()
            self.open_button.setEnabled(True)

    def back_to_select(self):
        logging.debug("Back button clicked, displaying select project")
        self.parent.display_select_project()