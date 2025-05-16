from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import Qt
import logging

# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class SelectProjectWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        self.setStyleSheet("background-color: #f5f7fa;")

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        self.setLayout(layout)

        card_widget = QWidget()
        card_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 15px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                padding: 30px;
            }
        """)
        card_layout = QVBoxLayout()
        card_layout.setSpacing(20)
        card_widget.setLayout(card_layout)
        layout.addWidget(card_widget)

        title_label = QLabel("Select an option")
        title_label.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #343a40;
            margin-bottom: 20px;
        """)
        card_layout.addWidget(title_label, alignment=Qt.AlignCenter)

        create_button = QPushButton("Create New Project")
        create_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                font-weight: bold;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """)
        create_button.clicked.connect(self.parent.create_project)
        card_layout.addWidget(create_button, alignment=Qt.AlignCenter)

        open_button = QPushButton("Open Existing Project")
        open_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                font-weight: bold;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        open_button.clicked.connect(self.parent.display_project_structure)
        card_layout.addWidget(open_button, alignment=Qt.AlignCenter)

        # logout_button = QPushButton("Logout")
        # logout_button.setStyleSheet("""
        #     QPushButton {
        #         background-color: #dc3545;
        #         color: white;
        #         border-radius: 8px;
        #         padding: 12px;
        #         font-size: 16px;
        #         font-weight: bold;
        #         min-width: 200px;
        #     }
        #     QPushButton:hover {
        #         background-color: #c82333;
        #     }
        #     QPushButton:pressed {
        #         background-color: #bd2130;
        #     }
        # """)
        # logout_button.clicked.connect(self.parent.back_to_login)
        # card_layout.addWidget(logout_button, alignment=Qt.AlignCenter)