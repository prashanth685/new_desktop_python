
from PyQt5.QtWidgets import QMdiArea, QInputDialog, QMessageBox
from PyQt5.QtCore import Qt, QTimer
import logging

class MainSection(QMdiArea):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        self.setStyleSheet("QMdiArea { background-color: #263238; border: none; }")

    def arrange_layout(self, prompt_for_layout=False):
        try:
            sub_windows = list(self.parent.sub_windows.values())
            if not sub_windows:
                self.parent.console.append_to_console("No sub-windows to arrange.")
                return

            if prompt_for_layout:
                layout_options = ["1x2", "2x2", "3x3"]
                layout_choice, ok = QInputDialog.getItem(self.parent, "Select Layout",
                                                        "Choose a layout:",
                                                        layout_options, layout_options.index(f"{self.parent.current_layout[0]}x{self.parent.current_layout[1]}"), False)
                if not ok or not layout_choice:
                    self.parent.console.append_to_console("Layout selection cancelled.")
                    return
                rows, cols = map(int, layout_choice.split('x'))
                self.parent.current_layout = (rows, cols)
            else:
                rows, cols = self.parent.current_layout

            GAP = 10
            num_windows = len(sub_windows)

            # Get MDI area dimensions
            mdi_rect = self.viewport().rect()
            mdi_width = mdi_rect.width()
            mdi_height = mdi_rect.height()

            if rows == 1 and cols == 2:
                windows_per_grid = 2
                num_grids = (num_windows + 1) // 2
                total_vertical_gaps = (num_grids - 1) * GAP if num_grids > 1 else 0
                window_width = max(700, (mdi_width) // 2)
                window_height = max(700, (mdi_height) // 2)

                total_content_height = num_grids * (window_height + GAP) + total_vertical_gaps

                for i, sub_window in enumerate(sub_windows):
                    try:
                        grid_index = i // windows_per_grid
                        col_in_grid = i % 2

                        x = col_in_grid * (window_width)
                        y = grid_index * (window_height)

                        sub_window.setGeometry(x, y, window_width, window_height)
                        sub_window.showNormal()
                        sub_window.raise_()
                    except Exception as e:
                        logging.error(f"Error arranging sub-window {i}: {str(e)}")
                        self.parent.console.append_to_console(f"Error arranging sub-window {i}: {str(e)}")

                self.setMinimumHeight(mdi_height)
                self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                self.setMinimumSize(0, 0)
                self.viewport().update()

            else:
                windows_per_grid = rows * cols
                num_grids = (num_windows + windows_per_grid - 1) // windows_per_grid
                horizontal_gaps_per_grid = (cols - 1) * GAP if cols > 1 else 0
                vertical_gaps_per_grid = (rows - 1) * GAP if rows > 1 else 0
                total_horizontal_gaps = horizontal_gaps_per_grid
                total_vertical_gaps = (num_grids - 1) * GAP if num_grids > 1 else 0
                total_vertical_gaps += vertical_gaps_per_grid * num_grids

                available_width = mdi_width - total_horizontal_gaps
                base_window_width = max(300, available_width // max(1, cols))
                base_window_height = max(200, (mdi_height - vertical_gaps_per_grid) // max(1, rows))

                for i, sub_window in enumerate(sub_windows):
                    try:
                        grid_index = i // windows_per_grid
                        index_in_grid = i % windows_per_grid
                        row_in_grid = index_in_grid // cols
                        col_in_grid = index_in_grid % cols

                        x = col_in_grid * (base_window_width + GAP)
                        y = (grid_index * (rows * base_window_height + vertical_gaps_per_grid + GAP)) + (row_in_grid * (base_window_height + GAP))

                        window_width = base_window_width
                        window_height = base_window_height

                        if col_in_grid == cols - 1:
                            remaining_width = mdi_width - x - (cols - 1) * GAP
                            window_width = max(300, remaining_width)

                        if row_in_grid == rows - 1:
                            grid_top = grid_index * (rows * base_window_height + vertical_gaps_per_grid + GAP)
                            grid_height = (rows * base_window_height + (rows - 1) * GAP)
                            remaining_height = (mdi_height - grid_top - grid_height) // max(1, num_grids)
                            window_height = max(200, base_window_height + remaining_height // rows)

                        sub_window.setGeometry(x, y, window_width, window_height)
                        sub_window.showNormal()
                        sub_window.raise_()
                    except Exception as e:
                        logging.error(f"Error arranging sub-window {i}: {str(e)}")
                        self.parent.console.append_to_console(f"Error arranging sub-window {i}: {str(e)}")

                total_height = num_grids * (rows * base_window_height + vertical_gaps_per_grid) + (num_grids - 1) * GAP
                self.setMinimumHeight(min(total_height, mdi_height))

            layout_str = f"{rows}x{cols}"
            logging.info(f"Arranged {num_windows} sub-windows in {layout_str} grid layout ({num_grids} grids) with 10px gaps")
            self.parent.console.append_to_console(f"Arranged {num_windows} sub-windows in {layout_str} grid layout ({num_grids} grids) with 10px gaps")
        except Exception as e:
            logging.error(f"Error arranging layout: {str(e)}")
            QMessageBox.warning(self.parent, "Error", f"Error arranging layout: {str(e)}")
            self.parent.console.append_to_console(f"Error arranging layout: {str(e)}")