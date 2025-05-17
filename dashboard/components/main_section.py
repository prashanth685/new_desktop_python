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
        # Create a subwindow
        subwindow = QMdiSubWindow()
        subwindow.setWidget(widget)
        
        # Set the title based on the feature
        if feature_name in ["Time View", "Time Report"]:
            title = f"{type(widget).__name__} - {model_name if model_name else 'Unknown Model'}"
        else:
            title = f"{type(widget).__name__} - {channel_name if channel_name else 'Unknown Channel'}"
        subwindow.setWindowTitle(title)
        
        # Add the subwindow to the MDI area
        self.mdi_area.addSubWindow(subwindow)
        subwindow.show()
        
        # Arrange the subwindows according to the current layout
        self.arrange_layout()
        logging.debug(f"Added subwindow in MainSection: {title}")

    def clear_widget(self):
        if self.current_widget:
            self.layout.removeWidget(self.current_widget)
            self.current_widget.hide()
            self.current_widget.setParent(None)
            self.current_widget.deleteLater()
            self.current_widget = None
            logging.debug("Cleared custom widget from MainSection")
        self.scroll_area.show()
        logging.debug("Scroll area with MDI area shown in MainSection")

    def arrange_layout(self, layout=None, prompt_for_layout=False):
        if self.current_widget:
            logging.debug("Skipping MDI arrangement due to custom widget")
            return  # Don't arrange MDI subwindows if a custom widget is displayed

        # Update the current layout if a new one is provided
        if layout:
            self.current_layout = layout

        subwindows = self.mdi_area.subWindowList()
        if not subwindows:
            return

        # Ensure all subwindows are visible and not minimized
        for subwindow in subwindows:
            subwindow.showNormal()

        # Parse the layout (e.g., "1x2" -> rows=1, cols=2)
        rows, cols = map(int, self.current_layout.split('x'))

        # Calculate the size of the visible area (excluding scrollbars)
        viewport_width = self.scroll_area.viewport().width()
        viewport_height = self.scroll_area.viewport().height()

        # Calculate the size for each subwindow in the grid
        subwindow_width = viewport_width // cols
        subwindow_height = viewport_height // rows

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

        # Adjust the size of the QMdiArea to accommodate all subwindows
        total_pages_needed = (len(subwindows) + (rows * cols) - 1) // (rows * cols)
        total_height = total_pages_needed * viewport_height
        total_width = cols * subwindow_width
        self.mdi_area.setMinimumSize(total_width, total_height)

        logging.info(f"Arranged {len(subwindows)} MDI subwindows in a {self.current_layout} grid pattern")