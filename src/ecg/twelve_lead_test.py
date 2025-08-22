import sys
import time
import numpy as np
from pyparsing import line
import serial
import serial.tools.list_ports
import csv
import cv2
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QGroupBox, QFileDialog,
    QStackedLayout, QGridLayout, QSizePolicy, QMessageBox, QFormLayout, QLineEdit, QFrame, QApplication
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QDateTime
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from ecg.recording import ECGMenu
from scipy.signal import find_peaks
from utils.settings_manager import SettingsManager

class SerialECGReader:
    def __init__(self, port, baudrate):
        self.ser = serial.Serial(port, baudrate, timeout=1)
        self.running = False

    def start(self):
        self.ser.reset_input_buffer()
        self.ser.write(b'1\r\n')
        time.sleep(0.5)
        self.running = True

    def stop(self):
        self.ser.write(b'0\r\n')
        self.running = False

    def read_value(self):
        if not self.running:
            return None
        try:
            line_raw = self.ser.readline()
            line_data = line_raw.decode('utf-8', errors='replace').strip()
            if line_data:
                print("Received:", line_data)
            if line_data.isdigit():
                return int(line_data[-3:])
        except Exception as e:
            print("Error:", e)
        return None

    def close(self):
        self.ser.close()

class LiveLeadWindow(QWidget):
    def __init__(self, lead_name, data_source, buffer_size=80, color="#00ff99"):
        super().__init__()
        self.setWindowTitle(f"Live View: {lead_name}")
        self.resize(900, 300)
        self.lead_name = lead_name
        self.data_source = data_source
        self.buffer_size = buffer_size
        self.color = color

        layout = QVBoxLayout(self)
        self.fig = Figure(facecolor='#000')
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#000')
        self.ax.set_ylim(-400, 400)
        self.ax.set_xlim(0, buffer_size)
        self.line, = self.ax.plot([0]*buffer_size, color=self.color, lw=2)
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(100)

    def update_plot(self):
        data = self.data_source()
        if data and len(data) > 0:
            plot_data = np.full(self.buffer_size, np.nan)
            n = min(len(data), self.buffer_size)
            centered = np.array(data[-n:]) - np.mean(data[-n:])
            plot_data[-n:] = centered
            self.line.set_ydata(plot_data)
            self.canvas.draw_idle()

# ------------------------ Calculate QRS axis ------------------------

def calculate_qrs_axis(lead_I, lead_aVF, r_peaks, fs=500, window_ms=100):
    """
    Calculate QRS axis using net area of QRS complex around R peaks.
    - lead_I, lead_aVF: arrays of samples
    - r_peaks: indices of R peaks
    - fs: sampling rate
    - window_ms: window size around R peak (default 100 ms)
    """
    if len(lead_I) < 100 or len(lead_aVF) < 100 or len(r_peaks) == 0:
        return "--"
    window = int(window_ms * fs / 1000)
    net_I = []
    net_aVF = []
    for r in r_peaks:
        start = max(0, r - window//2)
        end = min(len(lead_I), r + window//2)
        net_I.append(np.sum(lead_I[start:end]))
        net_aVF.append(np.sum(lead_aVF[start:end]))
    mean_net_I = np.mean(net_I)
    mean_net_aVF = np.mean(net_aVF)
    axis_rad = np.arctan2(mean_net_aVF, mean_net_I)
    axis_deg = int(np.degrees(axis_rad))
    return axis_deg

# ------------------------ Calculate ST Segment ------------------------

def calculate_st_segment(lead_signal, r_peaks, fs=500, j_offset_ms=40, st_offset_ms=80):
    """
    Calculate mean ST segment amplitude (in mV) at (J-point + st_offset_ms) after R peak.
    - lead_signal: ECG samples (e.g., Lead II)
    - r_peaks: indices of R peaks
    - fs: sampling rate (Hz)
    - j_offset_ms: ms after R peak to estimate J-point (default 40ms)
    - st_offset_ms: ms after J-point to measure ST segment (default 80ms)
    Returns mean ST segment amplitude in mV (float), or '--' if not enough data.
    """
    if len(lead_signal) < 100 or len(r_peaks) == 0:
        return "--"
    st_values = []
    j_offset = int(j_offset_ms * fs / 1000)
    st_offset = int(st_offset_ms * fs / 1000)
    for r in r_peaks:
        st_idx = r + j_offset + st_offset
        if st_idx < len(lead_signal):
            st_values.append(lead_signal[st_idx])
    if len(st_values) == 0:
        return "--"
    
    st_value = float(np.mean(st_values))
    # Interpret as medical term
    if 80 <= st_value <= 120:
        return "Isoelectric"
    elif st_value > 120:
        return "Elevated"
    elif st_value < 80:
        return "Depressed"
    return str(st_value)

# ------------------------ Calculate Arrhythmia ------------------------

def detect_arrhythmia(heart_rate, qrs_duration, rr_intervals, pr_interval=None, p_peaks=None, r_peaks=None, ecg_signal=None):
    """
    Expanded arrhythmia detection logic for common clinical arrhythmias.
    - Sinus Bradycardia: HR < 60, regular RR
    - Sinus Tachycardia: HR > 100, regular RR
    - Atrial Fibrillation: Irregular RR, absent/irregular P waves
    - Atrial Flutter: Sawtooth P pattern (not robustly detected here)
    - PAC: Early P, narrow QRS, compensatory pause (approximate)
    - PVC: Early wide QRS, no P, compensatory pause (approximate)
    - VT: HR > 100, wide QRS (>120ms), regular
    - VF: Chaotic, no clear QRS, highly irregular
    - Asystole: Flatline (very low amplitude, no R)
    - SVT: HR > 150, narrow QRS, regular
    - Heart Block: PR > 200 (1°), dropped QRS (2°), AV dissociation (3°)
    """
    try:
        if rr_intervals is None or len(rr_intervals) < 2:
            return "Detecting..."
        rr_std = np.std(rr_intervals)
        rr_mean = np.mean(rr_intervals)
        rr_reg = rr_std < 0.12  # Regular if std < 120ms
        # Asystole: flatline (no R peaks, or very low amplitude)
        if r_peaks is not None and len(r_peaks) < 1:
            if ecg_signal is not None and np.ptp(ecg_signal) < 50:
                return "Asystole (Flatline)"
            return "No QRS Detected"
        # VF: highly irregular, no clear QRS, rapid undulating
        if r_peaks is not None and len(r_peaks) > 5:
            if rr_std > 0.25 and np.ptp(ecg_signal) > 100 and heart_rate and heart_rate > 180:
                return "Ventricular Fibrillation (VF)"
        # VT: HR > 100, wide QRS (>120ms), regular
        if heart_rate and heart_rate > 100 and qrs_duration and qrs_duration > 120 and rr_reg:
            return "Ventricular Tachycardia (VT)"
        # Sinus Bradycardia: HR < 60, regular
        if heart_rate and heart_rate < 60 and rr_reg:
            return "Sinus Bradycardia"
        # Sinus Tachycardia: HR > 100, regular
        if heart_rate and heart_rate > 100 and qrs_duration and qrs_duration <= 120 and rr_reg:
            return "Sinus Tachycardia"
        # SVT: HR > 150, narrow QRS, regular
        if heart_rate and heart_rate > 150 and qrs_duration and qrs_duration <= 120 and rr_reg:
            return "Supraventricular Tachycardia (SVT)"
        # AFib: Irregular RR, absent/irregular P
        if not rr_reg and (p_peaks is None or len(p_peaks) < len(r_peaks) * 0.5):
            return "Atrial Fibrillation (AFib)"
        # Atrial Flutter: (not robust, but if HR ~150, regular, and P waves rapid)
        if heart_rate and 140 < heart_rate < 170 and rr_reg and p_peaks is not None and len(p_peaks) > len(r_peaks):
            return "Atrial Flutter (suggestive)"
        # PAC: Early P, narrow QRS, compensatory pause (approximate)
        if p_peaks is not None and r_peaks is not None and len(p_peaks) > 1 and len(r_peaks) > 1:
            pr_diffs = np.diff([r - p for p, r in zip(p_peaks, r_peaks)])
            if np.any(pr_diffs < -0.15 * len(ecg_signal)) and qrs_duration and qrs_duration <= 120:
                return "Premature Atrial Contraction (PAC)"
        # PVC: Early wide QRS, no P, compensatory pause (approximate)
        if qrs_duration and qrs_duration > 120 and (p_peaks is None or len(p_peaks) < len(r_peaks) * 0.5):
            return "Premature Ventricular Contraction (PVC)"
        # Heart Block: PR > 200ms (1°), dropped QRS (2°), AV dissociation (3°)
        if pr_interval and pr_interval > 200:
            return "Heart Block (1° AV)"
        # If QRS complexes are missing (dropped beats)
        if r_peaks is not None and len(r_peaks) < len(ecg_signal) / 500 * heart_rate * 0.7:
            return "Heart Block (2°/3° AV, dropped QRS)"
        return "None Detected"
    except Exception as e:
        return "Detecting..."

class ECGTestPage(QWidget):
    LEADS_MAP = {
        "Lead II ECG Test": ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"],
        "Lead III ECG Test": ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"],
        "7 Lead ECG Test": ["V1", "V2", "V3", "V4", "V5", "V6", "II"],
        "12 Lead ECG Test": ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"],
        "ECG Live Monitoring": ["II"]
    }
    LEAD_COLORS = {
        "I": "#00ff99",
        "II": "#ff0055", 
        "III": "#0099ff",
        "aVR": "#ff9900",
        "aVL": "#cc00ff",
        "aVF": "#00ccff",
        "V1": "#ffcc00",
        "V2": "#00ffcc",
        "V3": "#ff6600",
        "V4": "#6600ff",
        "V5": "#00b894",
        "V6": "#ff0066"
    }
    def __init__(self, test_name, stacked_widget):
        super().__init__()
        self.setWindowTitle("12-Lead ECG Monitor")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.center_on_screen()
        self.stacked_widget = stacked_widget  # Save reference for navigation

        self.settings_manager = SettingsManager()

        self.grid_widget = QWidget()
        self.detailed_widget = QWidget()
        self.page_stack = QStackedLayout()
        self.page_stack.addWidget(self.grid_widget)
        self.page_stack.addWidget(self.detailed_widget)
        self.setLayout(self.page_stack)

        self.test_name = test_name
        self.leads = self.LEADS_MAP[test_name]
        self.buffer_size = 2000  # Increased buffer size for all leads
        self.data = {lead: [] for lead in self.leads}
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.serial_reader = None
        self.stacked_widget = stacked_widget
        self.lines = []
        self.axs = []
        self.canvases = []

        # Initialize time tracking for elapsed time
        self.start_time = None
        self.elapsed_timer = QTimer()
        self.elapsed_timer.timeout.connect(self.update_elapsed_time)

        main_vbox = QVBoxLayout()

        menu_frame = QGroupBox("Menu")

        menu_frame.setStyleSheet("""
            QGroupBox {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #ffffff, stop:1 #f8f9fa);
                border: 2px solid #e9ecef;
                border-radius: 16px;
                margin-top: 12px;
                padding: 16px;
                font-weight: bold;
            }
            QGroupBox::title {
                color: #495057;
                font-size: 16px;
                font-weight: bold;
                padding: 8px;
            }
        """)

        # Enhanced Menu Panel
        menu_container = QWidget()
        menu_container.setFixedWidth(300)
        menu_container.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #ffffff, stop:1 #f8f9fa);
                border-right: 2px solid #e9ecef;
            }
        """)

        # Style menu buttons
        menu_layout = QVBoxLayout(menu_container)
        menu_layout.setContentsMargins(20, 20, 20, 20)
        menu_layout.setSpacing(12)
        
        # Header
        header_label = QLabel("ECG Control Panel")
        header_label.setStyleSheet("""
            QLabel {
                color: #ff6600;
                font-size: 24px;
                font-weight: bold;
                padding: 20px 0;
                border-bottom: 3px solid #ff6600;
                margin-bottom: 20px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #fff5f0, stop:1 #ffe0cc);
                border-radius: 10px;
            }
        """)
        header_label.setAlignment(Qt.AlignCenter)
        menu_layout.addWidget(header_label)

        # Create ECGMenu instance to use its methods
        self.ecg_menu = ECGMenu(parent=self, dashboard=self.stacked_widget.parent())

        self.ecg_menu.settings_manager = self.settings_manager

        # Initialize sliding panel for the ECG menu
        self.ecg_menu.sliding_panel = None
        self.ecg_menu.parent_widget = self

        self.ecg_menu.setVisible(False)
        self.ecg_menu.hide()
        
        if self.ecg_menu.parent():
            self.ecg_menu.setParent(None)

        self.ecg_menu.settings_changed_callback = self.on_settings_changed 

        self.apply_display_settings()

    
        menu_buttons = [
            ("Save ECG", self.ecg_menu.show_save_ecg, "#28a745"),
            ("Open ECG", self.ecg_menu.open_ecg_window, "#17a2b8"),
            ("Working Mode", self.ecg_menu.show_working_mode, "#6f42c1"),
            ("Printer Setup", self.ecg_menu.show_printer_setup, "#fd7e14"),
            ("Set Filter", self.ecg_menu.set_filter_setup, "#20c997"),
            ("System Setup", self.ecg_menu.show_system_setup, "#6c757d"),
            ("Load Default", self.ecg_menu.show_load_default, "#ffc107"),
            ("Version", self.ecg_menu.show_version_info, "#17a2b8"),
            ("Factory Maintain", self.ecg_menu.show_factory_maintain, "#dc3545"),
        ]
        
        # Create buttons and store them in a list
        created_buttons = []
        for text, handler, color in menu_buttons:
            btn = QPushButton(text)
            btn.setFixedHeight(77)
            btn.clicked.connect(handler)
            created_buttons.append(btn)
            menu_layout.addWidget(btn)

        menu_layout.addStretch(1)

        # Style menu buttons AFTER they're created
        for i, btn in enumerate(created_buttons):
            color = menu_buttons[i][2]
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:0 #ffffff, stop:1 #f8f9fa);
                    color: #1a1a1a;
                    border: 3px solid #e9ecef;
                    border-radius: 15px;
                    padding: 20px 30px;
                    font-size: 18px;
                    font-weight: bold;
                    text-align: left;
                    margin: 4px 0;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:0 #fff5f0, stop:1 #ffe0cc);
                    border: 4px solid {color};
                    color: {color};
                    transform: translateY(-3px);
                    box-shadow: 0 8px 25px rgba(255,102,0,0.5);
                }}
                QPushButton:pressed {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:0 #ffe0cc, stop:1 #ffcc99);
                    border: 4px solid {color};
                    color: {color};
                }}
            """)

        created_buttons[0].clicked.disconnect()
        created_buttons[0].clicked.connect(self.ecg_menu.show_save_ecg)
        
        created_buttons[1].clicked.disconnect()
        created_buttons[1].clicked.connect(self.ecg_menu.open_ecg_window)
        
        created_buttons[2].clicked.disconnect()
        created_buttons[2].clicked.connect(self.ecg_menu.show_working_mode)
        
        created_buttons[3].clicked.disconnect()
        created_buttons[3].clicked.connect(self.ecg_menu.show_printer_setup)
        
        created_buttons[4].clicked.disconnect()
        created_buttons[4].clicked.connect(self.ecg_menu.set_filter_setup)
        
        created_buttons[5].clicked.disconnect()
        created_buttons[5].clicked.connect(self.ecg_menu.show_system_setup)
        
        created_buttons[6].clicked.disconnect()
        created_buttons[6].clicked.connect(self.ecg_menu.show_load_default)
        
        created_buttons[7].clicked.disconnect()
        created_buttons[7].clicked.connect(self.ecg_menu.show_version_info)
        
        created_buttons[8].clicked.disconnect()
        created_buttons[8].clicked.connect(self.ecg_menu.show_factory_maintain)

        # Recording Toggle Button Section
        recording_frame = QFrame()
        recording_frame.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
                padding: 10px;
                margin-top: 5px;
            }
        """)

        recording_layout = QVBoxLayout(recording_frame)

        # Capture Screen button
        self.capture_screen_btn = QPushButton("Capture Screen")
        self.capture_screen_btn.setFixedHeight(77)
        self.capture_screen_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #ffffff, stop:1 #f8f9fa);
                color: #1a1a1a;
                border: 3px solid #e9ecef;
                border-radius: 15px;
                padding: 20px 30px;
                font-size: 18px;
                font-weight: bold;
                text-align: center;
                margin: 5px 0;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #fff5f0, stop:1 #ffe0cc);
                border: 4px solid #2453ff;
                color: #2453ff;
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(36,83,255,0.5);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #e0e8ff, stop:1 #ccd9ff);
                border: 4px solid #2453ff;
                color: #2453ff;
            }
        """)
        self.capture_screen_btn.clicked.connect(self.capture_screen)
        recording_layout.addWidget(self.capture_screen_btn)
        
        # Toggle-style recording button
        self.recording_toggle = QPushButton("Record Screen")
        self.recording_toggle.setFixedHeight(77)
        self.recording_toggle.setCheckable(True)
        self.recording_toggle.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #ffffff, stop:1 #f8f9fa);
                color: #1a1a1a;
                border: 3px solid #e9ecef;
                border-radius: 15px;
                padding: 20px 30px;
                font-size: 18px;
                font-weight: bold;
                text-align: center;
                margin: 5px 0;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #fff5f0, stop:1 #ffe0cc);
                border: 4px solid #ff6600;
                color: #ff6600;
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(255,102,0,0.5);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #ffe0cc, stop:1 #ffcc99);
                border: 4px solid #ff6600;
                color: #ff6600;
            }
            QPushButton:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #fff5f0, stop:1 #ffe0cc);
                border: 4px solid #dc3545;
                color: #dc3545;
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(220,53,69,0.5);
            }
            QPushButton:checked:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #ffe0cc, stop:1 #ffcc99);
                border: 4px solid #c82333;
                color: #c82333;
            }
        """)
        self.recording_toggle.clicked.connect(self.toggle_recording)
        recording_layout.addWidget(self.recording_toggle)
        
        menu_layout.addWidget(recording_frame)
        
        # Initialize recording variables
        self.is_recording = False
        self.recording_writer = None
        self.recording_frames = []


        # conn_layout = QHBoxLayout()
        # self.port_combo = QComboBox()
        # self.baud_combo = QComboBox()
        # self.baud_combo.addItem("Select Baud Rate")
        # self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        # conn_layout.addWidget(QLabel("Serial Port:"))
        # conn_layout.addWidget(self.port_combo)
        # conn_layout.addWidget(QLabel("Baud Rate:"))
        # conn_layout.addWidget(self.baud_combo)
        # self.refresh_ports()
        # main_vbox.addLayout(conn_layout)

        self.plot_area = QWidget()

        # Add metrics frame above the plot area
        self.metrics_frame = self.create_metrics_frame()
        main_vbox.addWidget(self.metrics_frame)

        main_vbox.addWidget(self.plot_area)

        main_vbox.setSpacing(16)
        main_vbox.setContentsMargins(24, 24, 24, 24)

        self.update_lead_layout()

        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.export_pdf_btn = QPushButton("Export as PDF")
        self.export_csv_btn = QPushButton("Export as CSV")
        self.back_btn = QPushButton("Back")
        self.ecg_plot_btn = QPushButton("Open ECG Live Plot")
        self.sequential_btn = QPushButton("Show All Leads Sequentially")
        self.twelve_leads_btn = QPushButton("12:1")
        self.six_leads_btn = QPushButton("6:2")

        green_color = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #4CAF50, stop:1 #45a049);
                color: white;
                border: 2px solid #4CAF50;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
                min-height: 32px;
                min-width: 100px;
                text-align: center;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #45a049, stop:1 #4CAF50);
                border: 2px solid #45a049;
                color: white;
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(76,175,80,0.3);
            }
            QPushButton:pressed {
                background: #3d8b40;
                border: 2px solid #3d8b40;
                transform: translateY(0px);
            }
        """
        
        # Apply medical green style to all buttons
        self.start_btn.setStyleSheet(green_color)
        self.stop_btn.setStyleSheet(green_color)
        self.export_pdf_btn.setStyleSheet(green_color)
        self.export_csv_btn.setStyleSheet(green_color)
        self.back_btn.setStyleSheet(green_color)
        self.ecg_plot_btn.setStyleSheet(green_color)
        self.sequential_btn.setStyleSheet(green_color)
        self.twelve_leads_btn.setStyleSheet(green_color)
        self.six_leads_btn.setStyleSheet(green_color)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.export_pdf_btn)
        btn_layout.addWidget(self.export_csv_btn)
        btn_layout.addWidget(self.back_btn)
        btn_layout.addWidget(self.ecg_plot_btn)
        btn_layout.addWidget(self.sequential_btn)
        btn_layout.addWidget(self.twelve_leads_btn)
        btn_layout.addWidget(self.six_leads_btn)
        main_vbox.addLayout(btn_layout)

        self.start_btn.clicked.connect(self.start_acquisition)
        self.stop_btn.clicked.connect(self.stop_acquisition)


        self.start_btn.setToolTip("Start ECG recording from the selected port")
        self.stop_btn.setToolTip("Stop current ECG recording")
        self.export_pdf_btn.setToolTip("Export ECG data as PDF report")
        self.export_csv_btn.setToolTip("Export ECG data as CSV file")

        # Add help button
        help_btn = QPushButton("?")
        help_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border-radius: 50%;
                width: 30px;
                height: 30px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #495057;
            }
        """)
        help_btn.clicked.connect(self.show_help)

        self.export_pdf_btn.clicked.connect(self.export_pdf)
        self.export_csv_btn.clicked.connect(self.export_csv)
        self.back_btn.clicked.connect(self.go_back)
        self.sequential_btn.clicked.connect(self.show_sequential_view)
        self.twelve_leads_btn.clicked.connect(self.twelve_leads_overlay)
        self.six_leads_btn.clicked.connect(self.six_leads_overlay)
        # self.ecg_plot_btn.clicked.connect(lambda: run_ecg_live_plot(port='/cu.usbserial-10', baudrate=9600, buffer_size=100))

        main_hbox = QHBoxLayout(self.grid_widget)
    
        # Add widgets to the layout
        main_hbox.addWidget(menu_container, 0)  # Fixed width for menu
        main_hbox.addLayout(main_vbox, 2)  # Give main_vbox more space
        
        # Set spacing and layout
        main_hbox.setSpacing(15)  # Add spacing between menu and main content
        self.grid_widget.setLayout(main_hbox)
        
        # Initial settings display update
        QTimer.singleShot(100, self.apply_display_settings)

    def on_settings_changed(self, key, value):
        
        print(f"Setting changed: {key} = {value}")
        
        if key in ["wave_speed", "wave_gain"]:
            # Apply new settings immediately
            self.apply_display_settings()
            
            # CRITICAL: Update all lead titles IMMEDIATELY
            self.update_all_lead_titles()
            
            # Force redraw of all plots
            self.redraw_all_plots()
            
            print(f"Settings applied and titles updated for {key} = {value}")

    def update_all_lead_titles(self):
        
        current_speed = self.settings_manager.get_wave_speed()
        current_gain = self.settings_manager.get_wave_gain()
        
        print(f"Updating titles: Speed={current_speed}mm/s, Gain={current_gain}mm/mV")
        
        for i, lead in enumerate(self.leads):
            if i < len(self.axs):
                new_title = f"{lead} | Speed: {current_speed}mm/s | Gain: {current_gain}mm/mV"
                self.axs[i].set_title(new_title, fontsize=8, color='#666', pad=10)
                print(f"Updated {lead} title: {new_title}")
        
        # Force redraw of all canvases
        for canvas in self.canvases:
            if canvas:
                canvas.draw_idle()

    def apply_display_settings(self):
        
        wave_speed = self.settings_manager.get_wave_speed()
        wave_gain = self.settings_manager.get_wave_gain()
        
        # Update buffer size based on wave speed
        # Higher speed = more samples per second = larger buffer for same time window
        base_buffer = 2000
        speed_factor = wave_speed / 50.0  # 50mm/s is baseline
        self.buffer_size = int(base_buffer * speed_factor)
        
        # Update y-axis limits based on gain
        # Higher gain = larger amplitude display
        base_ylim = 400
        gain_factor = wave_gain / 10.0  # 10mm/mV is baseline
        self.ylim = int(base_ylim * gain_factor)

        # Force immediate redraw of all plots with new settings
        self.redraw_all_plots()
        
        print(f"Applied settings: speed={wave_speed}mm/s, gain={wave_gain}mm/mV, buffer={self.buffer_size}, ylim={self.ylim}")

    # ------------------------ Update Dashboard Metrics on the top of the lead graphs ------------------------

    def create_metrics_frame(self):
        metrics_frame = QFrame()
        metrics_frame.setObjectName("metrics_frame")
        metrics_frame.setStyleSheet("""
            QFrame {
                background: #000000;
                border: 2px solid #333333;
                border-radius: 6px;
                padding: 4px;
                margin: 2px 0;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }
        """)
        
        metrics_layout = QHBoxLayout(metrics_frame)
        metrics_layout.setSpacing(10)
        metrics_layout.setContentsMargins(10, 10, 10, 10)
        
        # Store metric labels for live update
        self.metric_labels = {}
        
        # Updated metric info to match the image design
        metric_info = [
            ("PR Intervals (ms)", "--", "pr_interval", "#ff0000"),
            ("QRS Complex (ms)", "--", "qrs_duration", "#ffff00"),
            ("QRS Axis", "--", "qrs_axis", "#ffff00"),
            ("ST Interval", "--", "st_segment", "#0000ff"),
            ("Time Elapsed", "00:00", "time_elapsed", "#ffffff"),
        ]
        
        for title, value, key, color in metric_info:
            metric_widget = QWidget()
            metric_widget.setStyleSheet("""
                QWidget {
                    background: transparent;
                    min-width: 120px;
                    border-right: none;
                }
            """)
            
            # Create vertical layout for the metric widget
            box = QVBoxLayout(metric_widget)
            box.setSpacing(3)
            box.setAlignment(Qt.AlignCenter)
            
            # Title label (green color as shown in image)
            lbl = QLabel(title)
            lbl.setFont(QFont("Arial", 12, QFont.Bold))
            lbl.setStyleSheet("color: #00ff00; margin-bottom: 5px;")  # Green color
            lbl.setAlignment(Qt.AlignCenter)
            
            # Value label with specific colors
            val = QLabel(value)
            val.setFont(QFont("Arial", 14, QFont.Bold))
            val.setStyleSheet(f"color: {color}; background: transparent; padding: 4px 0px;")
            val.setAlignment(Qt.AlignCenter)
            
            # Add labels to the metric widget's layout
            box.addWidget(lbl)
            box.addWidget(val)
            
            # Add the metric widget to the horizontal layout
            metrics_layout.addWidget(metric_widget)
            
            # Store reference for live update
            self.metric_labels[key] = val
        
        heart_rate_widget = QWidget()
        heart_rate_widget.setStyleSheet("""
            QWidget {
                background: transparent;
                min-width: 120px;
                border-right: none;
            }
        """)
        
        heart_layout = QHBoxLayout(heart_rate_widget)
        heart_layout.setSpacing(2)
        heart_layout.setContentsMargins(0, 0, 0, 0)
        heart_layout.setAlignment(Qt.AlignCenter)
        
        # Heart icon
        heart_icon = QLabel("❤")
        heart_icon.setFont(QFont("Arial", 18))
        heart_icon.setStyleSheet("color: #ff0000; background: transparent; border: none; margin: 0; padding: 0;")
        heart_icon.setAlignment(Qt.AlignCenter)
        
        # Heart rate value
        heart_rate_val = QLabel("00")
        heart_rate_val.setFont(QFont("Arial", 14, QFont.Bold))
        heart_rate_val.setStyleSheet("color: #ff0000; background: transparent; border: none; margin: 0;")
        heart_rate_val.setAlignment(Qt.AlignCenter)
        heart_rate_val.setContentsMargins(0, 0, 0, 0)
        
        heart_layout.addWidget(heart_icon)
        heart_layout.addWidget(heart_rate_val)
        
        # Insert heart rate widget at the beginning
        metrics_layout.insertWidget(0, heart_rate_widget)
        self.metric_labels['heart_rate'] = heart_rate_val
        
        return metrics_frame

    def update_ecg_metrics_on_top_of_lead_graphs(self, intervals):
        if 'Heart_Rate' in intervals and intervals['Heart_Rate'] is not None:
            self.metric_labels['heart_rate'].setText(
                f"{int(round(intervals['Heart_Rate']))}" if isinstance(intervals['Heart_Rate'], (int, float)) else str(intervals['Heart_Rate'])
            )
        
        if 'PR' in intervals and intervals['PR'] is not None:
            self.metric_labels['pr_interval'].setText(
                f"{int(round(intervals['PR']))}" if isinstance(intervals['PR'], (int, float)) else str(intervals['PR'])
            )
        
        if 'QRS' in intervals and intervals['QRS'] is not None:
            self.metric_labels['qrs_duration'].setText(
                f"{int(round(intervals['QRS']))}" if isinstance(intervals['QRS'], (int, float)) else str(intervals['QRS'])
            )
        
        if 'QRS_axis' in intervals and intervals['QRS_axis'] is not None:
            self.metric_labels['qrs_axis'].setText(str(intervals['QRS_axis']))
        
        if 'ST' in intervals and intervals['ST'] is not None:
            self.metric_labels['st_segment'].setText(
                f"{int(round(intervals['ST']))}" if isinstance(intervals['ST'], (int, float)) else str(intervals['ST'])
            )
        
        if 'time_elapsed' in self.metric_labels:
            # Time elapsed will be updated separately by a timer
            pass

    def update_metrics_frame_theme(self, dark_mode=False, medical_mode=False):
       
        if not hasattr(self, 'metrics_frame'):
            return
            
        if dark_mode:
            # Dark mode styling
            self.metrics_frame.setStyleSheet("""
                QFrame#metrics_frame {
                    background: #000000;
                    border: 2px solid #333333;
                    border-radius: 6px;
                    padding: 4px;
                    margin: 2px 0;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
                }
            """)
            
            # Update text colors for dark mode
            for key, label in self.metric_labels.items():
                if key == 'heart_rate':
                    label.setStyleSheet("color: #ff0000; background: transparent; padding: 0; border: none; margin: 0;")
                elif key == 'pr_interval':
                    label.setStyleSheet("color: #ff0000; background: transparent; padding: 4px 0px; border: none;")
                elif key == 'qrs_duration':
                    label.setStyleSheet("color: #ffff00; background: transparent; padding: 4px 0px; border: none;")
                elif key == 'qrs_axis':
                    label.setStyleSheet("color: #ffff00; background: transparent; padding: 4px 0px; border: none;")
                elif key == 'st_segment':
                    label.setStyleSheet("color: #0000ff; background: transparent; padding: 4px 0px; border: none;")
                elif key == 'time_elapsed':
                    label.setStyleSheet("color: #ffffff; background: transparent; padding: 4px 0px; border: none;")
            
            # Update title colors to green for dark mode
            for child in self.metrics_frame.findChildren(QLabel):
                if child != self.metric_labels.get('heart_rate') and child != self.metric_labels.get('time_elapsed'):
                    if not any(child == label for label in self.metric_labels.values()):
                        child.setStyleSheet("color: #00ff00; margin-bottom: 5px; border: none;")
                        
        elif medical_mode:
            # Medical mode styling (green theme)
            self.metrics_frame.setStyleSheet("""
                QFrame#metrics_frame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                        stop:0 #f0fff0, stop:1 #e0f0e0);
                    border: 2px solid #4CAF50;
                    border-radius: 6px;
                    padding: 4px;
                    margin: 2px 0;
                    box-shadow: 0 4px 15px rgba(76,175,80,0.2);
                }
            """)
            
            # Update text colors for medical mode
            for key, label in self.metric_labels.items():
                if key == 'heart_rate':
                    label.setStyleSheet("color: #d32f2f; background: transparent; padding: 0; border: none; margin: 0;")
                elif key == 'pr_interval':
                    label.setStyleSheet("color: #d32f2f; background: transparent; padding: 4px 0px; border: none;")
                elif key == 'qrs_duration':
                    label.setStyleSheet("color: #f57c00; background: transparent; padding: 4px 0px; border: none;")
                elif key == 'qrs_axis':
                    label.setStyleSheet("color: #f57c00; background: transparent; padding: 4px 0px; border: none;")
                elif key == 'st_segment':
                    label.setStyleSheet("color: #1976d2; background: transparent; padding: 4px 0px; border: none;")
                elif key == 'time_elapsed':
                    label.setStyleSheet("color: #388e3c; background: transparent; padding: 4px 0px; border: none;")
            
            # Update title colors to dark green for medical mode
            for child in self.metrics_frame.findChildren(QLabel):
                if child != self.metric_labels.get('heart_rate') and child != self.metric_labels.get('time_elapsed'):
                    if not any(child == label for label in self.metric_labels.values()):
                        child.setStyleSheet("color: #2e7d32; margin-bottom: 5px; border: none;")
                        
        else:
            # Light mode (default) styling
            self.metrics_frame.setStyleSheet("""
                QFrame#metrics_frame {
                    background: #ffffff;
                    border: 2px solid #e0e0e0;
                    border-radius: 6px;
                    padding: 4px;
                    margin: 2px 0;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                }
            """)
            
            # Update text colors for light mode
            for key, label in self.metric_labels.items():
                if key == 'heart_rate':
                    label.setStyleSheet("color: #ff0000; background: transparent; padding: 0; border: none; margin: 0;")
                elif key == 'pr_interval':
                    label.setStyleSheet("color: #ff0000; background: transparent; padding: 4px 0px; border: none;")
                elif key == 'qrs_duration':
                    label.setStyleSheet("color: #ff8f00; background: transparent; padding: 4px 0px; border: none;")
                elif key == 'qrs_axis':
                    label.setStyleSheet("color: #ff8f00; background: transparent; padding: 4px 0px; border: none;")
                elif key == 'st_segment':
                    label.setStyleSheet("color: #1976d2; background: transparent; padding: 4px 0px; border: none;")
                elif key == 'time_elapsed':
                    label.setStyleSheet("color: #424242; background: transparent; padding: 4px 0px; border: none;")
            
            # Update title colors to dark gray for light mode
            for child in self.metrics_frame.findChildren(QLabel):
                if child != self.metric_labels.get('heart_rate') and child != self.metric_labels.get('time_elapsed'):
                    if not any(child == label for label in self.metric_labels.values()):
                        child.setStyleSheet("color: #666; margin-bottom: 5px; border: none;")

    def update_elapsed_time(self):
        
        if self.start_time and 'time_elapsed' in self.metric_labels:
            elapsed = time.time() - self.start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            self.metric_labels['time_elapsed'].setText(f"{minutes:02d}:{seconds:02d}")

    # ------------------------ Calculate ECG Intervals ------------------------

    def calculate_ecg_intervals(self, lead_ii_data):
        if not lead_ii_data or len(lead_ii_data) < 100:
            return {}
        
        try:
            from ecg.pan_tompkins import pan_tompkins
            
            # Convert to numpy array
            data = np.array(lead_ii_data)
            
            # Detect R peaks using Pan-Tompkins algorithm
            r_peaks = pan_tompkins(data, fs=500)  # 500Hz sampling rate
            
            if len(r_peaks) < 2:
                return {}
            
            # Calculate heart rate
            rr_intervals = np.diff(r_peaks) / 500.0  # Convert to seconds
            mean_rr = np.mean(rr_intervals)
            heart_rate = 60 / mean_rr if mean_rr > 0 else 0
            
            # Calculate intervals
            pr_interval = 0.16  
            qrs_duration = 0.08  
            qt_interval = 0.4    
            qtc_interval = 0.42  
            qrs_axis = "--"      
            st_segment = 0.12    
            
            return {
                'Heart_Rate': heart_rate,
                'PR': pr_interval * 1000,  # Convert to ms
                'QRS': qrs_duration * 1000,
                'QT': qt_interval * 1000,
                'QTc': qtc_interval * 1000,
                'QRS_axis': qrs_axis,
                'ST': st_segment * 1000
            }
            
        except Exception as e:
            print(f"Error calculating ECG intervals: {e}")
            return {}

    # ------------------------ Show help dialog ------------------------

    def show_help(self):
        help_text = """
        <h3>12-Lead ECG Monitor Help</h3>
        <p><b>Getting Started:</b></p>
        <ul>
        <li>Configure serial port and baud rate in System Setup</li>
        <li>Click 'Start' to begin recording</li>
        <li>Click on any lead to view it in detail</li>
        <li>Use the menu options for additional features</li>
        </ul>
        <p><b>Features:</b></p>
        <ul>
        <li>Real-time 12-lead ECG monitoring</li>
        <li>Export data as PDF or CSV</li>
        <li>Detailed lead analysis</li>
        <li>Arrhythmia detection</li>
        </ul>
        """
        msg = QMessageBox(self)
        msg.setWindowTitle("Help - 12-Lead ECG Monitor")
        msg.setText(help_text)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    # ------------------------ Capture Screen Details ------------------------

    def capture_screen(self):
        try:
            
            # Get the main window
            main_window = self.window()
            
            # Create a timer to delay the capture slightly to ensure UI is ready
            def delayed_capture():
                # Capture the entire window
                pixmap = main_window.grab()
                
                # Show save dialog
                filename, _ = QFileDialog.getSaveFileName(
                    self, 
                    "Save Screenshot", 
                    f"ECG_Screenshot_{QDateTime.currentDateTime().toString('yyyy-MM-dd_hh-mm-ss')}.png",
                    "PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*)"
                )
                
                if filename:
                    # Save the screenshot
                    if pixmap.save(filename):
                        QMessageBox.information(
                            self, 
                            "Success", 
                            f"Screenshot saved successfully!\nLocation: {filename}"
                        )
                    else:
                        QMessageBox.warning(
                            self, 
                            "Error", 
                            "Failed to save screenshot."
                        )
            
            # Use a short delay to ensure the UI is fully rendered
            QTimer.singleShot(100, delayed_capture)
            
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Error", 
                f"Failed to capture screenshot: {str(e)}"
            )

    # ------------------------ Recording Details ------------------------

    def toggle_recording(self):
        if self.recording_toggle.isChecked():
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        try:
            # Initialize recording
            self.is_recording = True
            
            # Update UI - only change button text, no status updates
            self.recording_toggle.setText("STOP")
            
            # Start capture timer
            self.recording_timer = QTimer()
            self.recording_timer.timeout.connect(self.capture_frame)
            self.recording_timer.start(33)  # ~30 FPS
            
        except Exception as e:
            QMessageBox.warning(self, "Recording Error", f"Failed to start recording: {str(e)}")
            self.is_recording = False
            self.recording_toggle.setChecked(False)
    
    def stop_recording(self):
        try:
            # Stop recording
            self.is_recording = False
            if hasattr(self, 'recording_timer'):
                self.recording_timer.stop()
            
            # Update UI - only change button text, no status updates
            self.recording_toggle.setText("RECORD")
            
            # Ask user if they want to save the recording
            if len(self.recording_frames) > 0:
                reply = QMessageBox.question(
                    self, 
                    "Save Recording", 
                    "Would you like to save the recording?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self.save_recording()
                else:
                    # Discard recording
                    self.recording_frames.clear()
                    QMessageBox.information(self, "Recording Discarded", "Recording has been discarded.")
            
        except Exception as e:
            QMessageBox.warning(self, "Recording Error", f"Failed to stop recording: {str(e)}")
            self.recording_toggle.setChecked(True)

    def capture_frame(self):
        try:
            if self.is_recording:
                # Capture the current window
                screen = QApplication.primaryScreen()
                pixmap = screen.grabWindow(self.winId())
                
                # Convert to numpy array for OpenCV
                image = pixmap.toImage()
                width = image.width()
                height = image.height()
                ptr = image.bits()
                ptr.setsize(height * width * 4)
                arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
                arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
                
                # Store frame
                self.recording_frames.append(arr)
                
        except Exception as e:
            print(f"Frame capture error: {e}")
    
    def save_recording(self):
        try:
            if len(self.recording_frames) == 0:
                QMessageBox.warning(self, "No Recording", "No frames to save.")
                return
            
            # Get save file path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"ecg_recording_{timestamp}.mp4"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Recording",
                default_filename,
                "MP4 Files (*.mp4);;AVI Files (*.avi);;All Files (*)"
            )
            
            if file_path:
                # Get video dimensions from first frame
                height, width = self.recording_frames[0].shape[:2]
                
                # Create video writer
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(file_path, fourcc, 30.0, (width, height))
                
                # Write frames
                for frame in self.recording_frames:
                    out.write(frame)
                
                out.release()
                
                # Clear frames
                self.recording_frames.clear()
                
                QMessageBox.information(
                    self, 
                    "Recording Saved", 
                    f"Recording saved successfully to:\n{file_path}"
                )
            else:
                # User cancelled save
                self.recording_frames.clear()
                QMessageBox.information(self, "Recording Cancelled", "Recording was not saved.")
                
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Failed to save recording: {str(e)}")
            self.recording_frames.clear()

    # ------------------------ Get lead figure in pdf ------------------------

    def get_lead_figure(self, lead):
        if hasattr(self, "lead_figures"):
            return self.lead_figures.get(lead)

        ordered_leads = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]
        if hasattr(self, "figures"):
            if lead in ordered_leads:
                idx = ordered_leads.index(lead)
                if idx < len(self.figures):
                    return self.figures[idx]
        return None

    def center_on_screen(self):
        qr = self.frameGeometry()
        from PyQt5.QtWidgets import QApplication
        cp = QApplication.desktop().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def expand_lead(self, idx):
        lead = self.leads[idx]
        def get_lead_data():
            return self.data[lead]
        color = self.LEAD_COLORS.get(lead, "#00ff99")
        if hasattr(self, '_detailed_timer') and self._detailed_timer is not None:
            self._detailed_timer.stop()
            self._detailed_timer.deleteLater()
            self._detailed_timer = None
        old_layout = self.detailed_widget.layout()
        if old_layout is not None:
            while old_layout.count():
                item = old_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
            QWidget().setLayout(old_layout)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        back_btn = QPushButton("Back")
        back_btn.setFixedHeight(40)
        back_btn.clicked.connect(lambda: self.page_stack.setCurrentIndex(0))
        layout.addWidget(back_btn, alignment=Qt.AlignLeft)
        fig = Figure(facecolor='#fff')  # White background for the figure
        ax = fig.add_subplot(111)
        ax.set_facecolor('#fff')        # White background for the axes
        line, = ax.plot([], [], color=color, lw=2)
        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(canvas)
        # Create metric labels for cards
        pr_label = QLabel("-- ms")
        qrs_label = QLabel("-- ms")
        qtc_label = QLabel("-- ms")
        arrhythmia_label = QLabel("--")
        # Add metrics card row below the plot (card style)
        metrics_row = QHBoxLayout()
        def create_metric_card(title, label_widget):
            card = QFrame()
            card.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #fff7f0, stop:1 #ffe0cc);
                border-radius: 32px;
                border: 2.5px solid #ff6600;
                padding: 18px 18px;
            """)
            vbox = QVBoxLayout(card)
            vbox.setSpacing(6)
            lbl = QLabel(title)
            lbl.setAlignment(Qt.AlignHCenter)
            lbl.setStyleSheet("color: #ff6600; font-size: 18px; font-weight: bold;")
            label_widget.setStyleSheet("font-size: 32px; font-weight: bold; color: #222; padding: 8px 0;")
            vbox.addWidget(lbl)
            vbox.addWidget(label_widget)
            vbox.setAlignment(Qt.AlignHCenter)
            return card
        metrics_row.setSpacing(32)
        metrics_row.setContentsMargins(32, 16, 32, 24)
        metrics_row.setAlignment(Qt.AlignHCenter)
        cards = [create_metric_card("PR Interval", pr_label),
                 create_metric_card("QRS Duration", qrs_label),
                 create_metric_card("QTc Interval", qtc_label),
                 create_metric_card("Arrhythmia", arrhythmia_label)]
        for card in cards:
            card.setMinimumWidth(0)
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            metrics_row.addWidget(card)
        layout.addLayout(metrics_row)
        self.detailed_widget.setLayout(layout)
        self.detailed_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.page_stack.setCurrentIndex(1)
        self._detailed_timer = QTimer(self)

        def update_detailed_plot():
            detailed_buffer_size = 500  # Reduced to 500 samples for real-time effect
            data = get_lead_data()

            current_gain = self.settings_manager.get_wave_gain()
            current_speed = self.settings_manager.get_wave_speed()

            # Robust: Only plot if enough data, else show blank
            if data and len(data) >= 10:
                plot_data = np.array(data[-detailed_buffer_size:])
                x = np.arange(len(plot_data))
                centered = plot_data - np.mean(plot_data)

                # Apply current gain setting
                gain_factor = float(current_gain) / 10.0
                centered = centered * gain_factor

                line.set_data(x, centered)
                ax.set_xlim(0, max(len(centered)-1, 1))
                
                ylim = 500 * gain_factor
                ymin = np.min(centered) - ylim * 0.2
                ymax = np.max(centered) + ylim * 0.2
                if ymin == ymax:
                    ymin, ymax = -ylim, ylim
                ax.set_ylim(ymin, ymax)

                # --- PQRST detection and green labeling for Lead II only ---
                # Remove all extra lines except the main ECG line (robust for all Matplotlib versions)
                try:
                    while len(ax.lines) > 1:
                        ax.lines.remove(ax.lines[-1])
                except Exception as e:
                    print(f"Warning: Could not remove extra lines: {e}")
                for txt in list(ax.texts):
                    try:
                        txt.remove()
                    except Exception as e:
                        print(f"Warning: Could not remove text: {e}")
                # Optionally, clear all lines if you want only labels visible (no ECG trace):
                # ax.lines.clear()
                if lead == "II":
                    # Use the same detection logic as in main.py
                    from scipy.signal import find_peaks
                    sampling_rate = 80
                    ecg_signal = centered
                    window_size = min(500, len(ecg_signal))
                    if len(ecg_signal) > window_size:
                        ecg_signal = ecg_signal[-window_size:]
                        x = x[-window_size:]
                    # R peak detection
                    r_peaks, _ = find_peaks(ecg_signal, distance=int(0.2 * sampling_rate), prominence=0.6 * np.std(ecg_signal))
                    # Q and S: local minima before and after R
                    q_peaks = []
                    s_peaks = []
                    for r in r_peaks:
                        q_start = max(0, r - int(0.06 * sampling_rate))
                        q_end = r
                        if q_end > q_start:
                            q_idx = np.argmin(ecg_signal[q_start:q_end]) + q_start
                            q_peaks.append(q_idx)
                        s_start = r
                        s_end = min(len(ecg_signal), r + int(0.06 * sampling_rate))
                        if s_end > s_start:
                            s_idx = np.argmin(ecg_signal[s_start:s_end]) + s_start
                            s_peaks.append(s_idx)
                    # P: positive peak before Q (within 0.1-0.2s)
                    p_peaks = []
                    for q in q_peaks:
                        p_start = max(0, q - int(0.2 * sampling_rate))
                        p_end = q - int(0.08 * sampling_rate)
                        if p_end > p_start:
                            p_candidates, _ = find_peaks(ecg_signal[p_start:p_end], prominence=0.1 * np.std(ecg_signal))
                            if len(p_candidates) > 0:
                                p_peaks.append(p_start + p_candidates[-1])
                    # T: positive peak after S (within 0.1-0.4s)
                    t_peaks = []
                    for s in s_peaks:
                        t_start = s + int(0.08 * sampling_rate)
                        t_end = min(len(ecg_signal), s + int(0.4 * sampling_rate))
                        if t_end > t_start:
                            t_candidates, _ = find_peaks(ecg_signal[t_start:t_end], prominence=0.1 * np.std(ecg_signal))
                            if len(t_candidates) > 0:
                                t_peaks.append(t_start + t_candidates[np.argmax(ecg_signal[t_start + t_candidates])])
                    # Only show the most recent peak for each label (if any)
                    peak_dict = {'P': p_peaks, 'Q': q_peaks, 'R': r_peaks, 'S': s_peaks, 'T': t_peaks}
                    for label, idxs in peak_dict.items():
                        if len(idxs) > 0:
                            idx = idxs[-1]
                            ax.plot(idx, ecg_signal[idx], 'o', color='green', markersize=8, zorder=10)
                            y_offset = 0.12 * (np.max(ecg_signal) - np.min(ecg_signal))
                            if label in ['P', 'T']:
                                ax.text(idx, ecg_signal[idx]+y_offset, label, color='green', fontsize=12, fontweight='bold', ha='center', va='bottom', zorder=11, bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, boxstyle='round,pad=0.1'))
                            else:
                                ax.text(idx, ecg_signal[idx]-y_offset, label, color='green', fontsize=12, fontweight='bold', ha='center', va='top', zorder=11, bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, boxstyle='round,pad=0.1'))
                # --- Metrics (for Lead II only, based on R peaks) ---
                if lead == "II":
                    heart_rate = None
                    pr_interval = None
                    qrs_duration = None
                    qt_interval = None
                    qtc_interval = None
                    rr_intervals = None

                    if len(r_peaks) > 1:
                        rr_intervals = np.diff(r_peaks) / sampling_rate  # in seconds
                        mean_rr = np.mean(rr_intervals)
                        if mean_rr > 0:
                            heart_rate = 60 / mean_rr
                    if len(p_peaks) > 0 and len(r_peaks) > 0:
                        pr_interval = (r_peaks[-1] - p_peaks[-1]) * 1000 / sampling_rate  # ms
                    if len(q_peaks) > 0 and len(s_peaks) > 0:
                        qrs_duration = (s_peaks[-1] - q_peaks[-1]) * 1000 / sampling_rate  # ms
                    if len(q_peaks) > 0 and len(t_peaks) > 0:
                        qt_interval = (t_peaks[-1] - q_peaks[-1]) * 1000 / sampling_rate  # ms
                    if qt_interval and heart_rate:
                        qtc_interval = qt_interval / np.sqrt(60 / heart_rate)  # Bazett's formula

                    # Update ECG metrics labels with calculated values for Lead2 graph

                    if isinstance(pr_interval, (int, float)):
                        pr_label.setText(f"{int(round(pr_interval))} ms")
                    else:
                        pr_label.setText("-- ms")

                    if isinstance(qrs_duration, (int, float)):
                        qrs_label.setText(f"{int(round(qrs_duration))} ms")
                    else:
                        qrs_label.setText("-- ms")

                    if isinstance(qtc_interval, (int, float)) and qtc_interval >= 0:
                        qtc_label.setText(f"{int(round(qtc_interval))} ms")
                    else:
                        qtc_label.setText("-- ms")
                    
                    # Calculate QRS axis using Lead I and aVF
                    lead_I = self.data.get("I", [])
                    lead_aVF = self.data.get("aVF", [])
                    qrs_axis = calculate_qrs_axis(lead_I, lead_aVF, r_peaks)

                    # Calculate ST segment using Lead II and r_peaks
                    lead_ii = self.data.get("II", [])
                    st_segment = calculate_st_segment(lead_ii, r_peaks, fs=500)

                    if hasattr(self, 'dashboard_callback'):
                        self.dashboard_callback({
                            'Heart_Rate': heart_rate,
                            'PR': pr_interval,
                            'QRS': qrs_duration,
                            'QTc': qtc_interval,
                            'QRS_axis': qrs_axis,
                            'ST': st_segment
                        })

                    # --- Arrhythmia detection ---
                    arrhythmia_result = detect_arrhythmia(heart_rate, qrs_duration, rr_intervals)
                    arrhythmia_label.setText(arrhythmia_result)
                else:
                    pr_label.setText("-- ms")
                    qrs_label.setText("-- ms")
                    qtc_label.setText("-- ms")
                    arrhythmia_label.setText("--")
            else:
                line.set_data([], [])
                ax.set_xlim(0, 1)
                ax.set_ylim(-500, 500)
                pr_label.setText("-- ms")
                qrs_label.setText("-- ms")
                qtc_label.setText("-- ms")
            canvas.draw_idle()
        self._detailed_timer.timeout.connect(update_detailed_plot)
        self._detailed_timer.start(100)
        update_detailed_plot()  # Draw immediately on open

    def refresh_ports(self):
        self.port_combo.clear()
        self.port_combo.addItem("Select Port")
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(port.device)

    def update_lead_layout(self):
        old_layout = self.plot_area.layout()
        if old_layout:
            while old_layout.count():
                item = old_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.setParent(None)
            self.plot_area.setLayout(None)
        self.figures = []
        self.canvases = []
        self.axs = []
        self.lines = []
        grid = QGridLayout()
        n_leads = len(self.leads)
        if n_leads == 12:
            rows, cols = 3, 4
        elif n_leads == 7:
            rows, cols = 2, 4
        else:
            rows, cols = 1, 1
        for idx, lead in enumerate(self.leads):
            row, col = divmod(idx, cols)
            group = QGroupBox(lead)
            group.setStyleSheet("""
                QGroupBox {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                        stop:0 #ffffff, stop:1 #f8f9fa);
                    border: 2px solid #e9ecef;
                    border-radius: 16px;
                    color: #495057;
                    font: bold 16px 'Segoe UI';
                    margin-top: 12px;
                    padding: 12px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                }
                QGroupBox:hover {
                    border: 2px solid #ff6600;
                    box-shadow: 0 6px 20px rgba(255,102,0,0.2);
                    transform: translateY(-2px);
                }
            """)
            vbox = QVBoxLayout(group)
            fig = Figure(facecolor='#fafbfc', figsize=(6, 2.5))
            ax = fig.add_subplot(111)
            ax.set_facecolor('#fafbfc')
            ylim = self.ylim if hasattr(self, 'ylim') else 400
            ax.set_ylim(-ylim, ylim)
            ax.set_xlim(0, self.buffer_size)
            
            # Modern grid styling
            ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5, color='#e9ecef')
            ax.set_axisbelow(True)

            # Remove spines for cleaner look
            for spine in ax.spines.values():
                spine.set_visible(False)

            # Style ticks
            ax.tick_params(axis='both', colors='#6c757d', labelsize=10)
            ax.tick_params(axis='x', length=0)
            ax.tick_params(axis='y', length=0)

            # Enhanced line styling
            import matplotlib.patheffects as path_effects 
            line, = ax.plot([0]*self.buffer_size, 
                            color=self.LEAD_COLORS.get(lead, '#ff6600'), 
                            lw=0.5, 
                            alpha=0.9,
                            path_effects=[path_effects.SimpleLineShadow(offset=(1,1), alpha=0.3),
                                        path_effects.Normal()])

            self.lines.append(line)
            canvas = FigureCanvas(fig)
            vbox.addWidget(canvas)
            grid.addWidget(group, row, col)
            self.figures.append(fig)
            self.canvases.append(canvas)
            self.axs.append(ax)
        self.plot_area.setLayout(grid)
        def make_expand_lead(idx):
            return lambda event: self.expand_lead(idx)
        for i, canvas in enumerate(self.canvases):
            canvas.mpl_connect('button_press_event', make_expand_lead(i))

    def redraw_all_plots(self):
        
        if hasattr(self, 'lines') and self.lines:
            for i, line in enumerate(self.lines):
                if i < len(self.leads):
                    lead = self.leads[i]
                    data = self.data.get(lead, [])
                    
                    if len(data) > 0:
                        # Apply current settings to the real data
                        gain_factor = self.settings_manager.get_wave_gain() / 10.0
                        centered = (np.array(data) - np.nanmean(data)) * gain_factor
                        
                        # Update line data with new buffer size
                        if len(centered) < self.buffer_size:
                            plot_data = np.full(self.buffer_size, np.nan)
                            plot_data[-len(centered):] = centered
                        else:
                            plot_data = centered[-self.buffer_size:]
                        
                        line.set_ydata(plot_data)
                        
                        # Update axis limits based on current settings
                        if i < len(self.axs):
                            ylim = self.ylim if hasattr(self, 'ylim') else 400
                            self.axs[i].set_ylim(-ylim, ylim)
                            self.axs[i].set_xlim(0, self.buffer_size)
                            
                            # Update plot title with current settings
                            current_speed = self.settings_manager.get_wave_speed()
                            current_gain = self.settings_manager.get_wave_gain()
                            new_title = f"{lead} | Speed: {current_speed}mm/s | Gain: {current_gain}mm/mV"
                            self.axs[i].set_title(new_title, fontsize=8, color='#666', pad=10)
                            print(f"Redraw updated {lead} title: {new_title}")
                        
                        # Redraw canvas
                        if i < len(self.canvases):
                            self.canvases[i].draw_idle()

    # ---------------------- Start Button Functionality ----------------------

    def start_acquisition(self):
        port = self.settings_manager.get_serial_port()
        baud = self.settings_manager.get_baud_rate()

        print(f"Starting acquisition with Port: {port}, Baud: {baud}")

        if port == "Select Port" or baud == "Select Baud Rate" or port is None or baud is None:
            self.show_connection_warning("Please configure serial port and baud rate in System Setup first.")
            return
        
        try:
            # Convert baud rate to integer with error handling
            try:
                baud_int = int(baud)
            except (ValueError, TypeError):
                self.show_connection_warning(f"Invalid baud rate: {baud}. Please set a valid baud rate in System Setup.")
                return
            
            if self.serial_reader:
                self.serial_reader.close()
            
            print(f"Connecting to {port} at {baud_int} baud...")
            self.serial_reader = SerialECGReader(port, baud_int)
            self.serial_reader.start()
            self.timer.start(50)
            if hasattr(self, '_12to1_timer'):
                self._12to1_timer.start(100)

            # Start elapsed time tracking
            self.start_time = time.time()
            self.elapsed_timer.start(1000)
                
            print("Serial connection established successfully!")
            
        except Exception as e:
            error_msg = f"Failed to connect to {port} at {baud} baud: {str(e)}"
            print(error_msg)
            self.show_connection_warning(error_msg)

    # ---------------------- Stop Button Functionality ----------------------

    def stop_acquisition(self):
        port = self.settings_manager.get_serial_port()
        baud = self.settings_manager.get_baud_rate()
        
        if port == "Select Port" or baud == "Select Baud Rate" or port is None or baud is None:
            self.show_connection_warning("Please configure serial port and baud rate in System Setup first.")
            return
            
        if self.serial_reader:
            self.serial_reader.stop()
        self.timer.stop()
        if hasattr(self, '_12to1_timer'):
            self._12to1_timer.stop()

        # Stop elapsed time tracking
        self.elapsed_timer.stop()
        self.start_time = None

        # --- Calculate and update metrics on dashboard ---
        if hasattr(self, 'dashboard_callback'):
            lead2_data = self.data.get("II", [])[-500:]
            lead_I_data = self.data.get("I", [])[-500:]
            lead_aVF_data = self.data.get("aVF", [])[-500:]
            heart_rate = None
            pr_interval = None
            qrs_duration = None
            qt_interval = None
            qtc_interval = None
            qrs_axis = "--"
            st_segment = "--"
            if len(lead2_data) > 100:
                # Use same detection logic as live
                from scipy.signal import find_peaks
                sampling_rate = 500
                ecg_signal = np.array(lead2_data)
                centered = ecg_signal - np.mean(ecg_signal)
                # R peak detection
                r_peaks, _ = find_peaks(centered, distance=int(0.2 * sampling_rate), prominence=0.6 * np.std(centered))
                # Q and S: local minima before and after R
                q_peaks = []
                s_peaks = []
                for r in r_peaks:
                    q_start = max(0, r - int(0.06 * sampling_rate))
                    q_end = r
                    if q_end > q_start:
                        q_idx = np.argmin(centered[q_start:q_end]) + q_start
                        q_peaks.append(q_idx)
                    s_start = r
                    s_end = min(len(centered), r + int(0.06 * sampling_rate))
                    if s_end > s_start:
                        s_idx = np.argmin(centered[s_start:s_end]) + s_start
                        s_peaks.append(s_idx)
                # P: positive peak before Q (within 0.1-0.2s)
                p_peaks = []
                for q in q_peaks:
                    p_start = max(0, q - int(0.2 * sampling_rate))
                    p_end = q - int(0.08 * sampling_rate)
                    if p_end > p_start:
                        p_candidates, _ = find_peaks(centered[p_start:p_end], prominence=0.1 * np.std(centered))
                        if len(p_candidates) > 0:
                            p_peaks.append(p_start + p_candidates[-1])
                # T: positive peak after S (within 0.1-0.4s)
                t_peaks = []
                for s in s_peaks:
                    t_start = s + int(0.08 * sampling_rate)
                    t_end = min(len(centered), s + int(0.4 * sampling_rate))
                    if t_end > t_start:
                        t_candidates, _ = find_peaks(centered[t_start:t_end], prominence=0.1 * np.std(centered))
                        if len(t_candidates) > 0:
                            t_peaks.append(t_start + t_candidates[np.argmax(centered[t_start + t_candidates])])
                # Calculate intervals
                if len(r_peaks) > 1:
                    rr_intervals = np.diff(r_peaks) / sampling_rate  # in seconds
                    mean_rr = np.mean(rr_intervals)
                    heart_rate = 60 / mean_rr if mean_rr > 0 else None
                else:
                    rr_intervals = None
                    heart_rate = None
                if len(p_peaks) > 0 and len(r_peaks) > 0:
                    pr_interval = (r_peaks[-1] - p_peaks[-1]) * 1000 / sampling_rate  # ms
                if len(q_peaks) > 0 and len(s_peaks) > 0:
                    qrs_duration = (s_peaks[-1] - q_peaks[-1]) * 1000 / sampling_rate  # ms
                if len(q_peaks) > 0 and len(t_peaks) > 0:
                    qt_interval = (t_peaks[-1] - q_peaks[-1]) * 1000 / sampling_rate  # ms
                if qt_interval and heart_rate:
                    qtc_interval = qt_interval / np.sqrt(60 / heart_rate)  # Bazett's formula

                # QRS axis
                qrs_axis = calculate_qrs_axis(lead_I_data, lead_aVF_data, r_peaks)

                # ST segment
                st_segment = calculate_st_segment(lead2_data, r_peaks, fs=sampling_rate)

            self.dashboard_callback({
                'Heart Rate': heart_rate,
                'PR': pr_interval,
                'QRS': qrs_duration,
                'QTc': qtc_interval,
                'QRS_axis': qrs_axis,
                'ST': st_segment
            })

    def update_plot(self):
        
        if not self.serial_reader:
            return
        
        line = self.serial_reader.ser.readline()
        line_data = line.decode('utf-8', errors='replace').strip()
        if not line_data:
            return
        
        try:
            values = [int(x) for x in line_data.split()]
            if len(values) != 8:
                return
            lead1 = values[0]
            v4    = values[1]
            v5    = values[2]
            lead2 = values[3]
            v3    = values[4]
            v6    = values[5]
            v1    = values[6]
            v2    = values[7]
            lead3 = lead2 - lead1
            avr = - (lead1 + lead2) / 2
            avl = (lead1 - lead3) / 2
            avf = (lead2 + lead3) / 2
            lead_data = {
                "I": lead1,
                "II": lead2,
                "III": lead3,
                "aVR": avr,
                "aVL": avl,
                "aVF": avf,
                "V1": v1,
                "V2": v2,
                "V3": v3,
                "V4": v4,
                "V5": v5,
                "V6": v6
            }
            for i, lead in enumerate(self.leads):
                self.data[lead].append(lead_data[lead])
                if len(self.data[lead]) > self.buffer_size:
                    self.data[lead].pop(0)
            
            # Write latest Lead II data to file for dashboard
            try:
                import json
                with open('lead_ii_live.json', 'w') as f:
                    json.dump(self.data["II"][-500:], f)
            except Exception as e:
                print("Error writing lead_ii_live.json:", e)
            
            # Calculate and update ECG metrics in real-time
            lead_ii_data = self.data.get("II", [])
            if lead_ii_data:
                intervals = self.calculate_ecg_intervals(lead_ii_data)
                self.update_ecg_metrics_on_top_of_lead_graphs(intervals)
            
            for i, lead in enumerate(self.leads):
                if len(self.data[lead]) > 0:
                    if len(self.data[lead]) < self.buffer_size:
                        data = np.full(self.buffer_size, np.nan)
                        data[-len(self.data[lead]):] = self.data[lead]
                    else:
                        data = np.array(self.data[lead])
                    
                    centered = data - np.nanmean(data)

                    # Apply current gain setting to the real data
                    gain_factor = self.settings_manager.get_wave_gain() / 10.0
                    centered = (data - np.nanmean(data)) * gain_factor
                    
                    self.lines[i].set_ydata(centered)
                    
                    # Use dynamic y-limits based on current gain setting
                    ylim = self.ylim if hasattr(self, 'ylim') else 400
                    self.axs[i].set_ylim(-ylim, ylim)
                    
                    # Use dynamic x-limits based on current buffer size
                    self.axs[i].set_xlim(0, self.buffer_size)

                    # Update title with current settings
                    current_speed = self.settings_manager.get_wave_speed()
                    current_gain = self.settings_manager.get_wave_gain()
                    self.axs[i].set_title(f"{lead} | Speed: {current_speed}mm/s | Gain: {current_gain}mm/mV", 
                                        fontsize=8, color='#666', pad=10)
                    
                    # Add grid lines to show scale
                    self.axs[i].grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
                    
                    # Remove any existing labels
                    self.axs[i].set_xlabel("")
                    self.axs[i].set_ylabel("")
                    
                    self.canvases[i].draw_idle()
                    
        except Exception as e:
            print("Error parsing ECG data:", e)

    def export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export ECG Data as PDF", "", "PDF Files (*.pdf)")
        if path:
            from matplotlib.backends.backend_pdf import PdfPages
            with PdfPages(path) as pdf:
                for fig in self.figures:
                    pdf.savefig(fig)

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export ECG Data as CSV", "", "CSV Files (*.csv)")
        if path:
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Sample"] + self.leads)
                for i in range(self.buffer_size):
                    row = [i]
                    for lead in self.leads:
                        if i < len(self.data[lead]):
                            row.append(self.data[lead][i])
                        else:
                            row.append("")
                    writer.writerow(row)

    def go_back(self):

        if hasattr(self, '_overlay_active') and self._overlay_active:
            self._restore_original_layout()

        # Go back to dashboard (assumes dashboard is at index 0)
        self.stacked_widget.setCurrentIndex(0)

    def show_connection_warning(self, extra_msg=""):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Connection Required")
        msg.setText("❤️ Please configure serial port and baud rate in System Setup.\n\nStay healthy!" + ("\n\n" + extra_msg if extra_msg else ""))
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def show_main_menu(self):  
        self.clear_content()

    def clear_content(self):
        for i in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

    def show_sequential_view(self):
        from ecg.lead_sequential_view import LeadSequentialView
        win = LeadSequentialView(self.leads, self.data, buffer_size=500)
        win.show()
        self._sequential_win = win

    # ------------------------------------ 12 leads overlay --------------------------------------------

    def twelve_leads_overlay(self):
        # If overlay is already shown, hide it and restore original layout
        if hasattr(self, '_overlay_active') and self._overlay_active:
            self._restore_original_layout()
            return
        
        # Store the original plot area layout
        self._store_original_layout()
        
        # Create the overlay widget
        self._create_overlay_widget()
        
        # Replace the plot area with overlay
        self._replace_plot_area_with_overlay()
        
        # Mark overlay as active
        self._overlay_active = True

        self._apply_current_overlay_mode()

    def _store_original_layout(self):
        
        # Store the current plot area widget
        self._original_plot_area = self.plot_area
        
        # Store the current layout
        self._original_layout = self.plot_area.layout()
        
        # Store the current figures, canvases, axes, and lines
        self._original_figures = getattr(self, 'figures', [])
        self._original_canvases = getattr(self, 'canvases', [])
        self._original_axs = getattr(self, 'axs', [])
        self._original_lines = getattr(self, 'lines', [])

    def _create_overlay_widget(self):
        
        from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QFrame
        
        # Create overlay container
        self._overlay_widget = QWidget()
        self._overlay_widget.setStyleSheet("""
            QWidget {
                background: #000;
                border: 2px solid #ff6600;
                border-radius: 15px;
            }
        """)
        
        # Main layout for overlay
        overlay_layout = QVBoxLayout(self._overlay_widget)
        overlay_layout.setContentsMargins(20, 20, 20, 20)
        overlay_layout.setSpacing(15)
        
        # Top control panel with close button
        top_panel = QFrame()
        top_panel.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.1);
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 15px;
                padding: 10px;
            }
        """)
        top_layout = QHBoxLayout(top_panel)
        top_layout.setContentsMargins(15, 10, 15, 10)
        top_layout.setSpacing(20)
        
        # Close button
        close_btn = QPushButton("Close Overlay")
        close_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #ff6600, stop:1 #ff8c42);
                color: white;
                border: 2px solid #ff6600;
                border-radius: 10px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
                min-width: 120px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #ff8c42, stop:1 #ff6600);
                border: 2px solid #ff8c42;
            }
        """)
        close_btn.clicked.connect(self._restore_original_layout)
        
        # Mode control buttons with highlighting
        self.light_mode_btn = QPushButton("Light Mode")
        self.dark_mode_btn = QPushButton("Dark Mode")
        self.graph_mode_btn = QPushButton("Graph Mode")
        
        # Store current mode for highlighting
        self._current_overlay_mode = "dark"  # Default mode
        
        button_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #4CAF50, stop:1 #45a049);
                color: white;
                border: 2px solid #4CAF50;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #45a049, stop:1 #4CAF50);
                border: 2px solid #45a049;
            }
        """
        
        active_button_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #ff6600, stop:1 #ff8c42);
                color: white;
                border: 3px solid #ff6600;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 100px;
                box-shadow: 0 4px 12px rgba(255,102,0,0.4);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #ff8c42, stop:1 #ff6600);
                border: 3px solid #ff8c42;
            }
        """
        
        self.light_mode_btn.setStyleSheet(button_style)
        self.dark_mode_btn.setStyleSheet(button_style)
        self.graph_mode_btn.setStyleSheet(button_style)
        
        # Add widgets to top panel
        top_layout.addWidget(close_btn)
        top_layout.addStretch()
        top_layout.addWidget(self.light_mode_btn)
        top_layout.addWidget(self.dark_mode_btn)
        top_layout.addWidget(self.graph_mode_btn)
        
        overlay_layout.addWidget(top_panel)
        
        # Create the matplotlib figure with all leads
        self._create_overlay_figure(overlay_layout)
        
        # Connect mode buttons
        self.light_mode_btn.clicked.connect(lambda: self._apply_overlay_mode("light"))
        self.dark_mode_btn.clicked.connect(lambda: self._apply_overlay_mode("dark"))
        self.graph_mode_btn.clicked.connect(lambda: self._apply_overlay_mode("graph"))
        
        # Apply default dark mode and highlight it
        self._apply_overlay_mode("dark")

    def _create_overlay_figure(self, overlay_layout):
        
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        import numpy as np
        
        # Create figure with all leads - adjust spacing for better visibility
        num_leads = len(self.leads)
        fig = Figure(figsize=(16, num_leads * 2.2), facecolor='none')  # Changed to transparent
        
        # Adjust subplot parameters for better spacing
        fig.subplots_adjust(left=0.05, right=0.95, top=0.98, bottom=0.02, hspace=0.15)
        
        self._overlay_axes = []
        self._overlay_lines = []
        
        for idx, lead in enumerate(self.leads):
            ax = fig.add_subplot(num_leads, 1, idx+1)
            ax.set_facecolor('none')  # Changed to transparent
            
            # Remove all borders and spines
            for spine in ax.spines.values():
                spine.set_visible(False)
            
            # Remove all ticks and labels for cleaner look
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_ylabel(lead, color='#00ff00', fontsize=12, fontweight='bold', labelpad=20)
            
            # Create line with initial data
            line, = ax.plot(np.arange(self.buffer_size), [np.nan]*self.buffer_size, color="#00ff00", lw=1.5)
            self._overlay_axes.append(ax)
            self._overlay_lines.append(line)
        
        self._overlay_canvas = FigureCanvas(fig)
        overlay_layout.addWidget(self._overlay_canvas)
        
        # Start update timer for overlay
        self._overlay_timer = QTimer(self)
        self._overlay_timer.timeout.connect(self._update_overlay_plots)
        self._overlay_timer.start(100)

    def _update_overlay_plots(self):
        
        if not hasattr(self, '_overlay_lines') or not self._overlay_lines:
            return
        
        for idx, lead in enumerate(self.leads):
            if idx < len(self._overlay_lines):
                data = self.data.get(lead, [])
                line = self._overlay_lines[idx]
                ax = self._overlay_axes[idx]
                
                plot_data = np.full(self.buffer_size, np.nan)
                
                if data and len(data) > 0:
                    n = min(len(data), self.buffer_size)
                    centered = np.array(data[-n:]) - np.mean(data[-n:])
                    
                    # Apply current gain setting
                    gain_factor = self.settings_manager.get_wave_gain() / 10.0
                    centered = centered * gain_factor
                    
                    if n < self.buffer_size:
                        stretched = np.interp(
                            np.linspace(0, n-1, self.buffer_size),
                            np.arange(n),
                            centered
                        )
                        plot_data[:] = stretched
                    else:
                        plot_data[-n:] = centered
                    
                    # Set dynamic y-limits based on data
                    ymin = np.min(centered) - 100
                    ymax = np.max(centered) + 100
                    if ymin == ymax:
                        ymin, ymax = -500, 500
                    
                    # Ensure y-limits are reasonable
                    ymin = max(-1000, ymin)
                    ymax = min(1000, ymax)
                    
                    ax.set_ylim(ymin, ymax)
                else:
                    ax.set_ylim(-500, 500)
                
                # Set x-limits
                ax.set_xlim(0, self.buffer_size-1)
                line.set_ydata(plot_data)
        
        if hasattr(self, '_overlay_canvas'):
            self._overlay_canvas.draw_idle()

    def _apply_current_overlay_mode(self):

        if hasattr(self, '_current_overlay_mode'):
            self._apply_overlay_mode(self._current_overlay_mode)

    def _apply_overlay_mode(self, mode):
        
        if not hasattr(self, '_overlay_axes') or not self._overlay_axes:
            return
        
        # Store current mode
        self._current_overlay_mode = mode
        
        self._clear_all_backgrounds()
        
        # Update button highlighting
        button_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #4CAF50, stop:1 #45a049);
                color: white;
                border: 2px solid #4CAF50;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #45a049, stop:1 #4CAF50);
                border: 2px solid #45a049;
            }
        """
        
        active_button_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #ff6600, stop:1 #ff8c42);
                color: white;
                border: 3px solid #ff6600;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 100px;
                box-shadow: 0 4px 12px rgba(255,102,0,0.4);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #ff8c42, stop:1 #ff6600);
                border: 3px solid #ff8c42;
            }
        """
        
        # Reset all buttons to normal style
        self.light_mode_btn.setStyleSheet(button_style)
        self.dark_mode_btn.setStyleSheet(button_style)
        self.graph_mode_btn.setStyleSheet(button_style)
        
        # Highlight the active button
        if mode == "light":
            self.light_mode_btn.setStyleSheet(active_button_style)
            self._overlay_widget.setStyleSheet("""
                QWidget {
                    background: rgba(255, 255, 255, 0.95);
                    border: 2px solid #ff6600;
                    border-radius: 15px;
                }
            """)
            
            for ax in self._overlay_axes:
                ax.set_facecolor('#ffffff')
                ax.tick_params(axis='x', colors='#333333', labelsize=10)
                ax.tick_params(axis='y', colors='#333333', labelsize=10)
                ax.set_ylabel(ax.get_ylabel(), color='#333333', fontsize=14, fontweight='bold', labelpad=15)
                for spine in ax.spines.values():
                    spine.set_visible(True)
                    spine.set_color('#333333')
                    spine.set_linewidth(1.0)
                ax.figure.canvas.draw()
            
            for line in self._overlay_lines:
                line.set_color('#0066cc')
                line.set_linewidth(2.0)
        
        elif mode == "dark":
            self.dark_mode_btn.setStyleSheet(active_button_style)
            self._overlay_widget.setStyleSheet("""
                QWidget {
                    background: rgba(0, 0, 0, 0.95);
                    border: 2px solid #ff6600;
                    border-radius: 15px;
                }
            """)
            
            for ax in self._overlay_axes:
                ax.set_facecolor('#000')
                ax.tick_params(axis='x', colors='#00ff00', labelsize=10)
                ax.tick_params(axis='y', colors='#00ff00', labelsize=10)
                ax.set_ylabel(ax.get_ylabel(), color='#00ff00', fontsize=14, fontweight='bold', labelpad=15)
                for spine in ax.spines.values():
                    spine.set_visible(False)
            
            for line in self._overlay_lines:
                line.set_color('#00ff00')
                line.set_linewidth(2.0)
        
        elif mode == "graph":
            self.graph_mode_btn.setStyleSheet(active_button_style)
            self._apply_graph_mode()
        
        if hasattr(self, '_overlay_canvas'):
            self._overlay_canvas.draw()

    def _clear_all_backgrounds(self):
        
        try:
            # Clear figure-level background
            if hasattr(self, '_overlay_canvas') and self._overlay_canvas.figure:
                fig = self._overlay_canvas.figure
                if hasattr(fig, '_figure_background'):
                    try:
                        fig._figure_background.remove()
                        delattr(fig, '_figure_background')
                    except:
                        pass
                
                # Reset figure background to transparent
                fig.patch.set_facecolor('none')
            
            # Clear axis-level backgrounds
            if hasattr(self, '_overlay_axes'):
                for ax in self._overlay_axes:
                    if hasattr(ax, '_background_image'):
                        try:
                            ax._background_image.remove()
                            delattr(ax, '_background_image')
                        except:
                            pass
                    
                    # Reset axis background to transparent
                    ax.set_facecolor('none')
                    ax.patch.set_alpha(0.0)
                    
        except Exception as e:
            print(f"Error clearing backgrounds: {e}")

    def _apply_graph_mode(self):
        
        try:
            import os
            from PyQt5.QtGui import QPixmap
            import matplotlib.image as mpimg
            
            bg_path = "ecg_bgimg_test.png"
            if os.path.exists(bg_path):
                # Load the background image
                bg_img = QPixmap(bg_path)
                if not bg_img.isNull():
                    # Save temporary file for matplotlib
                    temp_path = "temp_bg.png"
                    bg_img.save(temp_path)
                    bg_matplotlib = mpimg.imread(temp_path)
                    
                    # Apply background to the entire figure first
                    if hasattr(self, '_overlay_canvas') and self._overlay_canvas.figure:
                        fig = self._overlay_canvas.figure
                        fig.patch.set_facecolor('#ffffff')  # White background for the figure
                        
                        # Remove any existing background from figure
                        if hasattr(fig, '_figure_background'):
                            try:
                                fig._figure_background.remove()
                            except:
                                pass
                        
                        # Apply background image to the entire figure
                        fig._figure_background = fig.figimage(
                            bg_matplotlib, 
                            xo=0, yo=0, 
                            alpha=0.4,  # Slightly transparent so waves are visible
                            zorder=0
                        )
                    
                    # Apply background to all axes
                    for i, ax in enumerate(self._overlay_axes):
                        # Set transparent background for subplots
                        ax.set_facecolor('none')
                        ax.patch.set_alpha(0.0)
                        
                        # Remove all borders and spines
                        for spine in ax.spines.values():
                            spine.set_visible(False)
                        
                        # Remove ticks for cleaner look
                        ax.set_xticks([])
                        ax.set_yticks([])
                        
                        # Set label color to dark for better visibility on grid background
                        ax.set_ylabel(ax.get_ylabel(), color='#333333', fontsize=12, fontweight='bold', labelpad=20)
                        
                        # Set proper limits
                        ax.set_xlim(0, self.buffer_size-1)
                        ax.set_ylim(-500, 500)
                    
                    # Change line colors to dark red for better visibility on grid background
                    for line in self._overlay_lines:
                        line.set_color('#cc0000')  # Darker red
                        line.set_linewidth(2.5)
                        line.set_alpha(1.0)
                    
                    # Clean up temporary file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    
                    # Force redraw
                    if hasattr(self, '_overlay_canvas'):
                        self._overlay_canvas.draw()
                        
                    return
                        
                else:
                    print("Failed to load background image")
                    return
            else:
                print(f"Background image not found at: {bg_path}")
                return
                
        except Exception as e:
            print(f"Error applying graph mode: {e}")
            return

    def _replace_plot_area_with_overlay(self):
        
        # Get the main horizontal layout
        main_layout = self.grid_widget.layout()
        
        # Find the main_vbox layout item (which contains the plot_area)
        for i in range(main_layout.count()):
            item = main_layout.itemAt(i)
            if item.layout() and hasattr(item.layout(), 'indexOf') and item.layout().indexOf(self.plot_area) >= 0:
                # Found the layout containing plot_area
                main_vbox_layout = item.layout()
                
                # Find and replace the plot_area in main_vbox_layout
                plot_area_index = main_vbox_layout.indexOf(self.plot_area)
                if plot_area_index >= 0:
                    # Remove the plot_area
                    main_vbox_layout.removeWidget(self.plot_area)
                    self.plot_area.hide()
                    
                    # Add the overlay widget at the same position
                    main_vbox_layout.insertWidget(plot_area_index, self._overlay_widget)
                    return
        
        # Fallback: if we can't find the exact position, add to the end of main_vbox
        # Find the main_vbox layout
        for i in range(main_layout.count()):
            item = main_layout.itemAt(i)
            if item.layout() and hasattr(item.layout(), 'indexOf') and item.layout().indexOf(self.plot_area) >= 0:
                main_vbox_layout = item.layout()
                main_vbox_layout.removeWidget(self.plot_area)
                self.plot_area.hide()
                main_vbox_layout.addWidget(self._overlay_widget)
                break

    def _restore_original_layout(self):
        
        if not hasattr(self, '_overlay_active') or not self._overlay_active:
            return
        
        # Stop overlay timer
        if hasattr(self, '_overlay_timer'):
            self._overlay_timer.stop()
            self._overlay_timer.deleteLater()
        
        # Find and remove overlay widget from main_vbox layout
        main_layout = self.grid_widget.layout()
        for i in range(main_layout.count()):
            item = main_layout.itemAt(i)
            if item.layout() and hasattr(item.layout(), 'indexOf'):
                main_vbox_layout = item.layout()
                
                # Check if overlay widget is in this layout
                overlay_index = main_vbox_layout.indexOf(self._overlay_widget)
                if overlay_index >= 0:
                    # Remove overlay widget
                    main_vbox_layout.removeWidget(self._overlay_widget)
                    
                    # Restore original plot area at the exact same position
                    main_vbox_layout.insertWidget(overlay_index, self.plot_area)
                    self.plot_area.show()
                    break
        
        # Clean up overlay references
        if hasattr(self, '_overlay_widget'):
            self._overlay_widget.deleteLater()
            delattr(self, '_overlay_widget')
        
        if hasattr(self, '_overlay_axes'):
            delattr(self, '_overlay_axes')
        
        if hasattr(self, '_overlay_lines'):
            delattr(self, '_overlay_lines')
        
        if hasattr(self, '_overlay_canvas'):
            delattr(self, '_overlay_canvas')
        
        # Mark overlay as inactive
        self._overlay_active = False
        
        # Force redraw of original plots
        self.redraw_all_plots()

    # ------------------------------------ 6 leads overlay --------------------------------------------

    def six_leads_overlay(self):
        # If overlay is already shown, hide it and restore original layout
        if hasattr(self, '_overlay_active') and self._overlay_active:
            self._restore_original_layout()
            return
        
        # Store the original plot area layout
        self._store_original_layout()
        
        # Create the 2-column overlay widget
        self._create_two_column_overlay_widget()
        
        # Replace the plot area with overlay
        self._replace_plot_area_with_overlay()
        
        # Mark overlay as active
        self._overlay_active = True

        self._apply_current_overlay_mode()

    def _create_two_column_overlay_widget(self):
        from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QFrame
        
        # Create overlay container
        self._overlay_widget = QWidget()
        self._overlay_widget.setStyleSheet("""
            QWidget {
                background: #000;
                border: 2px solid #ff6600;
                border-radius: 15px;
            }
        """)
        
        # Main layout for overlay
        overlay_layout = QVBoxLayout(self._overlay_widget)
        overlay_layout.setContentsMargins(20, 20, 20, 20)
        overlay_layout.setSpacing(15)
        
        # Top control panel with close button and mode controls
        top_panel = QFrame()
        top_panel.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.1);
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 15px;
                padding: 10px;
            }
        """)
        top_layout = QHBoxLayout(top_panel)
        top_layout.setContentsMargins(15, 10, 15, 10)
        top_layout.setSpacing(20)
        
        # Close button
        close_btn = QPushButton("Close Overlay")
        close_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #ff6600, stop:1 #ff8c42);
                color: white;
                border: 2px solid #ff6600;
                border-radius: 10px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
                min-width: 120px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #ff8c42, stop:1 #ff6600);
                border: 2px solid #ff8c42;
            }
        """)
        close_btn.clicked.connect(self._restore_original_layout)
        
        # Mode control buttons with highlighting
        self.light_mode_btn = QPushButton("Light Mode")
        self.dark_mode_btn = QPushButton("Dark Mode")
        self.graph_mode_btn = QPushButton("Graph Mode")
        
        # Store current mode for highlighting
        self._current_overlay_mode = "dark"  # Default mode
        
        button_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #4CAF50, stop:1 #45a049);
                color: white;
                border: 2px solid #4CAF50;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #45a049, stop:1 #4CAF50);
                border: 2px solid #45a049;
            }
        """
        
        active_button_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #ff6600, stop:1 #ff8c42);
                color: white;
                border: 3px solid #ff6600;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 100px;
                box-shadow: 0 4px 12px rgba(255,102,0,0.4);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #ff8c42, stop:1 #ff6600);
                border: 3px solid #ff8c42;
            }
        """
        
        self.light_mode_btn.setStyleSheet(button_style)
        self.dark_mode_btn.setStyleSheet(button_style)
        self.graph_mode_btn.setStyleSheet(button_style)
        
        # Add widgets to top panel
        top_layout.addWidget(close_btn)
        top_layout.addStretch()
        top_layout.addWidget(self.light_mode_btn)
        top_layout.addWidget(self.dark_mode_btn)
        top_layout.addWidget(self.graph_mode_btn)
        
        overlay_layout.addWidget(top_panel)
        
        # Create the 2-column matplotlib figure
        self._create_two_column_figure(overlay_layout)
        
        # Connect mode buttons
        self.light_mode_btn.clicked.connect(lambda: self._apply_overlay_mode("light"))
        self.dark_mode_btn.clicked.connect(lambda: self._apply_overlay_mode("dark"))
        self.graph_mode_btn.clicked.connect(lambda: self._apply_overlay_mode("graph"))
        
        # Apply default dark mode and highlight it
        self._apply_overlay_mode("dark")

    def _create_two_column_figure(self, overlay_layout):
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        import numpy as np
        
        # Define the two columns of leads
        left_leads = ["I", "II", "III", "aVR", "aVL", "aVF"]
        right_leads = ["V1", "V2", "V3", "V4", "V5", "V6"]
        
        # Create figure with 2 columns and 6 rows
        fig = Figure(figsize=(16, 12), facecolor='none')
        
        # Adjust subplot parameters for better spacing
        fig.subplots_adjust(left=0.05, right=0.95, top=0.98, bottom=0.02, hspace=0.15, wspace=0.1)
        
        self._overlay_axes = []
        self._overlay_lines = []
        
        # Create left column (limb leads)
        for idx, lead in enumerate(left_leads):
            ax = fig.add_subplot(6, 2, 2*idx + 1)
            ax.set_facecolor('none')
            
            # Remove all borders and spines

            for spine in ax.spines.values():
                spine.set_visible(False)
            
            # Remove all ticks and labels for cleaner look
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_ylabel(lead, color='#00ff00', fontsize=12, fontweight='bold', labelpad=20)
            
            # Create line with initial data
            line, = ax.plot(np.arange(self.buffer_size), [np.nan]*self.buffer_size, color="#00ff00", lw=1.5)
            self._overlay_axes.append(ax)
            self._overlay_lines.append(line)
        
        # Create right column (chest leads)
        for idx, lead in enumerate(right_leads):
            ax = fig.add_subplot(6, 2, 2*idx + 2)
            ax.set_facecolor('none')
            
            # Remove all borders and spines
            for spine in ax.spines.values():
                spine.set_visible(False)
            
            # Remove all ticks and labels for cleaner look
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_ylabel(lead, color='#00ff00', fontsize=12, fontweight='bold', labelpad=20)
            
            # Create line with initial data
            line, = ax.plot(np.arange(self.buffer_size), [np.nan]*self.buffer_size, color="#00ff00", lw=1.5)
            self._overlay_axes.append(ax)
            self._overlay_lines.append(line)
        
        self._overlay_canvas = FigureCanvas(fig)
        overlay_layout.addWidget(self._overlay_canvas)
        
        # Start update timer for overlay
        self._overlay_timer = QTimer(self)
        self._overlay_timer.timeout.connect(self._update_two_column_plots)
        self._overlay_timer.start(100)

    def _update_two_column_plots(self):
        if not hasattr(self, '_overlay_lines') or not self._overlay_lines:
            return
        
        # Define the two columns of leads
        left_leads = ["I", "II", "III", "aVR", "aVL", "aVF"]
        right_leads = ["V1", "V2", "V3", "V4", "V5", "V6"]
        all_leads = left_leads + right_leads
        
        for idx, lead in enumerate(all_leads):
            if idx < len(self._overlay_lines):
                data = self.data.get(lead, [])
                line = self._overlay_lines[idx]
                ax = self._overlay_axes[idx]
                
                plot_data = np.full(self.buffer_size, np.nan)
                
                if data and len(data) > 0:
                    n = min(len(data), self.buffer_size)
                    centered = np.array(data[-n:]) - np.mean(data[-n:])
                    
                    # Apply current gain setting
                    gain_factor = self.settings_manager.get_wave_gain() / 10.0
                    centered = centered * gain_factor
                    
                    if n < self.buffer_size:
                        stretched = np.interp(
                            np.linspace(0, n-1, self.buffer_size),
                            np.arange(n),
                            centered
                        )
                        plot_data[:] = stretched
                    else:
                        plot_data[-n:] = centered
                    
                    # Set dynamic y-limits based on data
                    ymin = np.min(centered) - 100
                    ymax = np.max(centered) + 100
                    if ymin == ymax:
                        ymin, ymax = -500, 500
                    
                    # Ensure y-limits are reasonable
                    ymin = max(-1000, ymin)
                    ymax = min(1000, ymax)
                    
                    ax.set_ylim(ymin, ymax)
                else:
                    ax.set_ylim(-500, 500)
                
                # Set x-limits
                ax.set_xlim(0, self.buffer_size-1)
                line.set_ydata(plot_data)
        
        if hasattr(self, '_overlay_canvas'):
            self._overlay_canvas.draw_idle()