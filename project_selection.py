from PyQt5.QtWidgets import QWidget
from dashboard.dashboard_window import DashboardWindow

class ProjectSelectionWindow(QWidget):
    def __init__(self, db, email, auth_window=None):
        super().__init__()
        self.db = db
        self.email = email
        self.auth_window = auth_window
        self.dashboard_window = None
        self.initUI()

    def initUI(self):
        # Placeholder for UI initialization
        # This should contain the logic to display the project selection UI
        # (e.g., SelectProjectWidget as shown in your previous code)
        # self.setWindowTitle("Project Selection - Sarayu Desktop Application")
        # self.setWindowState(Qt.WindowMaximized)

        # For now, let's assume it directly opens the DashboardWindow
        # Replace this with your actual project selection logic
        self.open_dashboard()

    def open_dashboard(self):
        # Open the DashboardWindow (as shown in your previous code)
        self.dashboard_window = DashboardWindow(self.db, self.email, self.auth_window)
        self.dashboard_window.show()
        self.hide()