from PyQt5.QtWidgets import QWidget, QVBoxLayout, QMdiArea, QScrollArea, QMdiSubWindow
from PyQt5.QtCore import Qt
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MainSection(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.current_widget = None
        self.current_layout = "2x2"  # Default layout
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Wrap QMdiArea in a QScrollArea to enable scrolling
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { background-color: #263238; border: none; }
            QScrollBar:vertical {
                border: none;
                background: #2c3e50;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #4a90e2;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                border: none;
                background: #2c3e50;
                height: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:horizontal {
                background: #4a90e2;
                border-radius: 5px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                background: none;
            }
        """)

        self.mdi_area = QMdiArea()
        self.mdi_area.setStyleSheet("QMdiArea { background-color: #263238; border: none; }")
        self.mdi_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.mdi_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Set the QMdiArea as the widget for the QScrollArea
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
            # Create a subwindow
            subwindow = QMdiSubWindow()
            subwindow.setWidget(widget)

            # Use the feature_name directly as the title
            subwindow.setWindowTitle(feature_name)

            # Add the subwindow to the MDI area
            self.mdi_area.addSubWindow(subwindow)
            subwindow.show()
            subwindow.raise_()
            subwindow.activateWindow()

            # Arrange the subwindows
            self.arrange_layout()
            logging.debug(f"Successfully added subwindow with title: {feature_name}")
        except Exception as e:
            logging.error(f"Failed to add subwindow for {feature_name}: {str(e)}")

    def clear_widget(self):
        try:
            # Close all subwindows in the MDI area
            for subwindow in self.mdi_area.subWindowList():
                self.mdi_area.removeSubWindow(subwindow)
                subwindow.hide()
                subwindow.setParent(None)
                subwindow.deleteLater()
                logging.debug(f"Closed subwindow during clear_widget: {subwindow.windowTitle()}")
            
            if self.current_widget:
                self.layout.removeWidget(self.current_widget)
                self.current_widget.hide()
                self.current_widget.setParent(None)
                self.current_widget.deleteLater()
                self.current_widget = None
                logging.debug("Cleared custom widget from MainSection")
            
            self.scroll_area.show()
            self.arrange_layout()
            logging.debug("Scroll area with MDI area shown in MainSection")
        except Exception as e:
            logging.error(f"Error in clear_widget: {str(e)}")

    def arrange_layout(self, layout=None, prompt_for_layout=False):
        try:
            if self.current_widget:
                logging.debug("Skipping MDI arrangement due to custom widget")
                return  # Don't arrange MDI subwindows if a custom widget is displayed

            # Update the current layout if a new one is provided
            if layout:
                self.current_layout = layout

            subwindows = self.mdi_area.subWindowList()
            if not subwindows:
                self.mdi_area.setMinimumSize(0, 0)
                logging.debug("No subwindows to arrange")
                return

            # Ensure all subwindows are visible and not minimized
            for subwindow in subwindows:
                subwindow.showNormal()
                logging.debug(f"Ensured subwindow is visible: {subwindow.windowTitle()}")

            # Parse the layout (e.g., "2x2" -> rows=2, cols=2)
            rows, cols = map(int, self.current_layout.split('x'))

            # Get the viewport size
            viewport_width = self.scroll_area.viewport().width()
            viewport_height = self.scroll_area.viewport().height()

            # Define a minimum size for subwindows
            MIN_SUBWINDOW_WIDTH = 300
            MIN_SUBWINDOW_HEIGHT = 200

            # Calculate the size for each subwindow
            subwindow_width = max(viewport_width // cols, MIN_SUBWINDOW_WIDTH)
            subwindow_height = max(viewport_height // rows, MIN_SUBWINDOW_HEIGHT)

            # Arrange subwindows in the selected grid pattern
            for idx, subwindow in enumerate(subwindows):
                # Determine the row and column for the current subwindow
                page = idx // (rows * cols)  # Which "page" of the grid (for scrolling)
                idx_in_page = idx % (rows * cols)  # Index within the current page
                row = idx_in_page // cols
                col = idx_in_page % cols

                # Calculate position for the subwindow
                x = col * subwindow_width
                y = (page * viewport_height) + (row * subwindow_height)

                # Resize and move the subwindow
                subwindow.setGeometry(x, y, subwindow_width, subwindow_height)
                logging.debug(f"Arranged subwindow {subwindow.windowTitle()} at ({x}, {y}) with size ({subwindow_width}x{subwindow_height})")

            # Calculate the total size needed for the MDI area
            total_pages_needed = (len(subwindows) + (rows * cols) - 1) // (rows * cols)
            total_height = total_pages_needed * viewport_height
            total_width = viewport_width

            # Adjust the size of the QMdiArea
            self.mdi_area.setMinimumSize(total_width, total_height)

            logging.info(
                f"Arranged {len(subwindows)} MDI subwindows in a {self.current_layout} grid pattern: "
                f"Viewport size ({viewport_width}x{viewport_height}), "
                f"Subwindow size ({subwindow_width}x{subwindow_height}), "
                f"Total pages needed: {total_pages_needed}"
            )
        except Exception as e:
            logging.error(f"Error in arrange_layout: {str(e)}")