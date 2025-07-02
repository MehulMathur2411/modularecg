from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QPushButton

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
    def on_exit(self):
        pass