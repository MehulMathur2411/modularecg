import sys
import time
import numpy as np
from pyparsing import line
import serial
import serial.tools.list_ports
import csv
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QGroupBox, QFileDialog,
    QStackedLayout, QGridLayout, QSizePolicy, QMessageBox, QFormLayout, QLineEdit, QFrame
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from ecg.recording import ECGMenu
from scipy.signal import find_peaks

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

        # Add Back button at the top
        back_btn = QPushButton("Back")
        back_btn.setStyleSheet("background: #ff6600; color: white; border-radius: 10px; padding: 8px 24px; font-size: 16px; font-weight: bold;")
        back_btn.clicked.connect(self.go_back)
        main_vbox = QVBoxLayout()
        main_vbox.addWidget(back_btn, alignment=Qt.AlignLeft)

        menu_frame = QGroupBox("Menu")
        menu_layout = QVBoxLayout(menu_frame)
        menu_buttons = [
            ("Save ECG", self.show_save_ecg),
            ("Open ECG", self.show_open_ecg),
            ("Working Mode", self.show_working_mode),
            ("Printer Setup", self.show_printer_setup),
            ("Set Filter", self.open_filter_settings),
            ("System Setup", self.show_system_setup),
            ("Load Default", self.show_factory_default_config),
            ("Version", self.show_version_info),
            ("Factory Maintain", self.show_maintain_password),
            ("12:1 Graph", self.show_12to1_graph),
            # ("Exit", self.show_exit_page)
        ]
        for text, handler in menu_buttons:
            btn = QPushButton(text)
            btn.setFixedHeight(36)
            btn.clicked.connect(handler)
            menu_layout.addWidget(btn)
        menu_layout.addStretch(1)

        conn_layout = QHBoxLayout()
        self.port_combo = QComboBox()
        self.baud_combo = QComboBox()
        self.baud_combo.addItem("Select Baud Rate")
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        conn_layout.addWidget(QLabel("Serial Port:"))
        conn_layout.addWidget(self.port_combo)
        conn_layout.addWidget(QLabel("Baud Rate:"))
        conn_layout.addWidget(self.baud_combo)
        self.refresh_ports()
        main_vbox.addLayout(conn_layout)

        self.plot_area = QWidget()
        main_vbox.addWidget(self.plot_area)
        self.update_lead_layout()

        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.export_pdf_btn = QPushButton("Export as PDF")
        self.export_csv_btn = QPushButton("Export as CSV")
        self.back_btn = QPushButton("Back")
        self.ecg_plot_btn = QPushButton("Open ECG Live Plot")
        self.sequential_btn = QPushButton("Show All Leads Sequentially")
        self.all_leads_btn = QPushButton("Show All Leads Overlay")
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.export_pdf_btn)
        btn_layout.addWidget(self.export_csv_btn)
        btn_layout.addWidget(self.back_btn)
        btn_layout.addWidget(self.ecg_plot_btn)
        btn_layout.addWidget(self.sequential_btn)
        btn_layout.addWidget(self.all_leads_btn)
        main_vbox.addLayout(btn_layout)

        self.start_btn.clicked.connect(self.start_acquisition)
        self.stop_btn.clicked.connect(self.stop_acquisition)
        self.export_pdf_btn.clicked.connect(self.export_pdf)
        self.export_csv_btn.clicked.connect(self.export_csv)
        self.back_btn.clicked.connect(self.go_back)
        self.sequential_btn.clicked.connect(self.show_sequential_view)
        self.all_leads_btn.clicked.connect(self.show_all_leads_overlay)
        # self.ecg_plot_btn.clicked.connect(lambda: run_ecg_live_plot(port='/cu.usbserial-10', baudrate=9600, buffer_size=100))

        # --- Add menu using ECGMenu ---
        self.menu = ECGMenu()
        self.menu.on_save_ecg = self.show_save_ecg
        self.menu.on_open_ecg = self.show_open_ecg
        self.menu.on_working_mode = self.show_working_mode
        self.menu.on_printer_setup = self.show_printer_setup
        self.menu.on_set_filter = self.open_filter_settings
        self.menu.on_system_setup = self.show_system_setup
        self.menu.on_load_default = self.show_factory_default_config
        self.menu.on_version_info = self.show_version_info
        self.menu.on_factory_maintain = self.show_maintain_password
        self.menu.on_exit = self.show_exit_page

        main_hbox = QHBoxLayout(self.grid_widget)
        main_hbox.addWidget(self.menu)
        main_hbox.addLayout(main_vbox)
        self.grid_widget.setLayout(main_hbox)

    def center_on_screen(self):
        qr = self.frameGeometry()
        from PyQt5.QtWidgets import QApplication
        cp = QApplication.desktop().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def show_12to1_graph(self):
        win = QWidget()
        win.setWindowTitle("12:1 ECG Graph")
        layout = QVBoxLayout(win)
        ordered_leads = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]
        self._12to1_lines = {}
        self._12to1_axes = {}
        for lead in ordered_leads:
            group = QGroup
            group.setStyleSheet("QGroupBox { border: 2px solid rgba(0,0,0,0.2); border-radius: 8px; margin-top: 8px; }")
            vbox = QVBoxLayout(group)
            fig = Figure(figsize=(12, 2.5), facecolor='#000')
            ax = fig.add_subplot(111)
            ax.set_facecolor('#000')
            ax.set_ylim(-400, 400)
            ax.set_xlim(0, self.buffer_size)
            line, = ax.plot([0]*self.buffer_size, color=self.LEAD_COLORS.get(lead, "#00ff99"), lw=2)
            self._12to1_lines[lead] = line
            self._12to1_axes[lead] = ax
            canvas = FigureCanvas(fig)
            vbox.addWidget(canvas)
            layout.addWidget(group)
        win.setLayout(layout)
        win.resize(1400, 1200)
        win.show()
        self._12to1_win = win
        self._12to1_timer = QTimer(self)
        self._12to1_timer.timeout.connect(self.update_12to1_graph)
        self._12to1_timer.start(100)
        def stop_timer():
            self._12to1_timer.stop()
        win.destroyed.connect(stop_timer)

    def update_12to1_graph(self):
        for lead, line in self._12to1_lines.items():
            data = self.data.get(lead, [])
            ax = self._12to1_axes[lead]
            if data:
                n = min(len(data), self.buffer_size)
                plot_data = np.full(self.buffer_size, np.nan)
                centered = np.array(data[-n:]) - np.mean(data[-n:])
                plot_data[-n:] = centered
                line.set_ydata(plot_data)
                ax.set_ylim(-400, 400)
            else:
                line.set_ydata([np.nan]*self.buffer_size)
            ax.figure.canvas.draw_idle()

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
            # Robust: Only plot if enough data, else show blank
            if data and len(data) >= 10:
                plot_data = np.array(data[-detailed_buffer_size:])
                x = np.arange(len(plot_data))
                centered = plot_data - np.mean(plot_data)
                line.set_data(x, centered)
                ax.set_xlim(0, max(len(centered)-1, 1))
                ymin = np.min(centered) - 100
                ymax = np.max(centered) + 100
                if ymin == ymax:
                    ymin, ymax = -500, 500
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
                    sampling_rate = 500
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
                            heart_rate = 60.0 / mean_rr
                    if len(p_peaks) > 0 and len(r_peaks) > 0:
                        pr_interval = (r_peaks[-1] - p_peaks[-1]) * 1000 / sampling_rate  # ms
                    if len(q_peaks) > 0 and len(s_peaks) > 0:
                        qrs_duration = (s_peaks[-1] - q_peaks[-1]) * 1000 / sampling_rate  # ms
                    if len(q_peaks) > 0 and len(t_peaks) > 0:
                        qt_interval = (t_peaks[-1] - q_peaks[-1]) * 1000 / sampling_rate  # ms
                    if qt_interval and heart_rate:
                        qtc_interval = qt_interval / np.sqrt(60.0 / heart_rate)  # Bazett's formula

                    pr_label.setText(f"{pr_interval:.1f} ms" if pr_interval else "-- ms")
                    qrs_label.setText(f"{qrs_duration:.1f} ms" if qrs_duration else "-- ms")
                    qtc_label.setText(f"{qtc_interval:.1f} ms" if qtc_interval else "-- ms")

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
                    border: 2px solid #ff6600;
                    border-radius: 12px;
                    background: #fff;
                    color: #ff6600;
                    font: bold 14pt Arial;
                    margin-top: 8px;
                    padding: 6px;
                }
            """)
            vbox = QVBoxLayout(group)
            fig = Figure(facecolor='#fff', figsize=(6, 2.5))
            ax = fig.add_subplot(111)
            ax.set_facecolor('#fff')
            ax.set_ylim(-400, 400)
            ax.set_xlim(0, self.buffer_size)
            ax.tick_params(axis='x', colors='#ff6600')
            ax.tick_params(axis='y', colors='#ff6600')
            for spine in ax.spines.values():
                spine.set_color('#ff6600')
            line, = ax.plot([0]*self.buffer_size, color=self.LEAD_COLORS.get(lead, '#ff6600'), lw=2)
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

    def start_acquisition(self):
        port = self.port_combo.currentText()
        baud = self.baud_combo.currentText()
        if port == "Select Port" or baud == "Select Baud Rate":
            self.show_connection_warning()
            return
        try:
            if self.serial_reader:
                self.serial_reader.close()
            self.serial_reader = SerialECGReader(port, int(baud))
            self.serial_reader.start()
            self.timer.start(50)
            if hasattr(self, '_12to1_timer'):
                self._12to1_timer.start(100)
        except Exception as e:
            self.show_connection_warning(str(e))

    def stop_acquisition(self):
        port = self.port_combo.currentText()
        baud = self.baud_combo.currentText()
        if port == "Select Port" or baud == "Select Baud Rate":
            self.show_connection_warning()
            return
        if self.serial_reader:
            self.serial_reader.stop()
        self.timer.stop()
        if hasattr(self, '_12to1_timer'):
            self._12to1_timer.stop()

    def update_plot(self):
        if not self.serial_reader:
            return
        line = self.serial_reader.ser.readline()
        line_data = line.decode('utf-8', errors='replace').strip()
        if not line_data:
            return
        print("Received:", line_data)
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
            for i, lead in enumerate(self.leads):
                if len(self.data[lead]) > 0:
                    if len(self.data[lead]) < self.buffer_size:
                        data = np.full(self.buffer_size, np.nan)
                        data[-len(self.data[lead]):] = self.data[lead]
                    else:
                        data = np.array(self.data[lead])
                    centered = data - np.nanmean(data)
                    self.lines[i].set_ydata(centered)
                    self.axs[i].set_ylim(-400, 400)
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
        # Go back to dashboard (assumes dashboard is at index 0)
        self.stacked_widget.setCurrentIndex(0)

    def show_connection_warning(self, extra_msg=""):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Connection Required")
        msg.setText("❤️ Please select a COM port and baud rate.\n\nStay healthy!" + ("\n\n" + extra_msg if extra_msg else ""))
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def show_main_menu(self):  
        self.clear_content()

    def save_ecg(self):
        self.show_save_ecg()

    def open_ecg(self):
        self.show_open_ecg()

    def working_mode(self):
        self.show_working_mode()

    def printer_setup(self):
        self.show_printer_setup()

    def set_filter(self):
        self.open_filter_settings()

    def system_setup(self):
        self.show_system_setup()

    def load_default(self):
        self.show_factory_default_config()

    def version_info(self):
        self.show_version_info()

    def factory_maintain(self):
        self.show_maintain_password()

    def exit_app(self):
        self.show_exit_page()

    def clear_content(self):
        for i in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

    def show_save_ecg(self):
        # ...user's full show_save_ecg code here...
        QMessageBox.information(self, "Save ECG", "Save ECG UI would show here.")

    def show_open_ecg(self):
        # ...user's full show_open_ecg code here...
        QMessageBox.information(self, "Open ECG", "Open ECG UI would show here.")

    def show_working_mode(self):
        # ...user's full show_working_mode code here...
        QMessageBox.information(self, "Working Mode", "Working Mode UI would show here.")

    def show_printer_setup(self):
        # ...user's full show_printer_setup code here...
        QMessageBox.information(self, "Printer Setup", "Printer Setup UI would show here.")

    def open_filter_settings(self):
        # ...user's full open_filter_settings code here...
        QMessageBox.information(self, "Set Filter", "Set Filter UI would show here.")

    def show_system_setup(self):
        # ...user's full show_system_setup code here...
        QMessageBox.information(self, "System Setup", "System Setup UI would show here.")

    def show_factory_default_config(self):
        # ...user's full show_factory_default_config code here...
        QMessageBox.information(self, "Load Default", "Load Default UI would show here.")

    def show_version_info(self):
        # ...user's full show_version_info code here...
        QMessageBox.information(self, "Version", "Version UI would show here.")

    def show_maintain_password(self):
        # ...user's full show_maintain_password code here...
        QMessageBox.information(self, "Factory Maintain", "Factory Maintain UI would show here.")

    def show_exit_page(self):
        # ...user's full show_exit_page code here...
        self.close()

    def show_sequential_view(self):
        from ecg.lead_sequential_view import LeadSequentialView
        win = LeadSequentialView(self.leads, self.data, buffer_size=500)
        win.show()
        self._sequential_win = win

    def show_all_leads_overlay(self):
        from ecg.lead_sequential_view import LeadSequentialView
        self._all_leads_win = LeadSequentialView.show_all_leads(self.leads, self.data, buffer_size=500)