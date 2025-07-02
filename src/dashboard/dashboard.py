# ...existing imports...
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QGridLayout, QCalendarWidget, QTextEdit,
    QDialog, QLineEdit, QComboBox, QFormLayout
)
from PyQt5.QtGui import QFont, QPixmap, QMovie
from PyQt5.QtCore import Qt
import os
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class PieChartCanvas(FigureCanvas):
    def __init__(self, parent=None, width=3, height=3, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)
        self.plot_pie()

    def plot_pie(self):
        data = [30, 25, 30, 15]
        labels = ["December", "November", "October", "September"]
        colors = ["#ff6600", "#00b894", "#636e72", "#fdcb6e"]
        wedges, texts, autotexts = self.axes.pie(
            data, labels=labels, autopct='%1.0f%%', colors=colors, startangle=90
        )
        self.axes.set_aspect('equal')
        self.axes.set_title('Total Visitors', fontsize=12)

class SignInDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sign In")
        self.setFixedSize(340, 240)
        self.setStyleSheet("""
            QDialog { background: #fff; border-radius: 18px; }
            QLabel { font-size: 15px; color: #222; }
            QLineEdit, QComboBox { border: 2px solid #ff6600; border-radius: 8px; padding: 6px 10px; font-size: 15px; background: #f7f7f7; }
            QPushButton { background: #ff6600; color: white; border-radius: 10px; padding: 8px 0; font-size: 16px; font-weight: bold; }
            QPushButton:hover { background: #ff8800; }
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Sign In to PulseMonitor")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.role_combo = QComboBox()
        self.role_combo.addItems(["Doctor", "Patient"])
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter your name")
        self.pass_edit = QLineEdit()
        self.pass_edit.setPlaceholderText("Password")
        self.pass_edit.setEchoMode(QLineEdit.Password)
        form.addRow("Role:", self.role_combo)
        form.addRow("Name:", self.name_edit)
        form.addRow("Password:", self.pass_edit)
        layout.addLayout(form)
        self.signin_btn = QPushButton("Sign In")
        self.signin_btn.clicked.connect(self.accept)
        layout.addWidget(self.signin_btn)
    def get_user_info(self):
        return self.role_combo.currentText(), self.name_edit.text()

class Dashboard(QWidget):
    def __init__(self, username=None, role=None):
        super().__init__()
        self.setWindowTitle("PulseMonitor Dashboard")
        self.setStyleSheet("background: #f7f7f7;")
        self.setGeometry(100, 100, 1300, 900)
        self.username = username
        self.role = role
        # --- Plasma GIF background ---
        self.bg_label = QLabel(self)
        self.bg_label.setGeometry(0, 0, 1300, 900)
        self.bg_label.lower()
        movie = QMovie("plasma.gif")
        self.bg_label.setMovie(movie)
        movie.start()
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(18)
        main_layout.setContentsMargins(30, 20, 30, 20)
        # --- Header ---
        header = QHBoxLayout()
        logo = QLabel()
        logo.setText('<span style="color:#ff6600;font-size:22pt;font-weight:bold;">★ CardioCare</span>')
        header.addWidget(logo)
        nav = QLabel("<b>Dashboard</b> &nbsp; Schedule &nbsp; History &nbsp; Activity")
        nav.setFont(QFont("Arial", 12))
        header.addWidget(nav)
        header.addStretch()
        search = QLineEdit()
        search.setPlaceholderText("Search")
        search.setFixedWidth(180)
        header.addWidget(search)
        user = QLabel()
        user.setText(f'<b>{username or "User"}</b><br><span style="font-size:10pt;">Medical Consultant</span>')
        user.setPixmap(QPixmap(os.path.join("..", "assets", "her.png")).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        user.setAlignment(Qt.AlignRight)
        header.addWidget(user)
        main_layout.addLayout(header)
        # --- Greeting and Date Row ---
        greet_row = QHBoxLayout()
        greet = QLabel(f"<span style='font-size:18pt;font-weight:bold;'>Good Morning, {username or 'User'}</span><br><span style='color:#888;'>You have 3 appointment today</span>")
        greet.setFont(QFont("Arial", 14))
        greet_row.addWidget(greet)
        greet_row.addStretch()
        date_btn = QPushButton("25 Nov 2024  |  24H  |  Weekly")
        date_btn.setStyleSheet("background: #ff6600; color: white; border-radius: 16px; padding: 8px 24px;")
        greet_row.addWidget(date_btn)
        main_layout.addLayout(greet_row)
        # --- Main Grid ---
        grid = QGridLayout()
        grid.setSpacing(18)
        # --- Heart Rate Card ---
        heart_card = QFrame()
        heart_card.setStyleSheet("background: white; border-radius: 18px;")
        heart_layout = QVBoxLayout(heart_card)
        heart_label = QLabel("<b>Live Heart Rate Overview</b>")
        heart_label.setFont(QFont("Arial", 14, QFont.Bold))
        # Heartbeat effect on her.png
        heart_img = QLabel()
        heart_img_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'her.png'))
        heart_pixmap = QPixmap(heart_img_path).scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        heart_img.setPixmap(heart_pixmap)
        heart_img.setAlignment(Qt.AlignCenter)
        # Heartbeat animation using QPropertyAnimation
        from PyQt5.QtCore import QPropertyAnimation
        self.heart_anim = QPropertyAnimation(heart_img, b"geometry")
        self.heart_anim.setDuration(800)
        self.heart_anim.setLoopCount(-1)
        orig_rect = heart_img.geometry()
        self.heart_anim.setStartValue(orig_rect)
        self.heart_anim.setKeyValueAt(0.5, orig_rect.adjusted(-10, -10, 10, 10))
        self.heart_anim.setEndValue(orig_rect)
        heart_layout.addWidget(heart_label)
        heart_layout.addWidget(heart_img)
        heart_layout.addWidget(QLabel("<b>Stress Level:</b> Low"))
        heart_layout.addWidget(QLabel("<b>Average Variability:</b> 90ms"))
        grid.addWidget(heart_card, 0, 0, 2, 1)
        # Start the heartbeat animation after the widget is shown
        def start_heartbeat():
            self.heart_anim.start()
        heart_img.showEvent = lambda event: start_heartbeat()
        # --- Patient Body Analysis Cards ---
        analysis_card = QFrame()
        analysis_card.setStyleSheet("background: white; border-radius: 18px;")
        analysis_layout = QHBoxLayout(analysis_card)
        for title, value, unit in [
            ("Glucose Level", "127", "mg/dl"),
            ("Cholesterol Level", "164", "mg"),
            ("Paracetamol", "35", "%")
        ]:
            box = QVBoxLayout()
            lbl = QLabel(f"<b>{title}</b>")
            lbl.setFont(QFont("Arial", 10, QFont.Bold))
            val = QLabel(f"<span style='font-size:16pt;font-weight:bold;'>{value}</span> {unit}")
            box.addWidget(lbl)
            box.addWidget(val)
            analysis_layout.addLayout(box)
        grid.addWidget(analysis_card, 0, 1, 1, 2)
        # --- ECG Recording (Animated Chart) ---
        ecg_card = QFrame()
        ecg_card.setStyleSheet("background: white; border-radius: 18px;")
        ecg_layout = QVBoxLayout(ecg_card)
        ecg_label = QLabel("<b>ECG Recording</b>")
        ecg_label.setFont(QFont("Arial", 12, QFont.Bold))
        ecg_layout.addWidget(ecg_label)
        ecg_canvas = FigureCanvas(Figure(figsize=(4, 2)))
        ax = ecg_canvas.figure.subplots()
        x = np.linspace(0, 2, 500)
        y = 1000 + 200 * np.sin(2 * np.pi * 2 * x) + 50 * np.random.randn(500)
        ax.plot(x, y, color="#ff6600")
        ax.set_facecolor("#f7f7f7")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title("Lead II", fontsize=10)
        ecg_layout.addWidget(ecg_canvas)
        grid.addWidget(ecg_card, 1, 1)
        # --- Total Visitors (Pie Chart) ---
        pie_card = QFrame()
        pie_card.setStyleSheet("background: white; border-radius: 18px;")
        pie_layout = QVBoxLayout(pie_card)
        pie_canvas = PieChartCanvas()
        pie_layout.addWidget(pie_canvas)
        grid.addWidget(pie_card, 1, 2)
        # --- Schedule Card ---
        schedule_card = QFrame()
        schedule_card.setStyleSheet("background: white; border-radius: 18px;")
        schedule_layout = QVBoxLayout(schedule_card)
        schedule_label = QLabel("<b>Schedule</b>")
        schedule_label.setFont(QFont("Arial", 12, QFont.Bold))
        schedule_layout.addWidget(schedule_label)
        cal = QCalendarWidget()
        cal.setFixedHeight(120)
        schedule_layout.addWidget(cal)
        grid.addWidget(schedule_card, 2, 0)
        # --- Issue Found Card ---
        issue_card = QFrame()
        issue_card.setStyleSheet("background: white; border-radius: 18px;")
        issue_layout = QVBoxLayout(issue_card)
        issue_label = QLabel("<b>Issue Found</b>")
        issue_label.setFont(QFont("Arial", 12, QFont.Bold))
        issue_layout.addWidget(issue_label)
        issues_box = QTextEdit()
        issues_box.setReadOnly(True)
        issues_box.setText("Osteoporosis    Bisphosphonate drugs")
        issues_box.setStyleSheet("background: #f7f7f7; border: none; font-size: 12px;")
        issues_box.setMinimumHeight(60)
        issue_layout.addWidget(issues_box)
        grid.addWidget(issue_card, 2, 1, 1, 2)
        main_layout.addLayout(grid)
