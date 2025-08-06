from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QPushButton, QWidget, QLabel, QMessageBox, QFrame, QGridLayout, QLineEdit, QComboBox, QHBoxLayout, QDialog, QRadioButton, QApplication
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from PyQt5.QtCore import QTimer, Qt
from utils.settings_manager import SettingsManager

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
            line, = ax.plot(np.zeros(self.window_size), color='lime', lw=1)
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

class ECGMenu(QGroupBox):
    def __init__(self, parent=None, dashboard=None):
        super().__init__("", parent)
        self.dashboard = dashboard
        self.settings_manager = SettingsManager()
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
        self.show_save_ecg()
    def on_open_ecg(self):
        self.open_ecg_window()
    def on_working_mode(self):
        self.show_working_mode()
    def on_printer_setup(self):
        self.show_printer_setup()
    def on_set_filter(self):
        self.set_filter_setup()
    def on_system_setup(self):
        self.show_system_setup()
    def on_load_default(self):
        self.show_load_default()
    def on_version_info(self):
        self.show_version_info()
    def on_factory_maintain(self):
        self.show_factory_maintain()
    def on_exit(self):
        self.show_exit()


    # ----------------------- Save ECG ------------------------------------


    def show_save_ecg(self):
        # Create a modal dialog for the save form
        dialog = QDialog(self.dashboard if self.dashboard else self)
        dialog.setWindowTitle("Save ECG Details")
        dialog.setModal(True)
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Save ECG Details")
        title.setStyleSheet("font: bold 14pt Arial;")
        layout.addWidget(title)

        form_frame = QFrame()
        form_layout = QGridLayout(form_frame)
        labels = ["Organisation", "Doctor", "Patient Name"]
        entries = {}

        for i, label in enumerate(labels):
            lbl = QLabel(label)
            lbl.setStyleSheet("font: bold 12pt Arial;")
            form_layout.addWidget(lbl, i, 0)

            entry = QLineEdit()
            entry.setStyleSheet("font: 12pt Arial;")
            entry.setFixedWidth(250)
            form_layout.addWidget(entry, i, 1)
            entries[label] = entry

        # Age
        lbl_age = QLabel("Age")
        lbl_age.setStyleSheet("font: bold 12pt Arial;")
        form_layout.addWidget(lbl_age, 3, 0)

        age_entry = QLineEdit()
        age_entry.setStyleSheet("font: 12pt Arial;")
        age_entry.setFixedWidth(100)
        form_layout.addWidget(age_entry, 3, 1)
        entries["Age"] = age_entry

        # Gender
        lbl_gender = QLabel("Gender")
        lbl_gender.setStyleSheet("font: bold 12pt Arial;")
        form_layout.addWidget(lbl_gender, 4, 0)

        gender_menu = QComboBox()
        gender_menu.addItems(["Select", "Male", "Female", "Other"])
        gender_menu.setStyleSheet("font: 12pt Arial; background-color: skyblue;")
        gender_menu.setFixedWidth(120)
        form_layout.addWidget(gender_menu, 4, 1)

        layout.addWidget(form_frame)

        # Submit logic
        def submit_details():
            values = {label: entries[label].text().strip() for label in labels + ["Age"]}
            values["Gender"] = gender_menu.currentText()

            if any(v == "" for v in values.values()) or values["Gender"] == "Select":
                QMessageBox.warning(dialog, "Missing Data", "Please fill all the fields and select gender.")
                return

            try:
                with open("ecg_data.txt", "a") as file:
                    file.write(f"{values['Organisation']}, {values['Doctor']}, {values['Patient Name']}, {values['Age']}, {values['Gender']}\n")

                # --- Store Patient info in Dashboard for PDF report ---
                if self.dashboard:
                    # Split patient name into first and last if possible
                    patient_name = values['Patient Name']
                    name_parts = patient_name.split()
                    first_name = name_parts[0] if len(name_parts) > 0 else ""
                    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                    self.dashboard.first_name = first_name
                    self.dashboard.last_name = last_name
                    self.dashboard.age = values['Age']
                    self.dashboard.gender = values['Gender']

                QMessageBox.information(dialog, "Saved", "Details saved to ecg_data.txt successfully.")
                dialog.accept()
            except Exception as e:
                QMessageBox.critical(dialog, "Error", f"Failed to save: {e}")

        # Buttons inside button frame
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("font: 12pt Arial; background-color: green; color: white;")
        save_btn.setFixedWidth(150)
        save_btn.clicked.connect(submit_details)
        button_layout.addWidget(save_btn)

        exit_btn = QPushButton("Exit")
        exit_btn.setStyleSheet("font: 12pt Arial; background-color: red; color: white;")
        exit_btn.setFixedWidth(150)
        exit_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(exit_btn)

        layout.addWidget(button_frame)

        dialog.exec_()


    # ----------------------- Open ECG ------------------------------------


    def open_ecg_window(self):
        dialog = QDialog(self.dashboard if self.dashboard else self)
        dialog.setWindowTitle("Open ECG")
        dialog.setModal(True)
        dialog.setMinimumWidth(600)

        container = QFrame()
        container.setStyleSheet("background-color: white; border: 1px solid gray;")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Open ECG")
        title.setStyleSheet("font: bold 16pt Arial; background-color: white;")
        title.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(title)

        # ---------------------- Top 4 Equal Boxes ----------------------
        top_info_frame = QFrame()
        top_info_frame.setStyleSheet("background-color: white;")
        container_layout.addWidget(top_info_frame)

        box_frame = QFrame()
        box_frame.setStyleSheet("background-color: white; border: 1px solid black;")
        box_layout = QHBoxLayout(box_frame)
        box_layout.setContentsMargins(0, 0, 0, 0)
        top_info_frame.setLayout(QVBoxLayout())
        top_info_frame.layout().addWidget(box_frame)

        def create_cell(text):
            lbl = QLabel(text)
            lbl.setStyleSheet("font: 9pt Arial; background-color: white;")
            lbl.setFixedWidth(130)
            lbl.setAlignment(Qt.AlignCenter)
            return lbl

        def vertical_divider(width=3):
            frame = QFrame()
            frame.setFixedWidth(width)
            frame.setStyleSheet("background-color: black;")
            frame.setFrameShape(QFrame.VLine)
            frame.setFrameShadow(QFrame.Sunken)
            return frame

        box_layout.addWidget(create_cell("Capacity"))
        box_layout.addWidget(vertical_divider())

        box_layout.addWidget(create_cell("30000 case"))
        box_layout.addWidget(vertical_divider())

        box_layout.addWidget(create_cell("Used:"))
        box_layout.addWidget(vertical_divider())

        box_layout.addWidget(create_cell("0 case"))

        # ---------------------- Header Row ----------------------------
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: white; border: 1px solid black;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(5, 5, 5, 5)

        def create_header_cell(text):
            lbl = QLabel(text)
            lbl.setStyleSheet("font: bold 10pt Arial; background-color: white;")
            lbl.setFixedWidth(150)
            lbl.setAlignment(Qt.AlignCenter)
            return lbl

        header_layout.addWidget(create_header_cell("ID"))
        header_layout.addWidget(vertical_divider(1))

        header_layout.addWidget(create_header_cell("Gender"))
        header_layout.addWidget(vertical_divider(1))

        header_layout.addWidget(create_header_cell("Age"))
        container_layout.addWidget(header_frame)

        # ---------------------- Data Rows ----------------------------
        rows_frame = QFrame()
        rows_frame.setStyleSheet("background-color: white;")
        rows_layout = QVBoxLayout(rows_frame)

        def create_row_cell(text):
            lbl = QLabel(text)
            lbl.setStyleSheet("font: 10pt Arial; background-color: white;")
            lbl.setFixedWidth(150)
            lbl.setAlignment(Qt.AlignCenter)
            return lbl

        for _ in range(10):
            row_outer = QFrame()
            row_outer.setStyleSheet("background-color: white; border: 1px solid gray;")
            row_layout = QHBoxLayout(row_outer)
            row_layout.setContentsMargins(5, 5, 5, 5)

            row_layout.addWidget(create_row_cell("-----------"))
            row_layout.addWidget(vertical_divider(1))

            row_layout.addWidget(create_row_cell("-----------"))
            row_layout.addWidget(vertical_divider(1))

            row_layout.addWidget(create_row_cell("-----------"))
            rows_layout.addWidget(row_outer)

        container_layout.addWidget(rows_frame)

        # ---------------------- Bottom Buttons ------------------------
        button_frame = QFrame()
        button_frame.setStyleSheet("background-color: white;")
        button_layout = QGridLayout(button_frame)
        container_layout.addWidget(button_frame)

        active_button = {"value": ""}
        buttons_dict = {}

        def update_button_styles():
            for name, btn in buttons_dict.items():
                if active_button["value"] == name:
                    btn.setStyleSheet("background-color: skyblue; font: 10pt Arial;")
                else:
                    btn.setStyleSheet("")

        button_config = [
            ("Up", 0, 0), ("Del This", 0, 1), ("Rec", 0, 2),
            ("Down", 1, 0), ("Del All", 1, 1), ("Exit", 1, 2)
        ]

        for text, r, c in button_config:
            def make_handler(name=text):
                def handler():
                    if name == "Exit":
                        dialog.accept()
                    else:
                        active_button["value"] = name
                        update_button_styles()
                return handler

            btn = QPushButton(text)
            btn.setFixedWidth(150)
            btn.setFixedHeight(30)
            btn.setStyleSheet("font: 10pt Arial;")
            btn.clicked.connect(make_handler())
            button_layout.addWidget(btn, r, c)
            buttons_dict[text] = btn

        # Set up dialog layout
        dialog_layout = QVBoxLayout()
        dialog.setLayout(dialog_layout)
        dialog_layout.addWidget(container)

        dialog.exec_()


    # ----------------------- Working Mode ------------------------------------
    

    def show_working_mode(self):
        dialog = QDialog(self.dashboard if self.dashboard else self)
        dialog.setWindowTitle("Working Mode")
        dialog.setModal(True)
        dialog.setMinimumWidth(600)

        container = QFrame()
        container.setStyleSheet("background-color: white; border: 1px solid black;")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Working Mode")
        title.setStyleSheet("font: bold 14pt Arial; background-color: white;")
        container_layout.addWidget(title)

        # Helper to add radio button sections
        def add_section(title, options, variable):
            group_box = QGroupBox(title)
            group_box.setStyleSheet("font: bold 12pt Arial; background-color: white;")
            hbox = QHBoxLayout(group_box)
            for text, val in options:
                btn = QRadioButton(text)
                btn.setStyleSheet("font: 11pt Arial; background-color: white;")
                btn.setChecked(variable['value'] == val)
                btn.toggled.connect(lambda checked, v=val: variable.update({'value': v}) if checked else None)
                hbox.addWidget(btn)
            container_layout.addWidget(group_box)

        # Load current settings
        wave_speed = {"value": self.settings_manager.get_setting("wave_speed")}
        wave_gain = {"value": self.settings_manager.get_setting("wave_gain")}
        lead_seq = {"value": self.settings_manager.get_setting("lead_sequence")}
        sampling = {"value": self.settings_manager.get_setting("sampling_mode")}
        demo_func = {"value": self.settings_manager.get_setting("demo_function")}
        storage = {"value": self.settings_manager.get_setting("storage")}

        add_section("Wave Speed", [("12.5mm/s", "12.5"), ("25.0mm/s", "25"), ("50.0mm/s", "50")], wave_speed)
        add_section("Wave Gain", [("2.5mm/mV", "2.5"), ("5mm/mV", "5"), ("10mm/mV", "10"), ("20mm/mV", "20")], wave_gain)
        add_section("Lead Sequence", [("Standard", "Standard"), ("Cabrera", "Cabrera")], lead_seq)
        add_section("Sampling Mode", [("Simultaneous", "Simultaneous"), ("Sequence", "Sequence")], sampling)
        add_section("Demo Function", [("Off", "Off"), ("On", "On")], demo_func)
        add_section("Priority Storage", [("U Disk", "U"), ("SD Card", "SD")], storage)

        # Example numeric entry with keypad
        hbox = QHBoxLayout()
        num_label = QLabel("Patient Count:")
        num_label.setStyleSheet("font: 12pt Arial;")
        hbox.addWidget(num_label)
        num_entry = QLineEdit()
        num_entry.setStyleSheet("font: 12pt Arial;")
        num_entry.setFixedWidth(100)
        hbox.addWidget(num_entry)
        keypad_btn = QPushButton("Keypad")
        keypad_btn.setStyleSheet("font: 11pt Arial;")
        hbox.addWidget(keypad_btn)
        container_layout.addLayout(hbox)

        # Connect keypad button
        keypad_btn.clicked.connect(lambda: self.open_keypad(num_entry, dialog))

        # Buttons
        btn_frame = QFrame()
        btn_layout = QHBoxLayout(btn_frame)

        ok_btn = QPushButton("OK")
        ok_btn.setFixedWidth(150)
        ok_btn.setStyleSheet("font: 12pt Arial;")
        ok_btn.clicked.connect(lambda: QMessageBox.information(dialog, "Saved", "Working mode settings saved"))
        btn_layout.addWidget(ok_btn)

        exit_btn = QPushButton("Exit")
        exit_btn.setFixedWidth(150)
        exit_btn.setStyleSheet("font: 12pt Arial; background-color: red; color: white;")
        exit_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(exit_btn)

        container_layout.addWidget(btn_frame)

        def save_working_mode_settings():
            # Save all settings
            self.settings_manager.set_setting("wave_speed", wave_speed["value"])
            self.settings_manager.set_setting("wave_gain", wave_gain["value"])
            self.settings_manager.set_setting("lead_sequence", lead_seq["value"])
            self.settings_manager.set_setting("sampling_mode", sampling["value"])
            self.settings_manager.set_setting("demo_function", demo_func["value"])
            self.settings_manager.set_setting("storage", storage["value"])
                
            # Terminal verification
            print(f"=== Working Mode Settings Saved ===")
            print(f"Wave Speed: {wave_speed['value']} mm/s")
            print(f"Wave Gain: {wave_gain['value']} mm/mV")
            print(f"Lead Sequence: {lead_seq['value']}")
            print(f"Sampling Mode: {sampling['value']}")
            print(f"Demo Function: {demo_func['value']}")
            print(f"Storage: {storage['value']}")
            print(f"================================")
                
            QMessageBox.information(dialog, "Saved", "Working mode settings saved successfully!")
            dialog.accept()
            
        ok_btn.clicked.connect(save_working_mode_settings)
        btn_layout.addWidget(ok_btn)

        dialog_layout = QVBoxLayout()
        dialog.setLayout(dialog_layout)
        dialog_layout.addWidget(container)

        dialog.exec_()
            

    def open_keypad(self, entry_widget, parent_dialog=None):
        keypad_dialog = QDialog(parent_dialog if parent_dialog else self.dashboard if self.dashboard else self)
        keypad_dialog.setWindowTitle("Keypad")
        keypad_dialog.setModal(True)
        keypad_dialog.setFixedWidth(200)

        keypad_layout = QGridLayout(keypad_dialog)
        keypad_layout.setSpacing(4)

        input_var = QLineEdit()
        input_var.setText(entry_widget.text())
        input_var.setReadOnly(True)
        input_var.setStyleSheet("font: 12pt Arial; background-color: white;")
        input_var.setAlignment(Qt.AlignRight)
        input_var.setFixedWidth(100)
        keypad_layout.addWidget(input_var, 0, 0, 1, 3)

        def update_display(val):
            input_var.setText(input_var.text() + val)

        def backspace():
            input_var.setText(input_var.text()[:-1])

        def clear():
            input_var.setText("")

        def apply_value():
            try:
                val = int(input_var.text())
                if 3 <= val <= 20:
                    entry_widget.setText(str(val))
                    keypad_dialog.accept()
                else:
                    QMessageBox.warning(keypad_dialog, "Invalid", "Please enter a value between 3 and 20.")
            except ValueError:
                QMessageBox.warning(keypad_dialog, "Invalid", "Please enter a numeric value.")

        # Digit buttons
        positions = [
            ('1', 1, 0), ('2', 1, 1), ('3', 1, 2),
            ('4', 2, 0), ('5', 2, 1), ('6', 2, 2),
            ('7', 3, 0), ('8', 3, 1), ('9', 3, 2),
            ('0', 4, 1)
        ]
        for (text, row, col) in positions:
            btn = QPushButton(text)
            btn.setFixedWidth(40)
            btn.setStyleSheet("font: 10pt Arial;")
            btn.clicked.connect(lambda _, t=text: update_display(t))
            keypad_layout.addWidget(btn, row, col)

        # ← Back
        btn_back = QPushButton("←")
        btn_back.setFixedWidth(40)
        btn_back.setStyleSheet("font: 10pt Arial;")
        btn_back.clicked.connect(backspace)
        keypad_layout.addWidget(btn_back, 4, 0)

        # Clear
        btn_clear = QPushButton("C")
        btn_clear.setFixedWidth(40)
        btn_clear.setStyleSheet("font: 10pt Arial;")
        btn_clear.clicked.connect(clear)
        keypad_layout.addWidget(btn_clear, 4, 2)

        # OK
        btn_ok = QPushButton("OK")
        btn_ok.setStyleSheet("font: bold 10pt Arial; background-color: green; color: white;")
        btn_ok.setFixedWidth(120)
        btn_ok.clicked.connect(apply_value)
        keypad_layout.addWidget(btn_ok, 5, 0, 1, 3)

        keypad_dialog.exec_()


    # ----------------------- Printer Setup ------------------------------------

    
    def show_printer_setup(self):
        dialog = QDialog(self.dashboard if self.dashboard else self)
        dialog.setWindowTitle("Rec Setup")
        dialog.setModal(True)
        dialog.setMinimumWidth(600)

        container = QFrame()
        container.setStyleSheet("background-color: white; border: 1px solid black;")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(30, 30, 30, 30)
        container_layout.setSpacing(14)

        title = QLabel("Rec Setup")
        title.setStyleSheet("font: bold 12pt Arial; background-color: white;")
        container_layout.addWidget(title)

        # Variables (dicts to mimic StringVar)
        auto_format = {"value": "3x4"}
        analysis_result = {"value": "on"}
        avg_wave = {"value": "on"}
        selected_rhythm_lead = {"value": "off"}
        sensitivity = {"value": "High"}

        def add_radiobutton_group(title, options, variable):
            group = QGroupBox(title)
            group.setStyleSheet("font: bold 12pt Arial; background-color: white;")
            layout = QHBoxLayout(group)
            layout.setSpacing(12)
            for opt in options:
                btn = QRadioButton(opt)
                btn.setStyleSheet("font: 10pt Arial; background-color: white;")
                btn.setChecked(variable["value"] == opt)
                btn.toggled.connect(lambda checked, val=opt: variable.update({"value": val}) if checked else None)
                layout.addWidget(btn)
            container_layout.addWidget(group)
            container_layout.addSpacing(6)

        add_radiobutton_group("Auto Rec Format", ["3x4", "3x2+2x3"], auto_format)
        add_radiobutton_group("Analysis Result", ["on", "off"], analysis_result)
        add_radiobutton_group("Avg Wave", ["on", "off"], avg_wave)

        # Rhythm Lead Group
        rhythm_group = QGroupBox("Rhythm Lead")
        rhythm_group.setStyleSheet("font: bold 12pt Arial; background-color: white;")
        rhythm_layout = QVBoxLayout(rhythm_group)
        row1 = QHBoxLayout()
        row2 = QHBoxLayout()
        row1.setSpacing(8)
        row2.setSpacing(8)
        lead_options = ["off", "I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]
        for i, lead in enumerate(lead_options):
            btn = QRadioButton(lead)
            btn.setStyleSheet("font: 10pt Arial; background-color: white;")
            btn.setChecked(selected_rhythm_lead["value"] == lead)
            btn.toggled.connect(lambda checked, val=lead: selected_rhythm_lead.update({"value": val}) if checked else None)
            if i < 7:
                row1.addWidget(btn)
            else:
                row2.addWidget(btn)
        rhythm_layout.addLayout(row1)
        rhythm_layout.addLayout(row2)
        container_layout.addWidget(rhythm_group)
        container_layout.addSpacing(6)

        # Auto Time
        time_group = QGroupBox("Automatic Time (sec/Lead)")
        time_group.setStyleSheet("font: bold 12pt Arial; background-color: white;")
        time_layout = QVBoxLayout(time_group)
        time_entry = QLineEdit()
        time_entry.setReadOnly(True)
        time_entry.setText("3")
        time_entry.setStyleSheet("font: 10pt Arial; background-color: white;")
        time_entry.setFixedWidth(60)
        time_entry.setAlignment(Qt.AlignLeft)
        time_layout.addWidget(time_entry)
        container_layout.addWidget(time_group)
        container_layout.addSpacing(6)

        # Sensitivity Group
        sens_group = QGroupBox("Analysis Sensitivity")
        sens_group.setStyleSheet("font: bold 12pt Arial; background-color: white;")
        sens_layout = QHBoxLayout(sens_group)
        sens_layout.setSpacing(12)
        for val in ["Low", "Med", "High"]:
            btn = QRadioButton(val)
            btn.setStyleSheet("font: 10pt Arial; background-color: white;")
            btn.setChecked(sensitivity["value"] == val)
            btn.toggled.connect(lambda checked, v=val: sensitivity.update({"value": v}) if checked else None)
            sens_layout.addWidget(btn)
        container_layout.addWidget(sens_group)
        container_layout.addSpacing(8)

        # Buttons
        btn_frame = QFrame()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setSpacing(16)

        ok_btn = QPushButton("OK")
        ok_btn.setFixedWidth(150)
        ok_btn.setStyleSheet("font: 12pt Arial;")
        ok_btn.clicked.connect(lambda: QMessageBox.information(dialog, "Saved", "Printer setup saved"))
        btn_layout.addWidget(ok_btn)

        exit_btn = QPushButton("Exit")
        exit_btn.setFixedWidth(150)
        exit_btn.setStyleSheet("font: 12pt Arial; background-color: red; color: white;")
        exit_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(exit_btn)

        container_layout.addWidget(btn_frame)

        dialog_layout = QVBoxLayout()
        dialog.setLayout(dialog_layout)
        dialog_layout.addWidget(container)

        dialog.exec_()


    # ----------------------- Set Filter Setup ------------------------------------
    

    def set_filter_setup(self):
        dialog = QDialog(self.dashboard if self.dashboard else self)
        dialog.setWindowTitle("Set Filter")
        dialog.setModal(True)
        dialog.setMinimumWidth(400)

        container = QFrame()
        container.setStyleSheet("background-color: white; border: 1px solid black;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(14)

        title = QLabel("Set Filter")
        title.setStyleSheet("font: bold 14pt Arial; background-color: white;")
        layout.addWidget(title)

        def add_filter_box(title_text, options, current_value_dict):
            group = QGroupBox(title_text)
            group.setStyleSheet("font: bold 12pt Arial; background-color: white;")
            hbox = QHBoxLayout(group)
            hbox.setSpacing(12)
            for text, val in options:
                btn = QRadioButton(text)
                btn.setStyleSheet("font: 11pt Arial; background-color: white;")
                btn.setChecked(current_value_dict["value"] == val)
                btn.toggled.connect(lambda checked, v=val: current_value_dict.update({"value": v}) if checked else None)
                hbox.addWidget(btn)
            layout.addWidget(group)
            layout.addSpacing(6)

        ac_var = {"value": "50Hz"}
        ac_options = [("off", "off"), ("50Hz", "50Hz"), ("60Hz", "60Hz")]
        add_filter_box("AC Filter", ac_options, ac_var)

        emg_var = {"value": "35Hz"}
        emg_options = [("25Hz", "25Hz"), ("35Hz", "35Hz"), ("45Hz", "45Hz"), ("75Hz", "75Hz"), ("100Hz", "100Hz"), ("150Hz", "150Hz")]
        add_filter_box("EMG Filter", emg_options, emg_var)

        dft_var = {"value": "0.5Hz"}
        dft_options = [("off", "off"), ("0.05Hz", "0.05Hz"), ("0.5Hz", "0.5Hz")]
        add_filter_box("DFT Filter", dft_options, dft_var)

        btn_frame = QHBoxLayout()
        btn_frame.setSpacing(16)
        ok_btn = QPushButton("OK")
        ok_btn.setFixedWidth(100)
        ok_btn.setStyleSheet("font: 11pt Arial;")
        ok_btn.clicked.connect(lambda: QMessageBox.information(dialog, "Saved", "Filter settings saved"))
        btn_frame.addWidget(ok_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedWidth(100)
        cancel_btn.setStyleSheet("font: 11pt Arial; background-color: red; color: white;")
        cancel_btn.clicked.connect(dialog.reject)
        btn_frame.addWidget(cancel_btn)

        layout.addLayout(btn_frame)

        dialog_layout = QVBoxLayout()
        dialog.setLayout(dialog_layout)
        dialog_layout.addWidget(container)

        dialog.exec_()


    # ----------------------- System Setup ------------------------------------


    def show_system_setup(self):
        dialog = QDialog(self.dashboard if self.dashboard else self)
        dialog.setWindowTitle("System Setup")
        dialog.setModal(True)
        dialog.setMinimumWidth(400)

        container = QFrame()
        container.setStyleSheet("background-color: white; border: 1px solid black;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(14)

        title = QLabel("System Setup")
        title.setStyleSheet("font: bold 14pt Arial; background-color: gray; color: white;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # --- BEAT VOL Block ---
        beat_vol_var = {"value": "on"}
        beat_frame = QGroupBox("BEAT VOL")
        beat_frame.setStyleSheet("font: bold 11pt Arial; background-color: #f0f0f0;")
        beat_inner = QHBoxLayout(beat_frame)
        beat_inner.setSpacing(12)
        def make_radio(text, val, var_dict):
            btn = QRadioButton(text)
            btn.setStyleSheet("font: 10pt Arial; background-color: white;")
            btn.setChecked(var_dict["value"] == val)
            btn.toggled.connect(lambda checked, v=val: var_dict.update({"value": v}) if checked else None)
            return btn
        beat_inner.addWidget(make_radio("Off", "off", beat_vol_var))
        beat_inner.addWidget(make_radio("On", "on", beat_vol_var))
        layout.addWidget(beat_frame)
        layout.addSpacing(8)

        # --- LANGUAGE Block ---
        lang_var = {"value": "English"}
        lang_frame = QGroupBox("LANGUAGE")
        lang_frame.setStyleSheet("font: bold 11pt Arial; background-color: #f0f0f0;")
        lang_inner = QHBoxLayout(lang_frame)
        lang_inner.setSpacing(12)
        lang_inner.addWidget(make_radio("English", "English", lang_var))
        lang_inner.addWidget(make_radio("Hindi", "Hindi", lang_var))
        layout.addWidget(lang_frame)
        layout.addSpacing(8)

        # --- Time Setup Button ---
        time_btn = QPushButton("Time Setup >>")
        time_btn.setFixedHeight(40)
        time_btn.setStyleSheet("font: 12pt Arial; background-color: navy; color: white;")
        layout.addWidget(time_btn)

        # --- OK/Cancel Buttons ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)
        ok_btn = QPushButton("OK")
        ok_btn.setFixedSize(120, 40)
        ok_btn.setStyleSheet("font: 11pt Arial;")
        def save_settings():
            QMessageBox.information(dialog, "Saved", f"Settings saved successfully!\nBEAT VOL: {beat_vol_var['value']}\nLANGUAGE: {lang_var['value']}")
            dialog.accept()
        ok_btn.clicked.connect(save_settings)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(120, 40)
        cancel_btn.setStyleSheet("font: 11pt Arial; background-color: red; color: white;")
        cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        dialog_layout = QVBoxLayout()
        dialog.setLayout(dialog_layout)
        dialog_layout.addWidget(container)

        # --- Time Setup Button Action ---
        time_btn.clicked.connect(lambda: self.show_time_setup_inside(dialog))

        dialog.exec_()

    def show_time_setup_inside(self, parent_dialog=None):
        dialog = QDialog(parent_dialog if parent_dialog else self.dashboard if self.dashboard else self)
        dialog.setWindowTitle("Time Setup")
        dialog.setModal(True)
        dialog.setMinimumWidth(350)

        container = QFrame()
        container.setStyleSheet("background-color: white; border: 1px solid black;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(12)

        title = QLabel("Time Setup")
        title.setStyleSheet("font: bold 13pt Arial; background-color: #f0f0f0;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        fields = [("Year", "2025"), ("Month", "06"), ("Day", "17"),
                ("Hour", "12"), ("Minute", "00"), ("Second", "00")]
        entries = {}

        for label, default in fields:
            row = QHBoxLayout()
            row.setSpacing(10)
            lbl = QLabel(label)
            lbl.setFixedWidth(70)
            lbl.setStyleSheet("font: bold 11pt Arial; background-color: white;")
            entry = QLineEdit()
            entry.setFixedWidth(100)
            entry.setText(default)
            entry.setStyleSheet("font: 11pt Arial;")
            entries[label] = entry
            row.addWidget(lbl)
            row.addWidget(entry)
            layout.addLayout(row)

        # Buttons
        btn_frame = QHBoxLayout()
        btn_frame.setSpacing(16)
        ok_btn = QPushButton("OK")
        ok_btn.setFixedSize(100, 36)
        ok_btn.setStyleSheet("font: 11pt Arial;")
        ok_btn.clicked.connect(lambda: [e.setDisabled(True) for e in entries.values()])
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(100, 36)
        cancel_btn.setStyleSheet("font: 11pt Arial; background-color: red; color: white;")
        cancel_btn.clicked.connect(dialog.reject)
        btn_frame.addWidget(ok_btn)
        btn_frame.addWidget(cancel_btn)
        layout.addLayout(btn_frame)

        dialog_layout = QVBoxLayout()
        dialog.setLayout(dialog_layout)
        dialog_layout.addWidget(container)

        dialog.exec_()


    # ----------------------- Load Default ------------------------------------


    def show_load_default(self):
        dialog = QDialog(self.dashboard if self.dashboard else self)
        dialog.setWindowTitle("Factory Default Config")
        dialog.setModal(True)
        dialog.setMinimumWidth(400)

        container = QFrame()
        container.setStyleSheet("background-color: white; border: 1px solid black;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("HINT")
        title.setStyleSheet("font: bold 14pt Arial; background-color: gray; color: white;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        label1 = QLabel("Adopt Factory Default Config?")
        label1.setStyleSheet("font: bold 12pt Arial; background-color: white;")
        label1.setAlignment(Qt.AlignCenter)
        layout.addWidget(label1)

        label2 = QLabel("The Previous Configure Will Be Lost!")
        label2.setStyleSheet("font: 10pt Arial; background-color: white; color: red;")
        label2.setAlignment(Qt.AlignCenter)
        layout.addWidget(label2)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(20)

        btn_no = QPushButton("No")
        btn_no.setFixedSize(100, 40)
        btn_no.setStyleSheet("font: 11pt Arial; background-color: navy; color: white;")
        btn_no.clicked.connect(dialog.reject)
        btn_row.addWidget(btn_no)

        btn_yes = QPushButton("Yes")
        btn_yes.setFixedSize(100, 40)
        btn_yes.setStyleSheet("font: 11pt Arial;")
        def apply_default_config():
            QMessageBox.information(dialog, "Done", "Factory defaults applied successfully.")
            dialog.accept()
        btn_yes.clicked.connect(apply_default_config)
        btn_row.addWidget(btn_yes)

        layout.addLayout(btn_row)

        dialog_layout = QVBoxLayout()
        dialog.setLayout(dialog_layout)
        dialog_layout.addWidget(container)

        dialog.exec_()



    # ----------------------- Version info ------------------------------------


    def show_version_info(self):
        dialog = QDialog(self.dashboard if self.dashboard else self)
        dialog.setWindowTitle("Version Info")
        dialog.setModal(True)
        dialog.setMinimumWidth(400)

        container = QFrame()
        container.setStyleSheet("background-color: white; border: 1px solid black;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(14)

        title = QLabel("Version Info")
        title.setStyleSheet("font: bold 14pt Arial; background-color: gray; color: white;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        inner_frame = QWidget()
        inner_layout = QGridLayout(inner_frame)
        inner_frame.setStyleSheet("background-color: white;")

        versions = [
            ("1. System Version:", "VER 1.6"),
            ("2. PM Version:", "VER 1.2"),
            ("3. KB Version:", "VER 3.22")
        ]

        for i, (label_text, version_text) in enumerate(versions):
            label = QLabel(label_text)
            label.setStyleSheet("font: bold 11pt Arial; background-color: white;")
            value = QLabel(version_text)
            value.setStyleSheet("font: 11pt Arial; background-color: white;")
            inner_layout.addWidget(label, i, 0)
            inner_layout.addWidget(value, i, 1)

        layout.addWidget(inner_frame)

        btn = QPushButton("Exit")
        btn.setFixedHeight(40)
        btn.setStyleSheet("font: 11pt Arial; background-color: skyblue;")
        btn.clicked.connect(dialog.accept)

        layout.addWidget(btn, alignment=Qt.AlignCenter)

        dialog_layout = QVBoxLayout()
        dialog.setLayout(dialog_layout)
        dialog_layout.addWidget(container)

        dialog.exec_()


    # ----------------------- Factory Maintain ------------------------------------


    def show_factory_maintain(self):
        dialog = QDialog(self.dashboard if self.dashboard else self)
        dialog.setWindowTitle("Factory Maintain")
        dialog.setModal(True)
        dialog.setMinimumWidth(400)

        container = QFrame()
        container.setStyleSheet("background-color: white; border: 1px solid black;")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(50, 50, 50, 50)
        container_layout.setSpacing(18)

        title = QLabel("Enter Maintain Password")
        title.setStyleSheet("font: bold 14pt Arial; background-color: gray; color: white;")
        title.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(title)

        form = QFrame()
        form_layout = QHBoxLayout()
        form.setLayout(form_layout)
        label = QLabel("Factory Key:")
        label.setStyleSheet("font: bold 12pt Arial; background-color: white;")
        form_layout.addWidget(label)

        key_input = QLineEdit()
        key_input.setText("0-999999")
        key_input.setStyleSheet("font: 12pt Arial; color: gray;")
        key_input.setAlignment(Qt.AlignCenter)
        form_layout.addWidget(key_input)

        # Placeholder text logic
        def on_entry_click():
            if key_input.text() == "0-999999":
                key_input.setText("")
                key_input.setStyleSheet("font: 12pt Arial; color: black;")
        def on_focus_out():
            if key_input.text().strip() == "":
                key_input.setText("0-999999")
                key_input.setStyleSheet("font: 12pt Arial; color: gray;")

        def focus_in_event(event):
            on_entry_click()
            QLineEdit.focusInEvent(key_input, event)

        def focus_out_event(event):
            on_focus_out()
            QLineEdit.focusOutEvent(key_input, event)

        key_input.focusInEvent = focus_in_event
        key_input.focusOutEvent = focus_out_event

        container_layout.addWidget(form)

        # Confirm button logic
        def on_confirm():
            val = key_input.text()
            if val.isdigit() and 0 <= int(val) <= 999999:
                QMessageBox.information(dialog, "Confirmed", f"Key Accepted: {val}")
                dialog.accept()
            else:
                QMessageBox.critical(dialog, "Invalid", "Please enter a valid number between 0 and 999999.")

        btn_frame = QVBoxLayout()
        confirm_btn = QPushButton("Confirm")
        confirm_btn.setFixedHeight(40)
        confirm_btn.setStyleSheet("font: 12pt Arial;")
        confirm_btn.clicked.connect(on_confirm)
        btn_frame.addWidget(confirm_btn)

        exit_btn = QPushButton("Exit")
        exit_btn.setFixedHeight(40)
        exit_btn.setStyleSheet("font: 12pt Arial; background-color: red; color: white;")
        exit_btn.clicked.connect(dialog.reject)
        btn_frame.addWidget(exit_btn)

        container_layout.addLayout(btn_frame)

        dialog_layout = QVBoxLayout()
        dialog.setLayout(dialog_layout)
        dialog_layout.addWidget(container)

        dialog.exec_()



    # ----------------------- Exit ------------------------------------



    def show_exit(self):
        dialog = QDialog(self.dashboard if self.dashboard else self)
        dialog.setWindowTitle("Exit Confirmation")
        dialog.setModal(True)
        dialog.setMinimumWidth(400)

        container = QFrame()
        container.setStyleSheet("background-color: white;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(24)

        label = QLabel("Do you really want to exit?")
        label.setStyleSheet("font: 16pt Arial; color: black; background-color: white;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        btn_yes = QPushButton("Yes - Exit")
        btn_yes.setStyleSheet("font: 12pt Arial; background-color: red; color: white;")
        btn_yes.setFixedWidth(200)

        def handle_exit():
            dialog.accept()
            if self.dashboard and hasattr(self.dashboard, "go_to_dashboard"):
                self.dashboard.go_to_dashboard()
            # Do NOT close or hide the ECG widget here!

        btn_yes.clicked.connect(handle_exit)
        layout.addWidget(btn_yes, alignment=Qt.AlignCenter)

        btn_no = QPushButton("No - Back")
        btn_no.setStyleSheet("font: 12pt Arial; background-color: green; color: white;")
        btn_no.setFixedWidth(200)
        btn_no.clicked.connect(dialog.reject)
        layout.addWidget(btn_no, alignment=Qt.AlignCenter)

        dialog_layout = QVBoxLayout()
        dialog.setLayout(dialog_layout)
        dialog_layout.addWidget(container)

        dialog.exec_()