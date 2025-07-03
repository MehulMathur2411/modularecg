from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QPushButton, QWidget, QLabel
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from PyQt5.QtCore import QTimer, Qt

class ECGRecording:
    def __init__(self):
        self.recording = False
        self.data = []

    def start_recording(self):
        self.recording = True
        self.data = []  # Reset data for new recording
        # Code to start ECG data acquisition would go here

    def stop_recording(self):
        self.recording = False
        # Code to stop ECG data acquisition would go here

    def save_recording(self, filename):
        if not self.recording and self.data:
            # Code to save self.data to a file with the given filename
            pass
        else:
            raise Exception("Recording is still in progress or no data to save.")
        
class Lead12BlackPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: black;")
        layout = QVBoxLayout(self)
        self.canvases = []
        self.lines = []
        self.data = [np.zeros(500) for _ in range(12)]
        self.lead_names = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]
        for i in range(12):
            row = QVBoxLayout()
            # Label above the wave
            label = QLabel(self.lead_names[i])
            label.setStyleSheet("color: white; font-size: 14px; font-weight: bold; margin-bottom: 2px;")
            label.setFixedWidth(70)
            layout.addWidget(label, alignment=Qt.AlignLeft)
            fig = Figure(figsize=(2, 2), facecolor='black')
            ax = fig.add_subplot(111)
            ax.set_facecolor('black')
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_ylim(-3, 3)
            # Draw vertical line at x=0
            ax.axvline(x=0, color='white', linestyle='--', linewidth=1)
            ax.set_title("", color='white', fontsize=12, loc='left')
            # Plot ECG
            line, = ax.plot(self.data[i], color='lime', lw=1)
            canvas = FigureCanvas(fig)
            layout.addWidget(canvas)
            self.canvases.append(canvas)
            self.lines.append(line)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(30)  # ~33 FPS

    def update_data(self):
        # Replace this with real ECG data in production
        for i in range(12):
            self.data[i] = np.roll(self.data[i], -1)
            self.data[i][-1] = 1.5 * np.sin(np.linspace(0, 2 * np.pi, 500)[(self.data[i].size-1)%500]) + 0.2 * np.random.randn()
            self.lines[i].set_ydata(self.data[i])
            self.canvases[i].draw()

class ECGMenu(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Menu", parent)
        self.setStyleSheet("QGroupBox { font: bold 14pt Arial; background-color: #fff; border-radius: 10px; }")
        layout = QVBoxLayout(self)
        self.buttons = {}
        menu_buttons = [
            ("Save ECG", self.on_save_ecg),
            ("Open ECG", self.on_open_ecg),
            ("Working Mode", self.on_working_mode),
            ("Printer Setup", self.on_printer_setup),
            ("Set Filter", self.on_set_filter),
            ("System Setup", self.on_system_setup),
            ("Load Default", self.on_load_default),
            ("Version", self.on_version_info),
            ("Factory Maintain", self.on_factory_maintain),
            ("12:1", self.on_12to1), 
            ("Exit", self.on_exit)
        ]
        for text, handler in menu_buttons:
            btn = QPushButton(text)
            btn.setFixedHeight(36)
            btn.clicked.connect(handler)
            layout.addWidget(btn)
            self.buttons[text] = btn
        layout.addStretch(1)

    # Placeholder methods to be connected externally
    def on_save_ecg(self):
        pass
    def on_open_ecg(self):
        pass
    def on_working_mode(self):
        pass
    def on_printer_setup(self):
        pass
    def on_set_filter(self):
        pass
    def on_system_setup(self):
        pass
    def on_load_default(self):
        pass
    def on_version_info(self):
        pass
    def on_factory_maintain(self):
        pass
    def on_12to1(self):
        self.lead12_window = Lead12BlackPage()
        self.lead12_window.setWindowTitle("12:1 ECG Leads")
        self.lead12_window.resize(1600, 300)
        self.lead12_window.show()
    def on_exit(self):
        pass