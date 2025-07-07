from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton
from PyQt5.QtCore import Qt
import webbrowser

class NavHome(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel("<h2>Home</h2><p>Welcome to PulseMonitor Home!</p>")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        link_btn = QPushButton("Visit deckmount.in")
        link_btn.setStyleSheet("color: #ff6600; font-size: 16px; font-weight: bold; text-decoration: underline; background: none; border: none;")
        link_btn.clicked.connect(lambda: webbrowser.open('https://deckmount.in/'))
        layout.addWidget(link_btn, alignment=Qt.AlignCenter)
        self.setLayout(layout)
