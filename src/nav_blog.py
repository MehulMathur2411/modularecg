from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton
from PyQt5.QtCore import Qt
import webbrowser

class NavBlog(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel("<h2>Blog</h2><p>Read the latest updates and articles from PulseMonitor.</p>")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        link_btn = QPushButton("Visit Blog on deckmount.in")
        link_btn.setStyleSheet("color: #ff6600; font-size: 16px; font-weight: bold; text-decoration: underline; background: none; border: none;")
        link_btn.clicked.connect(lambda: webbrowser.open('https://deckmount.in/blog'))
        layout.addWidget(link_btn, alignment=Qt.AlignCenter)
        self.setLayout(layout)
