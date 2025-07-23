from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QGridLayout, QCalendarWidget, QTextEdit,
    QDialog, QLineEdit, QComboBox, QFormLayout, QMessageBox, QSizePolicy, QStackedWidget
)
from PyQt5.QtGui import QFont, QPixmap, QMovie
from PyQt5.QtCore import Qt, QTimer
import sys
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.animation import FuncAnimation
import math
import os
import json
import matplotlib.image as mpimg
from dashboard.chatbot_dialog import ChatbotDialog

class MplCanvas(FigureCanvas):
    def __init__(self, width=4, height=2, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)

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
    
class DashboardHomeWidget(QWidget):
    def __init__(self):
        super().__init__()

class Dashboard(QWidget):
    def __init__(self, username=None, role=None):
        super().__init__()
        self.username = username
        self.role = role
        self.medical_mode = False
        self.dark_mode = False
        self.setWindowTitle("ECG Monitor Dashboard")
        self.setGeometry(100, 100, 1300, 900)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.setWindowState(Qt.WindowMaximized)
        self.center_on_screen()
        # --- Plasma GIF background ---
        self.bg_label = QLabel(self)
        self.bg_label.setGeometry(0, 0, 1300, 900)
        self.bg_label.lower()
        movie = QMovie("plasma.gif")
        self.bg_label.setMovie(movie)
        movie.start()
        # --- Central stacked widget for in-place navigation ---
        self.page_stack = QStackedWidget(self)
        # --- Dashboard main page widget ---
        self.dashboard_page = DashboardHomeWidget()
        dashboard_layout = QVBoxLayout(self.dashboard_page)
        dashboard_layout.setSpacing(20)
        dashboard_layout.setContentsMargins(20, 20, 20, 20)
        # --- Header ---
        header = QHBoxLayout()
        logo = QLabel("ECG Monitor")
        logo.setFont(QFont("Arial", 20, QFont.Bold))
        logo.setStyleSheet("color: #ff6600;")
        header.addWidget(logo)
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(18, 18)
        self.status_dot.setStyleSheet("border-radius: 9px; background: gray; border: 2px solid #fff;")
        header.addWidget(self.status_dot)
        self.update_internet_status()
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_internet_status)
        self.status_timer.start(3000)
        self.medical_btn = QPushButton("Medical Mode")
        self.medical_btn.setCheckable(True)
        self.medical_btn.setStyleSheet("background: #00b894; color: white; border-radius: 10px; padding: 4px 18px;")
        self.medical_btn.clicked.connect(self.toggle_medical_mode)
        header.addWidget(self.medical_btn)
        self.dark_btn = QPushButton("Dark Mode")
        self.dark_btn.setCheckable(True)
        self.dark_btn.setStyleSheet("background: #222; color: #fff; border-radius: 10px; padding: 4px 18px;")
        self.dark_btn.clicked.connect(self.toggle_dark_mode)
        header.addWidget(self.dark_btn)
        header.addStretch()
        self.user_label = QLabel(f"{self.username or 'User'}\n{self.role or ''}")
        self.user_label.setFont(QFont("Arial", 10))
        self.user_label.setAlignment(Qt.AlignRight)
        header.addWidget(self.user_label)
        self.sign_btn = QPushButton("Sign Out")
        self.sign_btn.setStyleSheet("background: #e74c3c; color: white; border-radius: 10px; padding: 4px 18px;")
        self.sign_btn.clicked.connect(self.handle_sign_out)
        header.addWidget(self.sign_btn)
        dashboard_layout.addLayout(header)
        # --- Greeting and Date Row ---
        greet_row = QHBoxLayout()
        from datetime import datetime
        hour = datetime.now().hour
        if hour < 12:
            greeting = "Good Morning"
        elif hour < 18:
            greeting = "Good Afternoon"
        else:
            greeting = "Good Evening"
        greet = QLabel(f"<span style='font-size:18pt;font-weight:bold;'>{greeting}, {self.username or 'User'}</span><br><span style='color:#888;'>Welcome to your ECG dashboard</span>")
        greet.setFont(QFont("Arial", 14))
        greet_row.addWidget(greet)
        greet_row.addStretch()
        date_btn = QPushButton("ECG Lead Test 12")
        date_btn.setStyleSheet("background: #ff6600; color: white; border-radius: 16px; padding: 8px 24px;")
        date_btn.clicked.connect(self.go_to_lead_test)
        greet_row.addWidget(date_btn)

        # --- Add Chatbot Button ---
        chatbot_btn = QPushButton("AI Chatbot")
        chatbot_btn.setStyleSheet("background: #2453ff; color: white; border-radius: 16px; padding: 8px 24px;")
        chatbot_btn.clicked.connect(self.open_chatbot_dialog)
        greet_row.addWidget(chatbot_btn)

        dashboard_layout.addLayout(greet_row)

        # --- Main Grid ---
        grid = QGridLayout()
        grid.setSpacing(20)
        # --- Heart Rate Card ---
        heart_card = QFrame()
        heart_card.setStyleSheet("background: white; border-radius: 16px;")
        heart_layout = QVBoxLayout(heart_card)
        heart_label = QLabel("Live Heart Rate Overview")
        heart_label.setFont(QFont("Arial", 14, QFont.Bold))
        heart_img = QLabel()
        # Use a portable path for the heart image asset
        heart_img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "her.png")
        heart_img_path = os.path.abspath(heart_img_path)
        # print(f"Pratyaksh Heart image path: {heart_img_path}")  # Debugging line to check the path
        # print(f"Pratyaksh Heart image exists: {os.path.exists(heart_img_path)}")  # Check if the file exists
        self.heart_pixmap = QPixmap(heart_img_path)
        self.heart_base_size = 220
        heart_img.setFixedSize(self.heart_base_size + 20, self.heart_base_size + 20)
        heart_img.setAlignment(Qt.AlignCenter)
        heart_img.setPixmap(self.heart_pixmap.scaled(self.heart_base_size, self.heart_base_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        heart_layout.addWidget(heart_label)
        heart_layout.addWidget(heart_img)
        heart_layout.addWidget(QLabel("Stress Level: Low"))
        heart_layout.addWidget(QLabel("Average Variability: 90ms"))
        grid.addWidget(heart_card, 0, 0, 2, 1)
        # --- Heartbeat Animation ---
        self.heart_img = heart_img
        self.heartbeat_phase = 0
        self.heartbeat_timer = QTimer(self)
        self.heartbeat_timer.timeout.connect(self.animate_heartbeat)
        self.heartbeat_timer.start(30)  # ~33 FPS
        # --- Patient Body Analysis Cards ---
        analysis_card = QFrame()
        analysis_card.setStyleSheet("background: white; border-radius: 16px;")
        analysis_layout = QHBoxLayout(analysis_card)
        for title, value, unit in [
            ("Glucose Level", "127", "mg/dl"),
            ("Cholesterol Level", "164", "mg"),
            ("Paracetamol", "35", "%")
        ]:
            box = QVBoxLayout()
            lbl = QLabel(title)
            lbl.setFont(QFont("Arial", 10, QFont.Bold))
            val = QLabel(f"{value} {unit}")
            val.setFont(QFont("Arial", 16, QFont.Bold))
            box.addWidget(lbl)
            box.addWidget(val)
            analysis_layout.addLayout(box)
        grid.addWidget(analysis_card, 0, 1, 1, 2)
        # --- ECG Recording (Animated Chart) ---
        ecg_card = QFrame()
        ecg_card.setStyle
        ecg_layout = QVBoxLayout(ecg_card)
        ecg_label = QLabel("ECG Recording")
        ecg_label.setFont(QFont("Arial", 12, QFont.Bold))
        ecg_layout.addWidget(ecg_label)
        self.ecg_canvas = MplCanvas(width=4, height=2)
        self.ecg_canvas.axes.set_facecolor("#eee")
        self.ecg_canvas.axes.set_xticks([])
        self.ecg_canvas.axes.set_yticks([])
        self.ecg_canvas.axes.set_title("Lead II", fontsize=10)
        ecg_layout.addWidget(self.ecg_canvas)
        grid.addWidget(ecg_card, 1, 1)
        # --- Total Visitors (Pie Chart) ---
        visitors_card = QFrame()
        visitors_card.setStyleSheet("background: white; border-radius: 16px;")
        visitors_layout = QVBoxLayout(visitors_card)
        visitors_label = QLabel("Total Visitors")
        visitors_label.setFont(QFont("Arial", 12, QFont.Bold))
        visitors_layout.addWidget(visitors_label)
        pie_canvas = MplCanvas(width=2.5, height=2.5)
        pie_data = [30, 25, 30, 15]
        pie_labels = ["December", "November", "October", "September"]
        pie_colors = ["#ff6600", "#00b894", "#636e72", "#fdcb6e"]
        wedges, texts, autotexts = pie_canvas.axes.pie(
            pie_data, labels=pie_labels, autopct='%1.0f%%', colors=pie_colors, startangle=90
        )
        pie_canvas.axes.set_aspect('equal')
        visitors_layout.addWidget(pie_canvas)
        grid.addWidget(visitors_card, 1, 2)
        # --- Schedule Card ---
        schedule_card = QFrame()
        schedule_card.setStyleSheet("background: white; border-radius: 16px;")
        schedule_layout = QVBoxLayout(schedule_card)
        schedule_label = QLabel("Schedule")
        schedule_label.setFont(QFont("Arial", 12, QFont.Bold))
        schedule_layout.addWidget(schedule_label)
        cal = QCalendarWidget()
        cal.setFixedHeight(120)
        # Highlight last ECG usage date in red
        from PyQt5.QtGui import QTextCharFormat, QColor
        last_ecg_file = 'last_ecg_date.json'
        import datetime
        today = datetime.date.today()
        # Try to load last ECG date from file
        last_ecg_date = None
        if os.path.exists(last_ecg_file):
            with open(last_ecg_file, 'r') as f:
                try:
                    data = json.load(f)
                    last_ecg_date = data.get('last_ecg_date')
                except Exception:
                    last_ecg_date = None
        if last_ecg_date:
            try:
                y, m, d = map(int, last_ecg_date.split('-'))
                last_date = Qt.QDate(y, m, d)
                fmt = QTextCharFormat()
                fmt.setBackground(QColor('red'))
                fmt.setForeground(QColor('white'))
                cal.setDateTextFormat(last_date, fmt)
            except Exception:
                pass
        schedule_layout.addWidget(cal)
        grid.addWidget(schedule_card, 2, 0)
        # --- Issue Found Card ---
        issue_card = QFrame()
        issue_card.setStyleSheet("background: white; border-radius: 16px;")
        issue_layout = QVBoxLayout(issue_card)
        issue_label = QLabel("Issue Found")
        issue_label.setFont(QFont("Arial", 12, QFont.Bold))
        issue_layout.addWidget(issue_label)
        issues_text = (
            "1. Heart Rate\n"
            "   • Tachycardia: Abnormally fast heart rate.\n"
            "   • Bradycardia: Abnormally slow heart rate.\n\n"
            "2. Heart Rhythm\n"
            "   • Normal Sinus Rhythm: Regular rhythm from the sinoatrial node.\n"
            "   • Arrhythmias: Irregular rhythms (e.g., atrial fibrillation, ventricular tachycardia, heart block).\n\n"
            "3. Electrical Conduction\n"
            "   • Heart block (1st, 2nd, 3rd degree), bundle branch blocks (right/left).\n\n"
            "4. Cardiac Size and Hypertrophy\n"
            "   • Enlarged chambers or hypertrophy (e.g., left ventricular hypertrophy).\n\n"
            "5. Ischemia and Infarction\n"
            "   • Ischemia: ST depression.\n"
            "   • Infarction: ST elevation, pathological Q waves.\n\n"
            "6. Electrolyte Abnormalities\n"
            "   • Hyperkalemia: Peaked T waves.\n"
            "   • Hypokalemia: Flattened/inverted T waves, U waves.\n"
            "   • Calcium: QT interval changes.\n\n"
            "7. Pericardial Disease\n"
            "   • Pericarditis: Diffuse ST elevation, PR depression.\n\n"
            "8. Pacemaker Activity\n"
            "   • Pacemaker function and capture.\n\n"
            "9. Drug Effects\n"
            "   • Digitalis, antiarrhythmics: Characteristic ECG changes.\n\n"
            "10. Cardiac Arrest Patterns\n"
            "   • Asystole, ventricular fibrillation, PEA."
        )
        issues_box = QTextEdit()
        issues_box.setReadOnly(True)
        issues_box.setText(issues_text)
        issues_box.setStyleSheet("background: #f7f7f7; border: none; font-size: 12px;")
        issues_box.setMinimumHeight(180)
        issue_layout.addWidget(issues_box)
        grid.addWidget(issue_card, 2, 1, 1, 2)
        # --- ECG Monitor Metrics Cards ---
        metrics_card = QFrame()
        metrics_card.setStyleSheet("background: white; border-radius: 16px;")
        metrics_layout = QHBoxLayout(metrics_card)
        # Store metric labels for live update
        self.metric_labels = {}
        metric_info = [
            ("Heart Rate", "--", "bpm", "heart_rate"),
            ("PR Interval", "--", "ms", "pr_interval"),
            ("QRS Duration", "--", "ms", "qrs_duration"),
            ("QTc Interval", "--", "ms", "qtc_interval"),
            ("QRS Axis", "--", "°", "qrs_axis"),
            ("ST Segment", "--", "", "st_segment"),
        ]
        for title, value, unit, key in metric_info:
            box = QVBoxLayout()
            lbl = QLabel(title)
            lbl.setFont(QFont("Arial", 10, QFont.Bold))
            val = QLabel(f"{value} {unit}")
            val.setFont(QFont("Arial", 16, QFont.Bold))
            box.addWidget(lbl)
            box.addWidget(val)
            metrics_layout.addLayout(box)
            self.metric_labels[key] = val  # Store reference for live update
        grid.addWidget(metrics_card, 0, 1, 1, 2)
        dashboard_layout.addLayout(grid)
        
        self.generate_report_btn = QPushButton("Generate Report")
        self.generate_report_btn.setStyleSheet("background: #ff6600; color: white; border-radius: 10px; padding: 8px 24px; font-size: 16px; font-weight: bold;")
        self.generate_report_btn.clicked.connect(self.generate_pdf_report)
        dashboard_layout.addWidget(self.generate_report_btn, alignment=Qt.AlignRight)
        
        # --- ECG Animation Setup ---
        self.ecg_x = np.linspace(0, 2, 500)
        self.ecg_y = 1000 + 200 * np.sin(2 * np.pi * 2 * self.ecg_x) + 50 * np.random.randn(500)
        self.ecg_line, = self.ecg_canvas.axes.plot(self.ecg_x, self.ecg_y, color="#ff6600")
        self.anim = FuncAnimation(self.ecg_canvas.figure, self.update_ecg, interval=50, blit=True)
        # Add dashboard_page to stack
        self.page_stack.addWidget(self.dashboard_page)
        # --- ECG Test Page ---
        from ecg.twelve_lead_test import ECGTestPage
        self.ecg_test_page = ECGTestPage("12 Lead ECG Test", self.page_stack)
        self.ecg_test_page.dashboard_callback = self.update_ecg_metrics
        self.page_stack.addWidget(self.ecg_test_page)
        # --- Main layout ---
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.page_stack)
        self.setLayout(main_layout)
        self.page_stack.setCurrentWidget(self.dashboard_page)

        # Add a content_frame for ECGMenu to use
        self.content_frame = QFrame(self)
        self.content_frame.setStyleSheet("background: transparent; border: none;")
        main_layout.addWidget(self.content_frame)

        self.setLayout(main_layout)
        self.page_stack.setCurrentWidget(self.dashboard_page)

    def open_chatbot_dialog(self):
        dlg = ChatbotDialog(self)
        dlg.exec_()

    def update_ecg(self, frame):
        import os, json
        lead_ii_file = 'lead_ii_live.json'
        if os.path.exists(lead_ii_file):
            try:
                with open(lead_ii_file, 'r') as f:
                    data = json.load(f)
                if isinstance(data, list) and len(data) > 10:
                    arr = np.array(data)
                    arr = arr - np.mean(arr)
                    arr = arr + 1000  # Center vertically
                    if len(arr) < len(self.ecg_x):
                        arr = np.pad(arr, (len(self.ecg_x)-len(arr), 0), 'constant', constant_values=(1000,))
                    self.ecg_line.set_ydata(arr[-len(self.ecg_x):])
                    return [self.ecg_line]
            except Exception as e:
                print("Error reading lead_ii_live.json:", e)
        # Fallback: mock wave
        self.ecg_y = np.roll(self.ecg_y, -1)
        self.ecg_y[-1] = 1000 + 200 * np.sin(2 * np.pi * 2 * self.ecg_x[-1] + frame/10) + 50 * np.random.randn()
        self.ecg_line.set_ydata(self.ecg_y)
        return [self.ecg_line]
    
    def update_ecg_metrics(self, intervals):
        if 'Heart_Rate' in intervals and intervals['Heart_Rate'] is not None:
            self.metric_labels['heart_rate'].setText(
                f"{int(round(intervals['Heart_Rate']))} bpm" if isinstance(intervals['Heart_Rate'], (int, float)) else str(intervals['Heart_Rate'])
            )
        if 'PR' in intervals and intervals['PR'] is not None:
            self.metric_labels['pr_interval'].setText(
                f"{int(round(intervals['PR']))} ms" if isinstance(intervals['PR'], (int, float)) else str(intervals['PR'])
            )
        if 'QRS' in intervals and intervals['QRS'] is not None:
            self.metric_labels['qrs_duration'].setText(
                f"{int(round(intervals['QRS']))} ms" if isinstance(intervals['QRS'], (int, float)) else str(intervals['QRS'])
            )
        if 'QTc' in intervals and intervals['QTc'] is not None:
            if isinstance(intervals['QTc'], (int, float)) and intervals['QTc'] >= 0:
                self.metric_labels['qtc_interval'].setText(f"{int(round(intervals['QTc']))} ms")
            else:
                self.metric_labels['qtc_interval'].setText("-- ms")
        if 'QRS_axis' in intervals and intervals['QRS_axis'] is not None:
            self.metric_labels['qrs_axis'].setText(str(intervals['QRS_axis']))
        if 'ST' in intervals and intervals['ST'] is not None:
            self.metric_labels['st_segment'].setText(
                f"{int(round(intervals['ST']))} ms" if isinstance(intervals['ST'], (int, float)) else str(intervals['ST'])
            )
            
    def generate_pdf_report(self):
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        import datetime
        from ecg.ecg_report_generator import generate_ecg_html_report

        # Gather details from dashboard
        HR = self.metric_labels['heart_rate'].text().split()[0] if 'heart_rate' in self.metric_labels else "--"
        PR = self.metric_labels['pr_interval'].text().split()[0] if 'pr_interval' in self.metric_labels else "--"
        QRS = self.metric_labels['qrs_duration'].text().split()[0] if 'qrs_duration' in self.metric_labels else "--"
        QT = self.metric_labels['qt_interval'].text().split()[0] if 'qt_interval' in self.metric_labels else "--"
        QTc = self.metric_labels['qtc_interval'].text().split()[0] if 'qtc_interval' in self.metric_labels else "--"
        QRS_axis = self.metric_labels['qrs_axis'].text() if 'qrs_axis' in self.metric_labels else "--"
        ST = self.metric_labels['st_segment'].text().split()[0] if 'st_segment' in self.metric_labels else "--"

        # Patient details (replace with actual data if available)
        first_name = getattr(self, "first_name", "")
        last_name = getattr(self, "last_name", "")
        age = getattr(self, "age", "")
        gender = getattr(self, "gender", "")
        test_name = "12 Lead ECG"
        date_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        abnormal_report = 'N'
        text = obstext = qrstext = ""
        uId = testId = dataId = "NA"

        # --- Save all lead graphs as image ---
        lead_img_paths = {}
        ordered_leads = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]

        # Get ECGTestPage instance and its figures

        bg_img_path = "ecg_bgimg.png" # Path to background image

        ecg_test_page = self.ecg_test_page
        for lead in ordered_leads:
            fig = ecg_test_page.get_lead_figure(lead)  # You may need to implement get_lead_figure
            if fig:
                ax = fig.axes[0]  # Get the main axes
                # Hide axis ticks and labels
                ax.set_xticks([])
                ax.set_yticks([])
                ax.set_xlabel("")
                ax.set_ylabel("")
                # Add background image ONLY for PDF export
                if os.path.exists(bg_img_path):
                    img = mpimg.imread(bg_img_path)
                    ax.imshow(img, aspect='auto', extent=ax.get_xlim() + ax.get_ylim(), zorder=0)
                img_path = f"lead_{lead}.png"
                fig.savefig(img_path, bbox_inches='tight', dpi=250)
                lead_img_paths[lead] = img_path
                # Remove the background image so it doesn't affect UI
                for img in list(ax.images):
                    img.remove()

        # --- Generate HTML report with graph image ---
        html = generate_ecg_html_report(
            HR=HR,
            PR=float(PR) if PR.replace('.', '', 1).isdigit() else 0,
            QRS=float(QRS) if QRS.replace('.', '', 1).isdigit() else 0,
            QT=float(QT) if QT.replace('.', '', 1).isdigit() else 0,
            QTc=float(QTc) if QTc.replace('.', '', 1).isdigit() else 0,
            ST=float(ST) if ST.replace('.', '', 1).isdigit() else 0,
            test_name=test_name,
            date_time=date_time,
            first_name=first_name,
            last_name=last_name,
            age=age,
            gender=gender,
            abnormal_report=abnormal_report,
            text=text,
            obstext=obstext,
            qrstext=qrstext,
            uId=uId,
            testId=testId,
            dataId=dataId,
            lead_img_paths=lead_img_paths,   # <-- Pass all 12 leads here
            QRS_axis=QRS_axis
        )
        
        # Save HTML report
        with open("ecg_report.html", "w") as f:
            f.write(html)

        # Ask user where to save PDF
        path, _ = QFileDialog.getSaveFileName(self, "Save ECG Report as PDF", "", "PDF Files (*.pdf)")
        if not path:
            return

        # Convert HTML to PDF using Qt's QTextDocument
        from PyQt5.QtGui import QTextDocument
        from PyQt5.QtPrintSupport import QPrinter
        doc = QTextDocument()
        doc.setHtml(html)
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(path)
        doc.print_(printer)
        QMessageBox.information(self, "Report Generated", f"ECG report saved as PDF:\n{path}")

        # Clean up temp image
        for img_path in lead_img_paths.values():
            if img_path and os.path.exists(img_path):
                try:
                    os.remove(img_path)
                except Exception:
                    pass

    def animate_heartbeat(self):
        # Heartbeat effect: scale up and down in a sine wave pattern
        beat = 1 + 0.13 * math.sin(self.heartbeat_phase) + 0.07 * math.sin(2 * self.heartbeat_phase)
        size = int(self.heart_base_size * beat)
        self.heart_img.setPixmap(self.heart_pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.heartbeat_phase += 0.18  # Controls speed of beat
        if self.heartbeat_phase > 2 * math.pi:
            self.heartbeat_phase -= 2 * math.pi
    def handle_sign(self):
        if self.sign_btn.text() == "Sign In":
            dialog = SignInDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                role, name = dialog.get_user_info()
                if not name.strip():
                    QMessageBox.warning(self, "Input Error", "Please enter your name.")
                    return
                self.user_label.setText(f"{name}\n{role}")
                self.sign_btn.setText("Sign Out")
        else:
            self.user_label.setText("Not signed in")
            self.sign_btn.setText("Sign In")
    def handle_sign_out(self):
        self.user_label.setText("Not signed in")
        self.sign_btn.setText("Sign In")
    def go_to_lead_test(self):
        self.page_stack.setCurrentWidget(self.ecg_test_page)
    def go_to_dashboard(self):
        self.page_stack.setCurrentWidget(self.dashboard_page)
    def update_internet_status(self):
        import socket
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            self.status_dot.setStyleSheet("border-radius: 9px; background: #00e676; border: 2px solid #fff;")
            self.status_dot.setToolTip("Connected to Internet")
        except Exception:
            self.status_dot.setStyleSheet("border-radius: 9px; background: #e74c3c; border: 2px solid #fff;")
            self.status_dot.setToolTip("No Internet Connection")
    def toggle_medical_mode(self):
        self.medical_mode = not self.medical_mode
        if self.medical_mode:
            # Medical color coding: blue/green/white
            self.setStyleSheet("QWidget { background: #e3f6fd; } QFrame { background: #f8fdff; border-radius: 16px; } QLabel { color: #006266; }")
            self.medical_btn.setText("Normal Mode")
            self.medical_btn.setStyleSheet("background: #0984e3; color: white; border-radius: 10px; padding: 4px 18px;")
        else:
            self.setStyleSheet("")
            self.medical_btn.setText("Medical Mode")
            self.medical_btn.setStyleSheet("background: #00b894; color: white; border-radius: 10px; padding: 4px 18px;")
    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            self.setStyleSheet("""
                QWidget { background: #181818; color: #fff; }
                QFrame { background: #232323 !important; border-radius: 16px; color: #fff; border: 2px solid #fff; }
                QLabel { color: #fff; }
                QPushButton { background: #333; color: #ff6600; border-radius: 10px; }
                QPushButton:checked { background: #ff6600; color: #fff; }
                QCalendarWidget QWidget { background: #232323; color: #fff; }
                QCalendarWidget QAbstractItemView { background: #232323; color: #fff; selection-background-color: #444; selection-color: #ff6600; }
                QTextEdit { background: #232323; color: #fff; border-radius: 12px; border: 2px solid #fff; }
            """)
            self.dark_btn.setText("Light Mode")
            # Set matplotlib canvas backgrounds to dark
            self.ecg_canvas.axes.set_facecolor("#232323")
            self.ecg_canvas.figure.set_facecolor("#232323")
            for child in self.findChildren(QFrame):
                child.setStyleSheet("background: #232323; border-radius: 16px; color: #fff; border: 2px solid #fff;")
                for canvas in child.findChildren(MplCanvas):
                    canvas.axes.set_facecolor("#232323")
                    canvas.figure.set_facecolor("#232323")
                    canvas.draw()
                for cal in child.findChildren(QCalendarWidget):
                    cal.setStyleSheet("background: #232323; color: #fff; border-radius: 12px; border: 2px solid #fff;")
                for txt in child.findChildren(QTextEdit):
                    txt.setStyleSheet("background: #232323; color: #fff; border-radius: 12px; border: 2px solid #fff;")
            # Remove all margins and spacing for a seamless dark look
            self.layout().setContentsMargins(0, 0, 0, 0)
            self.layout().setSpacing(10)
        else:
            self.setStyleSheet("")
            self.dark_btn.setText("Dark Mode")
            self.ecg_canvas.axes.set_facecolor("#eee")
            self.ecg_canvas.figure.set_facecolor("#fff")
            for child in self.findChildren(QFrame):
                child.setStyleSheet("")
                for canvas in child.findChildren(MplCanvas):
                    canvas.axes.set_facecolor("#fff")
                    canvas.figure.set_facecolor("#fff")
                    canvas.draw()
                for cal in child.findChildren(QCalendarWidget):
                    cal.setStyleSheet("")
                for txt in child.findChildren(QTextEdit):
                    txt.setStyleSheet("")
            self.layout().setContentsMargins(20, 20, 20, 20)
            self.layout().setSpacing(20)
    def center_on_screen(self):
        qr = self.frameGeometry()
        cp = QApplication.desktop().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())