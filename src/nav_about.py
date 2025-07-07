from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton
from PyQt5.QtCore import Qt
import webbrowser

class NavAbout(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel("<h2>About Us</h2><p>Learn more about PulseMonitor and our mission.</p>")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        link_btn = QPushButton("About Us on deckmount.in")
        link_btn.setStyleSheet("color: #ff6600; font-size: 16px; font-weight: bold; text-decoration: underline; background: none; border: none;")
        link_btn.clicked.connect(lambda: webbrowser.open('https://deckmount.in/about-us'))
        layout.addWidget(link_btn, alignment=Qt.AlignCenter)
        self.setLayout(layout)
