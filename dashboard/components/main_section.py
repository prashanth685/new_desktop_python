
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QMdiArea, QScrollArea, QMdiSubWindow
from PyQt5.QtCore import Qt
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MainSection(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.current_widget = None
        self.current_layout = "2x2"
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { background-color: #263238; border: none; }
            QScrollBar:vertical {
                border: none;
                background: #2c3e50;
                width: 8px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #4a90e2;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                border: none;
                background: #2c3e50;
                height: 8px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:horizontal {
                background: #4a90e2;
                border-radius: 4px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                background: none;
            }
        """)

        self.mdi_area = QMdiArea()
        self.mdi_area.setStyleSheet("""
            QMdiArea { background-color: #263238; border: none; }
            QMdiSubWindow {
                background-color: #263238;
                border: 1px solid #4a90e2;
                border-radius: 4px;
            }
        """)
        self.mdi_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.mdi_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.mdi_area.setActivationOrder(QMdiArea.ActivationHistoryOrder)

        self.scroll_area.setWidget(self.mdi_area)
        self.layout.addWidget(self.scroll_area)
        self.setLayout(self.layout)

    def set_widget(self, widget, feature_name=None, channel_name=None, model_name=None):
        self.clear_widget()
        self.current_widget = widget
        self.layout.addWidget(widget)
        self.scroll_area.hide()
        logging.debug(f"Set widget in MainSection: {type(widget).__name__}")

    def add_subwindow(self, widget, feature_name, channel_name=None, model_name=None):
        try:
            subwindow = QMdiSubWindow()
            subwindow.setWidget(widget)
            subwindow.setOption(QMdiSubWindow.RubberBandMove, False)
            title = f"{model_name or ''} - {channel_name or ''} - {feature_name}".strip(" - ")
            subwindow.setWindowTitle(title)
            self.mdi_area.addSubWindow(subwindow)
            subwindow.showNormal()
            self.arrange_layout()
            logging.debug(f"Added subwindow with title: {title}")
            return subwindow
        except Exception as e:
            logging.error(f"Failed to add subwindow for {feature_name}: {str(e)}")
            return None

    def clear_widget(self):
        try:
            for subwindow in self.mdi_area.subWindowList():
                subwindow.close()
                self.mdi_area.removeSubWindow(subwindow)
                widget = subwindow.widget()
                if widget:
                    widget.hide()
                    widget.setParent(None)
                    widget.deleteLater()
                subwindow.setParent(None)
                subwindow.deleteLater()

            if self.current_widget:
                self.layout.removeWidget(self.current_widget)
                self.current_widget.hide()
                self.current_widget.setParent(None)
                self.current_widget.deleteLater()
                self.current_widget = None

            self.scroll_area.show()
            self.mdi_area.update()
            logging.debug("Cleared all subwindows and custom widget")
        except Exception as e:
            logging.error(f"Error in clear_widget: {str(e)}")

    def arrange_layout(self, layout=None, prompt_for_layout=False):
        try:
            if self.current_widget:
                logging.debug("Skipping MDI arrangement due to custom widget")
                return

            if layout:
                self.current_layout = layout

            subwindows = self.mdi_area.subWindowList()
            if not subwindows:
                self.mdi_area.setMinimumSize(0, 0)
                logging.debug("No subwindows to arrange")
                return

            rows, cols = map(int, self.current_layout.split('x'))
            viewport_width = self.scroll_area.viewport().width()
            viewport_height = self.scroll_area.viewport().height()
            MIN_SUBWINDOW_WIDTH = 250
            MIN_SUBWINDOW_HEIGHT = 150
            GAP = 5

            subwindow_width = max((viewport_width - (cols + 1) * GAP) // cols, MIN_SUBWINDOW_WIDTH)
            subwindow_height = max((viewport_height - (rows + 1) * GAP) // rows, MIN_SUBWINDOW_HEIGHT)

            for idx, subwindow in enumerate(subwindows):
                if subwindow.isMaximized():
                    subwindow.showNormal()
                row = (idx % (rows * cols)) // cols
                col = (idx % (rows * cols)) % cols
                x = GAP + col * (subwindow_width + GAP)
                y = GAP + row * (subwindow_height + GAP)
                subwindow.setGeometry(x, y, subwindow_width, subwindow_height)
                logging.debug(f"Arranged subwindow {subwindow.windowTitle()} at ({x}, {y}) with size ({subwindow_width}x{subwindow_height})")

            total_pages_needed = (len(subwindows) + (rows * cols) - 1) // (rows * cols)
            total_height = total_pages_needed * (viewport_height + GAP)
            total_width = viewport_width + GAP * 2
            self.mdi_area.setMinimumSize(total_width, total_height)
            self.mdi_area.update()

            logging.info(
                f"Arranged {len(subwindows)} MDI subwindows in a {self.current_layout} grid: "
                f"Subwindow size ({subwindow_width}x{subwindow_height})"
            )
        except Exception as e:
            logging.error(f"Error in arrange_layout: {str(e)}")