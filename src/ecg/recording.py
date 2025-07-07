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
    def __init__(self, parent=None, dashboard=None):
        super().__init__(parent)
        self.dashboard = dashboard
        self.setStyleSheet("background: black;")
        layout = QVBoxLayout(self)
        self.canvases = []
        self.lines = []
        self.ecg_buffers = [np.zeros(5000) for _ in range(12)]
        self.ptrs = [0 for _ in range(12)]
        self.window_size = 1000 
        self.lead_names = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]
        for i in range(12):
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
            ax.axvline(x=0, color='white', linestyle='--', linewidth=1)
            ax.set_title("", color='white', fontsize=12, loc='left')
            line, = ax.plot(self.data[i], color='lime', lw=1)
            canvas = FigureCanvas(fig)
            layout.addWidget(canvas)
            self.canvases.append(canvas)
            self.lines.append(line)
        self.setLayout(layout)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(30)  # ~33 FPS

    def update_data(self):
        for i in range(12):
            # Slide a window over the simulated ECG for animation
            self.ptrs[i] = (self.ptrs[i] + 1) % (len(self.ecg_buffers[i]) - self.window_size)
            window = self.ecg_buffers[i][self.ptrs[i]:self.ptrs[i]+self.window_size]
            self.lines[i].set_ydata(window)

            # --- P peak detection and labeling for each lead ---
            if len(window) >= 1000:
                try:
                    # Placeholder for PQRST detection logic
                    p_peaks = np.array([100, 200, 300])  # Dummy values for illustration
                    ax = self.canvases[i].figure.axes[0]
                    main_line = ax.lines[0]
                    ax.lines = [main_line]
                    # Remove old text labels
                    for txt in ax.texts:
                        txt.remove()
                    # Plot green markers and labels for P peaks only
                    if len(p_peaks) > 0:
                        ax.plot(p_peaks, window[p_peaks], 'o', color='green', label='P', markersize=8, zorder=10)
                        for idx in p_peaks:
                            ax.text(idx, window[idx]+0.3, 'P', color='green', fontsize=10, ha='center', va='bottom', zorder=11)
                    # Optional: update legend
                    handles, labels = ax.get_legend_handles_labels()
                    by_label = dict(zip(labels, handles))
                    ax.legend(by_label.values(), by_label.keys(), loc='upper right', fontsize=8)
                except Exception as e:
                    print(f"ECG analysis error in lead {self.lead_names[i]}:", e)
            self.canvases[i].draw()

        # --- Lead II metrics and dashboard update (as before) ---
        lead_ii_signal = self.ecg_buffers[1][self.ptrs[1]:self.ptrs[1]+self.window_size]
        if len(lead_ii_signal) >= 1000:
            try:
                # Placeholder for Lead II metrics calculation
                pr_interval = 0.2  # Dummy value
                qrs_duration = 0.08  # Dummy value
                qt_interval = 0.4  # Dummy value
                qtc_interval = 0.42  # Dummy value
                qrs_axis = "--"  # Placeholder
                st_segment = "--"  # Placeholder
                with open("ecg_metrics_output.txt", "w") as f:
                    f.write("# ECG Metrics Output\n")
                    f.write("# Format: PR_interval(ms), QRS_duration(ms), QTc_interval(ms), QRS_axis, ST_segment\n")
                    f.write(f"{pr_interval*1000}, {qrs_duration*1000}, {qtc_interval*1000}, {qrs_axis}, {st_segment}\n")
                    # Dummy peak lists
                    f.write(f"P_peaks: {list(np.array([100, 200, 300]))}\n")
                    f.write(f"Q_peaks: {list(np.array([150, 250, 350]))}\n")
                    f.write(f"R_peaks: {list(np.array([180, 280, 380]))}\n")
                    f.write(f"S_peaks: {list(np.array([210, 310, 410]))}\n")
                    f.write(f"T_peaks: {list(np.array([240, 340, 440]))}\n")
                if self.dashboard and hasattr(self.dashboard, "update_ecg_metrics"):
                    self.dashboard.update_ecg_metrics(pr_interval, qrs_duration, qtc_interval, qrs_axis, st_segment)
                    QTimer.singleShot(0, self.dashboard.repaint)
            except Exception as e:
                print("ECG analysis error:", e)

    def __init__(self, parent=None, dashboard=None):
        super().__init__(parent)
        self.dashboard = dashboard
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
        self.setLayout(layout)

        # def update_data(self):
        #     for i in range(12):
        #         self.data[i] = np.roll(self.data[i], -1)
        #         self.data[i][-1] = 1.5 * np.sin(np.linspace(0, 2 * np.pi, 500)[(self.data[i].size-1)%500]) + 0.2 * np.random.randn()
        #         self.lines[i].set_ydata(self.data[i])

        #         # --- PQRST detection and labeling for each lead ---
        #         lead_signal = self.data[i]
        #         if len(lead_signal) >= 500:
        #             try:
        #                 signals, info = nk.ecg_process(lead_signal, sampling_rate=500)
        #                 p_peaks = info.get("ECG_P_Peaks", [])
        #                 q_peaks = info.get("ECG_Q_Peaks", [])
        #                 r_peaks = info.get("ECG_R_Peaks", [])
        #                 s_peaks = info.get("ECG_S_Peaks", [])
        #                 t_peaks = info.get("ECG_T_Peaks", [])
        #                 ax = self.canvases[i].figure.axes[0]
        #                 main_line = ax.lines[0]
        #                 ax.lines = [main_line]  # Keep only the main ECG line
        #                # ...inside your update_data loop for each lead...
        #                 for idxs, label in zip([p_peaks, q_peaks, r_peaks, s_peaks, t_peaks], ['P', 'Q', 'R', 'S', 'T']):
        #                     if len(idxs) > 0:
        #                         # Plot marker (optional, can keep original color if you want)
        #                         ax.plot(idxs, lead_signal[idxs], 'o', color='green', label=label, markersize=8, zorder=10)
        #                         # Add green text labels above each marker
        #                         for idx in idxs:
        #                             ax.text(idx, lead_signal[idx]+0.3, label, color='green', fontsize=8, ha='center', va='bottom', zorder=11)
        #                 # Deduplicate legend labels
        #                 handles, labels = ax.get_legend_handles_labels()
        #                 by_label = dict(zip(labels, handles))
        #                 ax.legend(by_label.values(), by_label.keys(), loc='upper right', fontsize=8)
        #             except Exception as e:
        #                 print(f"ECG analysis error in lead {self.lead_names[i]}:", e)
        #         self.canvases[i].draw()

        #     # --- Lead II metrics and dashboard update (as before) ---
        #     lead_ii_signal = self.data[1]
        #     if len(lead_ii_signal) >= 500:
        #         try:
        #             signals, info = nk.ecg_process(lead_ii_signal, sampling_rate=500)
        #             p_peaks = info.get("ECG_P_Peaks", [])
        #             q_peaks = info.get("ECG_Q_Peaks", [])
        #             r_peaks = info.get("ECG_R_Peaks", [])
        #             s_peaks = info.get("ECG_S_Peaks", [])
        #             t_peaks = info.get("ECG_T_Peaks", [])
        #             pr_interval = (q_peaks[0] - p_peaks[0]) / 500 if p_peaks and q_peaks else None
        #             qrs_duration = (s_peaks[0] - q_peaks[0]) / 500 if q_peaks and s_peaks else None
        #             qt_interval = (t_peaks[0] - q_peaks[0]) / 500 if t_peaks and q_peaks else None
        #             rr = np.diff(r_peaks) / 500 if len(r_peaks) > 1 else [1]
        #             qtc_interval = qt_interval / np.sqrt(np.mean(rr)) if qt_interval else None
        #             qrs_axis = "--"  # Placeholder
        #             st_segment = "--"  # Placeholder
        #             # Write metrics and peak indices to txt file
        #             with open("ecg_metrics_output.txt", "w") as f:
        #                 f.write("# ECG Metrics Output\n")
        #                 f.write("# Format: PR_interval(ms), QRS_duration(ms), QTc_interval(ms), QRS_axis, ST_segment\n")
        #                 f.write(f"{pr_interval*1000 if pr_interval else '--'}, {qrs_duration*1000 if qrs_duration else '--'}, {qtc_interval*1000 if qtc_interval else '--'}, {qrs_axis}, {st_segment}\n")
        #                 f.write(f"P_peaks: {list(p_peaks)}\nQ_peaks: {list(q_peaks)}\nR_peaks: {list(r_peaks)}\nS_peaks: {list(s_peaks)}\nT_peaks: {list(t_peaks)}\n")
        #             if self.dashboard and hasattr(self.dashboard, "update_ecg_metrics"):
        #                 self.dashboard.update_ecg_metrics(pr_interval, qrs_duration, qtc_interval, qrs_axis, st_segment)
        #                 from PyQt5.QtCore import QTimer
        #                 QTimer.singleShot(0, self.dashboard.repaint)
        #         except Exception as e:
        #             print("ECG analysis error:", e)

class ECGMenu(QGroupBox):
    def __init__(self, parent=None, dashboard=None):
        super().__init__("Menu", parent)
        self.dashboard = dashboard
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
        self.lead12_window = Lead12BlackPage(dashboard=self.dashboard)
        self.lead12_window.setWindowTitle("12:1 ECG Leads")
        self.lead12_window.resize(1600, 300)
        self.lead12_window.show()
    def on_exit(self):
        pass