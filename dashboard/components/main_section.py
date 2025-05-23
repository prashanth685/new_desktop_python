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
            subwindow.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMaximizeButtonHint)
            subwindow.setWidget(widget)
            subwindow.setOption(QMdiSubWindow.RubberBandMove, False)
            title = f"{model_name or ''} - {channel_name or ''} - {feature_name}".strip(" - ")
            subwindow.setWindowTitle(title)
            self.mdi_area.addSubWindow(subwindow)
            subwindow.showNormal()
            subwindow.raise_()
            subwindow.activateWindow()
            self.arrange_layout()
            logging.debug(f"Successfully added subwindow with title: {title}")
            return subwindow
        except Exception as e:
            logging.error(f"Failed to add subwindow for {feature_name}: {str(e)}")
            return None

    def clear_widget(self):
        try:
            for subwindow in self.mdi_area.subWindowList():
                try:
                    if subwindow.isMaximized():
                        subwindow.showNormal()
                    subwindow.close()
                    self.mdi_area.removeSubWindow(subwindow)
                    widget = subwindow.widget()
                    if widget:
                        widget.hide()
                        widget.setParent(None)
                        widget.deleteLater()
                    subwindow.setParent(None)
                    subwindow.deleteLater()
                    logging.debug(f"Closed subwindow: {subwindow.windowTitle()}")
                except Exception as e:
                    logging.error(f"Error closing subwindow {subwindow.windowTitle()}: {str(e)}")
            
            if self.current_widget:
                self.layout.removeWidget(self.current_widget)
                self.current_widget.hide()
                self.current_widget.setParent(None)
                self.current_widget.deleteLater()
                self.current_widget = None
                logging.debug("Cleared custom widget from MainSection")
            
            self.scroll_area.show()
            self.mdi_area.update()
            self.scroll_area.viewport().update()
            logging.debug("Scroll area with MDI area shown in MainSection")
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
                self.scroll_area.viewport().update()
                logging.debug("No subwindows to arrange")
                return

            for subwindow in subwindows:
                if subwindow.isMaximized():
                    subwindow.showNormal()
                subwindow.setOption(QMdiSubWindow.RubberBandMove, False)
                logging.debug(f"Ensured subwindow is visible and fixed: {subwindow.windowTitle()}")

            rows, cols = map(int, self.current_layout.split('x'))
            viewport_width = self.scroll_area.viewport().width()
            viewport_height = self.scroll_area.viewport().height()
            MIN_SUBWINDOW_WIDTH = 300
            MIN_SUBWINDOW_HEIGHT = 200
            GAP = 10

            subwindow_width = max((viewport_width - (cols + 1) * GAP) // cols, MIN_SUBWINDOW_WIDTH)
            subwindow_height = max((viewport_height - (rows + 1) * GAP) // rows, MIN_SUBWINDOW_HEIGHT)

            for idx, subwindow in enumerate(subwindows):
                page = idx // (rows * cols)
                idx_in_page = idx % (rows * cols)
                row = idx_in_page // cols
                col = idx_in_page % cols
                x = GAP + col * (subwindow_width + GAP)
                y = (page * viewport_height) + GAP + (row * (subwindow_height + GAP))
                subwindow.setGeometry(x, y, subwindow_width, subwindow_height)
                logging.debug(f"Arranged subwindow {subwindow.windowTitle()} at ({x}, {y}) with size ({subwindow_width}x{subwindow_height})")

            total_pages_needed = (len(subwindows) + (rows * cols) - 1) // (rows * cols)
            total_height = total_pages_needed * (viewport_height + GAP)
            total_width = viewport_width + GAP * 2
            self.mdi_area.setMinimumSize(total_width, total_height)
            self.mdi_area.update()
            self.scroll_area.viewport().update()

            logging.info(
                f"Arranged {len(subwindows)} MDI subwindows in a {self.current_layout} grid pattern: "
                f"Viewport size ({viewport_width}x{viewport_height}), "
                f"Subwindow size ({subwindow_width}x{subwindow_height}), "
                f"Total pages needed: {total_pages_needed}, "
                f"Gap: {GAP}px"
            )
        except Exception as e:
            logging.error(f"Error in arrange_layout: {str(e)}")




# from PyQt5.QtWidgets import QWidget, QVBoxLayout, QMdiArea, QScrollArea, QMdiSubWindow
# from PyQt5.QtCore import Qt, QPoint
# import logging

# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


# class FixedSubWindow(QMdiSubWindow):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self._allow_move = False
#         self._fixed_pos = self.pos()

#     def moveEvent(self, event):
#         if not self._allow_move:
#             # Snap back to fixed position to block user move
#             if self.pos() != self._fixed_pos:
#                 self.move(self._fixed_pos)
#         else:
#             # If programmatic move, update fixed pos accordingly
#             self._fixed_pos = self.pos()
#         super().moveEvent(event)

#     def showEvent(self, event):
#         self._fixed_pos = self.pos()
#         super().showEvent(event)

#     def setGeometry(self, *args):
#         # Allow move for this operation
#         self._allow_move = True
#         super().setGeometry(*args)
#         self._allow_move = False



# class MainSection(QWidget):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.parent = parent
#         self.current_widget = None
#         self.current_layout = "2x2"  # Default layout
#         self.initUI()

#     def initUI(self):
#         self.layout = QVBoxLayout()
#         self.layout.setContentsMargins(0, 0, 0, 0)
#         self.layout.setSpacing(0)

#         self.scroll_area = QScrollArea()
#         self.scroll_area.setWidgetResizable(True)
#         self.scroll_area.setStyleSheet("""
#             QScrollArea { background-color: #263238; border: none; }
#             QScrollBar:vertical {
#                 border: none;
#                 background: #2c3e50;
#                 width: 10px;
#                 margin: 0px 0px 0px 0px;
#             }
#             QScrollBar::handle:vertical {
#                 background: #4a90e2;
#                 border-radius: 5px;
#             }
#             QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
#                 background: none;
#             }
#             QScrollBar:horizontal {
#                 border: none;
#                 background: #2c3e50;
#                 height: 10px;
#                 margin: 0px 0px 0px 0px;
#             }
#             QScrollBar::handle:horizontal {
#                 background: #4a90e2;
#                 border-radius: 5px;
#             }
#             QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
#                 background: none;
#             }
#         """)

#         self.mdi_area = QMdiArea()
#         self.mdi_area.setStyleSheet("""
#             QMdiArea { background-color: #263238; border: none; }
#             QMdiSubWindow {
#                 background-color: #263238;
#                 border: 1px solid #4a90e2;
#                 border-radius: 4px;
#             }
#         """)
#         self.mdi_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
#         self.mdi_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

#         self.scroll_area.setWidget(self.mdi_area)
#         self.layout.addWidget(self.scroll_area)
#         self.setLayout(self.layout)

#     def set_widget(self, widget, feature_name=None, channel_name=None, model_name=None):
#         self.clear_widget()
#         self.current_widget = widget
#         self.layout.addWidget(widget)
#         self.scroll_area.hide()
#         logging.debug(f"Set widget in MainSection: {type(widget).__name__}")

#     def add_subwindow(self, widget, feature_name, channel_name=None, model_name=None):
#         try:
#             subwindow = FixedSubWindow()
#             subwindow.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMaximizeButtonHint)
#             subwindow.setWidget(widget)
#             title = f"{model_name or ''} - {channel_name or ''} - {feature_name}".strip(" - ")
#             subwindow.setWindowTitle(title)
#             self.mdi_area.addSubWindow(subwindow)
#             subwindow.showNormal()
#             subwindow.raise_()
#             subwindow.activateWindow()
#             self.arrange_layout()
#             logging.debug(f"Successfully added subwindow with title: {title}")
#             return subwindow
#         except Exception as e:
#             logging.error(f"Failed to add subwindow for {feature_name}: {str(e)}")
#             return None

#     def clear_widget(self):
#         try:
#             for subwindow in self.mdi_area.subWindowList():
#                 try:
#                     if subwindow.isMaximized():
#                         subwindow.showNormal()
#                     subwindow.close()
#                     self.mdi_area.removeSubWindow(subwindow)
#                     widget = subwindow.widget()
#                     if widget:
#                         widget.hide()
#                         widget.setParent(None)
#                         widget.deleteLater()
#                     subwindow.setParent(None)
#                     subwindow.deleteLater()
#                     logging.debug(f"Closed subwindow: {subwindow.windowTitle()}")
#                 except Exception as e:
#                     logging.error(f"Error closing subwindow {subwindow.windowTitle()}: {str(e)}")

#             if self.current_widget:
#                 self.layout.removeWidget(self.current_widget)
#                 self.current_widget.hide()
#                 self.current_widget.setParent(None)
#                 self.current_widget.deleteLater()
#                 self.current_widget = None
#                 logging.debug("Cleared custom widget from MainSection")

#             self.scroll_area.show()
#             self.mdi_area.update()
#             self.scroll_area.viewport().update()
#             logging.debug("Scroll area with MDI area shown in MainSection")
#         except Exception as e:
#             logging.error(f"Error in clear_widget: {str(e)}")

#     def arrange_layout(self, layout=None, prompt_for_layout=False):
#         try:
#             if self.current_widget:
#                 logging.debug("Skipping MDI arrangement due to custom widget")
#                 return

#             if layout:
#                 self.current_layout = layout

#             subwindows = self.mdi_area.subWindowList()
#             if not subwindows:
#                 self.mdi_area.setMinimumSize(0, 0)
#                 self.scroll_area.viewport().update()
#                 logging.debug("No subwindows to arrange")
#                 return

#             for subwindow in subwindows:
#                 if subwindow.isMaximized():
#                     subwindow.showNormal()
#                 subwindow.setOption(QMdiSubWindow.RubberBandMove, False)
#                 logging.debug(f"Ensured subwindow is visible and fixed: {subwindow.windowTitle()}")

#             rows, cols = map(int, self.current_layout.split('x'))
#             viewport_width = self.scroll_area.viewport().width()
#             viewport_height = self.scroll_area.viewport().height()
#             MIN_SUBWINDOW_WIDTH = 300
#             MIN_SUBWINDOW_HEIGHT = 200
#             GAP = 10

#             subwindow_width = max((viewport_width - (cols + 1) * GAP) // cols, MIN_SUBWINDOW_WIDTH)
#             subwindow_height = max((viewport_height - (rows + 1) * GAP) // rows, MIN_SUBWINDOW_HEIGHT)

#             for idx, subwindow in enumerate(subwindows):
#                 page = idx // (rows * cols)
#                 idx_in_page = idx % (rows * cols)
#                 row = idx_in_page // cols
#                 col = idx_in_page % cols
#                 x = GAP + col * (subwindow_width + GAP)
#                 y = (page * viewport_height) + GAP + (row * (subwindow_height + GAP))
#                 subwindow.setGeometry(x, y, subwindow_width, subwindow_height)
#                 logging.debug(f"Arranged subwindow {subwindow.windowTitle()} at ({x}, {y}) with size ({subwindow_width}x{subwindow_height})")

#             total_pages_needed = (len(subwindows) + (rows * cols) - 1) // (rows * cols)
#             total_height = total_pages_needed * (viewport_height + GAP)
#             total_width = viewport_width + GAP * 2
#             self.mdi_area.setMinimumSize(total_width, total_height)
#             self.mdi_area.update()
#             self.scroll_area.viewport().update()

#             logging.info(
#                 f"Arranged {len(subwindows)} MDI subwindows in a {self.current_layout} grid pattern: "
#                 f"Viewport size ({viewport_width}x{viewport_height}), "
#                 f"Subwindow size ({subwindow_width}x{subwindow_height}), "
#                 f"Total pages needed: {total_pages_needed}, "
#                 f"Gap: {GAP}px"
#             )
#         except Exception as e:
#             logging.error(f"Error in arrange_layout: {str(e)}")
