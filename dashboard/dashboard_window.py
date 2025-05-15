import sys
import gc
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSplitter, QSizePolicy, QApplication, QMdiSubWindow, QMessageBox, QInputDialog
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QColor
import logging
import uuid
from dashboard.components.file_bar import FileBar
from dashboard.components.tool_bar import ToolBar
from dashboard.components.sub_tool_bar import SubToolBar
from dashboard.components.main_section import MainSection
from dashboard.components.tree_view import TreeView
from dashboard.components.console import Console
from dashboard.components.mqtt_status import MQTTStatus
from mqtthandler import MQTTHandler
from features.create_tags import CreateTagsFeature
from features.tabular_view import TabularViewFeature
from features.time_view import TimeViewFeature
from features.fft_view import FFTViewFeature
from features.waterfall import WaterfallFeature
from features.orbit import OrbitFeature
from features.trend_view import TrendViewFeature
from features.multi_trend import MultiTrendFeature
from features.bode_plot import BodePlotFeature
from features.history_plot import HistoryPlotFeature
from features.time_report import TimeReportFeature
from features.report import ReportFeature

class DashboardWindow(QWidget):
    def __init__(self, db, email, project_name, project_selection_window):
        super().__init__()
        self.db = db
        self.email = email
        self.current_project = project_name
        self.project_selection_window = project_selection_window
        self.current_feature = None
        self.mqtt_handler = None
        self.feature_instances = {}
        self.sub_windows = {}
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.is_saving = False
        self.mqtt_connected = False
        self.current_layout = (2, 2)

        self.initUI()
        QTimer.singleShot(0, self.deferred_initialization)

    def initUI(self):
        self.setWindowTitle(f'Sarayu Desktop Application - {self.current_project.upper()}')
        self.setWindowState(Qt.WindowMaximized)

        app = QApplication.instance()
        app.setStyleSheet("""
            QInputDialog, QMessageBox {
                background-color: #1e2937;
                color: white;
                font-size: 16px;
                border: 1px solid #2c3e50;
                border-radius: 8px;
                padding: 15px;
                width:500px;
            }
            QInputDialog QLineEdit {
                background-color: #2c3e50;
                color: white;
                border: 1px solid #4a90e2;
                padding: 8px;
                border-radius: 4px;
                font-size: 15px;
            }
            QInputDialog QLabel,
            QMessageBox QLabel {
                color: #ecf0f1;
                font-size: 16px;
                padding-bottom: 10px;
            }
            QInputDialog QPushButton,
            QMessageBox QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-size: 15px;
                min-width: 80px;
                transition: background-color 0.2s ease;
            }
            QInputDialog QPushButton:hover,
            QMessageBox QPushButton:hover {
                background-color: #357abd;
            }
            QInputDialog QPushButton:pressed,
            QMessageBox QPushButton:pressed {
                background-color: #2c5d9b;
            }
            QMdiSubWindow {
                background-color: #263238;
                border: 1px solid #4a90e2;
                border-radius: 4px;
            }
            QMdiSubWindow > QWidget {
                background-color: #263238;
                color: #ecf0f1;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)

        self.file_bar = FileBar(self)
        main_layout.addWidget(self.file_bar)

        self.tool_bar = ToolBar(self)
        main_layout.addWidget(self.tool_bar)

        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setContentsMargins(0, 0, 0, 0)
        main_splitter.setHandleWidth(1)
        main_splitter.setStyleSheet("QSplitter::handle { background-color: #2c3e50; }")
        main_layout.addWidget(main_splitter)

        self.tree_view = TreeView(self)
        main_splitter.addWidget(self.tree_view)

        right_container = QWidget()
        right_container.setStyleSheet("background-color: #263238;")
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_container.setLayout(right_layout)

        self.sub_tool_bar = SubToolBar(self)
        right_layout.addWidget(self.sub_tool_bar)

        self.main_section = MainSection(self)
        right_layout.addWidget(self.main_section, 1)

        main_splitter.addWidget(right_container)
        main_splitter.setSizes([250, 950])

        self.console = Console(self)
        self.mqtt_status = MQTTStatus(self)
        self.console_layout = QVBoxLayout()
        self.console_layout.setContentsMargins(0, 0, 0, 0)
        self.console_layout.setSpacing(0)
        console_container = QWidget()
        console_container.setLayout(self.console_layout)
        self.console_layout.addWidget(self.console.button_container)
        self.console_layout.addWidget(self.console.console_message_area)
        self.console_layout.addWidget(self.mqtt_status)
        main_layout.addWidget(console_container, 0)

    def deferred_initialization(self):
        self.load_project_features()
        self.setup_mqtt()
        self.display_feature_content("Create Tags", self.current_project)

    def setup_mqtt(self):
        if not self.current_project:
            logging.warning("No project selected for MQTT setup")
            return
        self.cleanup_mqtt()
        try:
            tags = self.get_project_tags()
            if tags:
                self.mqtt_handler = MQTTHandler(self.db, self.current_project)
                self.mqtt_handler.data_received.connect(self.on_data_received)
                self.mqtt_handler.connection_status.connect(self.on_mqtt_status)
                self.mqtt_handler.start()
                self.mqtt_connected = True
                logging.info(f"MQTT setup for project: {self.current_project}")
                self.console.append_to_console(f"MQTT setup for project: {self.current_project}")
            else:
                logging.warning(f"No tags found for project: {self.current_project}")
                self.mqtt_connected = False
        except Exception as e:
            logging.error(f"Failed to setup MQTT: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to setup MQTT: {str(e)}")
            self.console.append_to_console(f"Failed to setup MQTT: {str(e)}")
        self.sub_tool_bar.update_subtoolbar()
        self.mqtt_status.update_mqtt_status_indicator()

    def cleanup_mqtt(self):
        if self.mqtt_handler:
            try:
                self.mqtt_handler.data_received.disconnect()
                self.mqtt_handler.connection_status.disconnect()
                self.mqtt_handler.stop()
                self.mqtt_handler.deleteLater()
                logging.info("Previous MQTT handler stopped")
            except Exception as e:
                logging.error(f"Error stopping MQTT handler: {str(e)}")
            finally:
                self.mqtt_handler = None
                self.mqtt_connected = False

    def get_project_tags(self):
        try:
            if not self.db.is_connected():
                self.db.reconnect()
            tags = list(self.db.tags_collection.find({"project_name": self.current_project}))
            return [tag["tag_name"] for tag in tags]
        except Exception as e:
            logging.error(f"Failed to retrieve project tags: {str(e)}")
            return []

    def connect_mqtt(self):
        if self.mqtt_connected:
            self.console.append_to_console("Already connected to MQTT")
            return
        try:
            tags = self.get_project_tags()
            if not tags:
                QMessageBox.warning(self, "Error", "No tags found for this project. Please create tags first!")
                self.console.append_to_console("No tags found for project")
                return
            self.cleanup_mqtt()
            self.mqtt_handler = MQTTHandler(self.db, self.current_project)
            self.mqtt_handler.data_received.connect(self.on_data_received)
            self.mqtt_handler.connection_status.connect(self.on_mqtt_status)
            self.mqtt_handler.start()
            self.mqtt_connected = True
            self.sub_tool_bar.update_subtoolbar()
            self.mqtt_status.update_mqtt_status_indicator()
            logging.info(f"MQTT connected for project: {self.current_project}")
            self.console.append_to_console(f"MQTT connected for project: {self.current_project}")
        except Exception as e:
            logging.error(f"Failed to connect MQTT: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to connect MQTT: {str(e)}")
            self.console.append_to_console(f"Failed to connect MQTT: {str(e)}")
            self.mqtt_connected = False
            self.mqtt_status.update_mqtt_status_indicator()

    def disconnect_mqtt(self):
        if not self.mqtt_connected:
            self.console.append_to_console("Already disconnected from MQTT")
            return
        try:
            self.cleanup_mqtt()
            self.sub_tool_bar.update_subtoolbar()
            self.mqtt_status.update_mqtt_status_indicator()
            logging.info(f"MQTT disconnected for project: {self.current_project}")
            self.console.append_to_console(f"MQTT disconnected for project: {self.current_project}")
        except Exception as e:
            logging.error(f"Failed to disconnect MQTT: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to disconnect MQTT: {str(e)}")
            self.console.append_to_console(f"Failed to disconnect MQTT: {str(e)}")
            self.mqtt_status.update_mqtt_status_indicator()

    def on_data_received(self, tag_name, values):
        if self.current_feature and self.current_project:
            feature_instance = self.feature_instances.get(self.current_feature)
            if feature_instance and hasattr(feature_instance, 'on_data_received'):
                try:
                    feature_instance.on_data_received(tag_name, values)
                except Exception as e:
                    logging.error(f"Error in on_data_received for {self.current_feature}: {str(e)}")

    def on_mqtt_status(self, message):
        self.mqtt_connected = "Connected" in message
        self.console.append_to_console(f"MQTT Status: {message}")
        self.mqtt_status.update_mqtt_status_indicator()
        self.sub_tool_bar.update_subtoolbar()

    def load_project_features(self):
        try:
            if not self.db.is_connected():
                self.db.reconnect()
            self.tree_view.tree.clear()
            self.tree_view.add_project_to_tree(self.current_project)
            for i in range(self.tree_view.tree.topLevelItemCount()):
                item = self.tree_view.tree.topLevelItem(i)
                if item.text(0) == f"📁 {self.current_project}":
                    item.setExpanded(True)
                    self.tree_view.tree.setCurrentItem(item)
                    self.tree_view.tree.scrollToItem(item)
                    break
        except Exception as e:
            logging.error(f"Failed to load project features: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to load project features: {str(e)}")

    def open_project(self):
        try:
            if not self.db.is_connected():
                self.db.reconnect()
            projects = self.db.load_projects()
            if not projects:
                QMessageBox.warning(self, "Error", "No projects available to open!")
                return
            project_name, ok = QInputDialog.getItem(self, "Open Project", "Select project:", projects, 0, False)
            if ok and project_name:
                if project_name in self.project_selection_window.open_dashboards:
                    self.project_selection_window.open_dashboards[project_name].raise_()
                    self.project_selection_window.open_dashboards[project_name].activateWindow()
                    return
                dashboard = DashboardWindow(self.db, self.email, project_name, self.project_selection_window)
                dashboard.show()
                self.project_selection_window.open_dashboards[project_name] = dashboard
                self.project_selection_window.load_projects()
                QMessageBox.information(self, "Success", f"Opened project: {project_name}")
                self.file_bar.update_file_bar()
        except Exception as e:
            logging.error(f"Error opening project: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error opening project: {str(e)}")

    def create_project(self):
        project_name, ok = QInputDialog.getText(self, "Create Project", "Enter project name:")
        if ok and project_name:
            try:
                if not self.db.is_connected():
                    self.db.reconnect()
                success, message = self.db.create_project(project_name)
                if success:
                    dashboard = DashboardWindow(self.db, self.email, project_name, self.project_selection_window)
                    dashboard.show()
                    self.project_selection_window.open_dashboards[project_name] = dashboard
                    self.project_selection_window.load_projects()
                    self.sub_tool_bar.update_subtoolbar()
                    QMessageBox.information(self, "Success", message)
                    self.file_bar.update_file_bar()
                else:
                    QMessageBox.warning(self, "Error", message)
            except Exception as e:
                logging.error(f"Error creating project: {str(e)}")
                QMessageBox.warning(self, "Error", f"Error creating project: {str(e)}")

    def edit_project_dialog(self):
        old_project_name = self.current_project
        new_project_name, ok = QInputDialog.getText(self, "Edit Project", "Enter new project name:", text=old_project_name)
        if not ok or not new_project_name or new_project_name == old_project_name:
            return
        try:
            if not self.db.is_connected():
                self.db.reconnect()
            success, message = self.db.edit_project(old_project_name, new_project_name)
            if success:
                self.current_project = new_project_name
                self.setWindowTitle(f'Sarayu Desktop Application - {self.current_project.upper()}')
                self.load_project_features()
                self.setup_mqtt()
                self.tool_bar.update_toolbar()
                self.sub_tool_bar.update_subtoolbar()
                if self.current_feature:
                    self.display_feature_content(self.current_feature, self.current_project)
                else:
                    self.display_feature_content("Create Tags", self.current_project)
                if old_project_name in self.project_selection_window.open_dashboards:
                    self.project_selection_window.open_dashboards[new_project_name] = self.project_selection_window.open_dashboards.pop(old_project_name)
                self.project_selection_window.load_projects()
                QMessageBox.information(self, "Success", message)
                self.file_bar.update_file_bar()
            else:
                QMessageBox.warning(self, "Error", message)
        except Exception as e:
            logging.error(f"Error editing project: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error editing project: {str(e)}")

    def delete_project(self):
        reply = QMessageBox.question(self, "Confirm Delete", f"Are you sure you want to delete {self.current_project}?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                if not self.db.is_connected():
                    self.db.reconnect()
                success, message = self.db.delete_project(self.current_project)
                if success:
                    if self.current_project in self.project_selection_window.open_dashboards:
                        del self.project_selection_window.open_dashboards[self.current_project]
                    self.project_selection_window.load_projects()
                    self.close()
                    QMessageBox.information(self, "Success", message)
                else:
                    QMessageBox.warning(self, "Error", message)
            except Exception as e:
                logging.error(f"Error deleting project: {str(e)}")
                QMessageBox.warning(self, "Error", f"Error deleting project: {str(e)}")

    def start_saving(self):
        if self.current_feature != "Time View":
            QMessageBox.warning(self, "Error", "Saving is only available in Time View!")
            return
        feature_instance = self.feature_instances.get("Time View")
        if not feature_instance:
            QMessageBox.warning(self, "Error", "Time View feature not initialized!")
            return
        try:
            feature_instance.start_saving()
            self.is_saving = True
            self.sub_tool_bar.update_subtoolbar()
            logging.info("Started saving data from dashboard")
            self.file_bar.update_file_bar()
        except Exception as e:
            logging.error(f"Failed to start saving: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to start saving: {str(e)}")

    def stop_saving(self):
        if self.current_feature != "Time View":
            QMessageBox.warning(self, "Error", "Saving is only available in Time View!")
            return
        feature_instance = self.feature_instances.get("Time View")
        if not feature_instance:
            QMessageBox.warning(self, "Error", "Time View feature not initialized!")
            return
        try:
            feature_instance.stop_saving()
            self.is_saving = False
            self.sub_tool_bar.update_subtoolbar()
            logging.info("Stopped saving data from dashboard")
            self.file_bar.update_file_bar()
        except Exception as e:
            logging.error(f"Failed to stop saving: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to stop saving: {str(e)}")

    def display_feature_content(self, feature_name, project_name):
        def render_feature():
            try:
                self.current_project = project_name
                self.current_feature = feature_name
                self.is_saving = False
                self.sub_tool_bar.update_subtoolbar()
                self.sub_tool_bar.current_feature_label.setText(feature_name)

                current_console_height = self.console.console_message_area.height()

                feature_instance = self.feature_instances.get(feature_name)
                sub_window = self.sub_windows.get(feature_name)

                if feature_instance and feature_instance.project_name == project_name and sub_window:
                    try:
                        if sub_window.isHidden():
                            sub_window.show()
                        sub_window.raise_()
                        sub_window.activateWindow()
                        self.main_section.arrange_layout(prompt_for_layout=False)
                        self.console.console_message_area.setFixedHeight(current_console_height)
                        return
                    except RuntimeError:
                        del self.feature_instances[feature_name]
                        del self.sub_windows[feature_name]
                        feature_instance = None
                        sub_window = None

                feature_classes = {
                    "Create Tags": CreateTagsFeature,
                    "Tabular View": TabularViewFeature,
                    "Time View": TimeViewFeature,
                    "Time Report": TimeReportFeature,
                    "FFT": FFTViewFeature,
                    "Waterfall": WaterfallFeature,
                    "Orbit": OrbitFeature,
                    "Trend View": TrendViewFeature,
                    "Multiple Trend View": MultiTrendFeature,
                    "Bode Plot": BodePlotFeature,
                    "History Plot": HistoryPlotFeature,
                    "Report": ReportFeature
                }

                if feature_name in feature_classes:
                    try:
                        if not self.db.is_connected():
                            self.db.reconnect()
                        feature_instance = feature_classes[feature_name](self, self.db, project_name)
                        self.feature_instances[feature_name] = feature_instance
                        widget = feature_instance.get_widget()
                        if widget:
                            sub_window = QMdiSubWindow()
                            sub_window.setWidget(widget)
                            sub_window.setWindowTitle(feature_name)
                            sub_window.setAttribute(Qt.WA_DeleteOnClose)
                            sub_window.resize(400, 300)
                            self.main_section.mdi_area.addSubWindow(sub_window)
                            self.sub_windows[feature_name] = sub_window
                            sub_window.show()
                            sub_window.closeEvent = lambda event, fn=feature_name: self.on_subwindow_closed(event, fn)
                            self.main_section.arrange_layout(prompt_for_layout=False)
                            self.console.console_message_area.setFixedHeight(current_console_height)
                        else:
                            logging.error(f"Feature {feature_name} returned invalid widget")
                            QMessageBox.warning(self, "Error", f"Feature {feature_name} failed to initialize")
                    except Exception as e:
                        logging.error(f"Failed to load feature {feature_name}: {str(e)}")
                        QMessageBox.warning(self, "Error", f"Failed to load {feature_name}: {str(e)}")
                else:
                    logging.warning(f"Unknown feature: {feature_name}")
                    QMessageBox.warning(self, "Error", f"Unknown feature: {feature_name}")
            except Exception as e:
                logging.error(f"Error displaying feature content: {str(e)}")
                QMessageBox.warning(self, "Error", f"Error displaying feature: {str(e)}")
            finally:
                self.console.console_message_area.setFixedHeight(current_console_height)

        QTimer.singleShot(50, render_feature)

    def on_subwindow_closed(self, event, feature_name):
        try:
            if feature_name in self.feature_instances:
                instance = self.feature_instances[feature_name]
                if hasattr(instance, 'cleanup'):
                    instance.cleanup()
                widget = instance.get_widget()
                if widget:
                    widget.hide()
                    widget.setParent(None)
                    widget.deleteLater()
                del self.feature_instances[feature_name]
            if feature_name in self.sub_windows:
                del self.sub_windows[feature_name]
            if self.current_feature == feature_name:
                self.current_feature = None
                self.is_saving = False
                self.sub_tool_bar.current_feature_label.setText("")
                self.sub_tool_bar.update_subtoolbar()
            self.main_section.arrange_layout(prompt_for_layout=False)
            self.main_section.mdi_area.setMinimumSize(0, 0)
            gc.collect()
        except Exception as e:
            logging.error(f"Error cleaning up sub-window for {feature_name}: {str(e)}")
        event.accept()

    def save_action(self):
        if self.current_project:
            try:
                if not self.db.is_connected():
                    self.db.reconnect()
                project_data = self.db.get_project_data(self.current_project)
                if project_data:
                    QMessageBox.information(self, "Save", f"Data for project '{self.current_project}' saved successfully!")
                else:
                    QMessageBox.warning(self, "Save Error", "No data to save for the selected project!")
                self.file_bar.update_file_bar()
            except Exception as e:
                logging.error(f"Error saving project: {str(e)}")
                QMessageBox.warning(self, "Error", f"Error saving project: {str(e)}")
        else:
            QMessageBox.warning(self, "Save Error", "No project selected to save!")

    def refresh_action(self):
        try:
            if self.current_project and self.current_feature:
                self.display_feature_content(self.current_feature, self.current_project)
                QMessageBox.information(self, "Refresh", f"Refreshed view for '{self.current_feature}'!")
            else:
                self.display_feature_content("Create Tags", self.current_project)
                QMessageBox.information(self, "Refresh", "Refreshed default view!")
            self.file_bar.update_file_bar()
        except Exception as e:
            logging.error(f"Error refreshing view: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error refreshing view: {str(e)}")

    def display_dashboard(self):
        self.current_feature = None
        self.is_saving = False
        self.timer.stop()
        self.sub_tool_bar.update_subtoolbar()
        self.display_feature_content("Create Tags", self.current_project)
        self.file_bar.update_file_bar()

    def clear_content_layout(self):
        try:
            for feature_name in list(self.sub_windows.keys()):
                sub_window = self.sub_windows[feature_name]
                sub_window.close()
            self.sub_windows.clear()
            for feature_name in list(self.feature_instances.keys()):
                try:
                    instance = self.feature_instances[feature_name]
                    if hasattr(instance, 'cleanup'):
                        instance.cleanup()
                    widget = instance.get_widget()
                    if widget:
                        widget.hide()
                        widget.setParent(None)
                        widget.deleteLater()
                    del self.feature_instances[feature_name]
                except Exception as e:
                    logging.error(f"Error cleaning up feature instance {feature_name}: {str(e)}")
            self.main_section.mdi_area.setMinimumSize(0, 0)
            gc.collect()
        except Exception as e:
            logging.error(f"Error clearing content layout: {str(e)}")

    def settings_action(self):
        QMessageBox.information(self, "Settings", "Settings functionality not implemented yet.")
        self.file_bar.update_file_bar()

    def closeEvent(self, event):
        try:
            if self.timer.isActive():
                self.timer.stop()
            self.cleanup_mqtt()
            self.clear_content_layout()
            if self.db and self.db.is_connected():
                self.db.close_connection()
            if self.current_project in self.project_selection_window.open_dashboards:
                del self.project_selection_window.open_dashboards[self.current_project]
            app = QApplication.instance()
            if app:
                app.quit()
        except Exception as e:
            logging.error(f"Error during closeEvent: {str(e)}")
        finally:
            event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(50, lambda: self.main_section.arrange_layout(prompt_for_layout=False))