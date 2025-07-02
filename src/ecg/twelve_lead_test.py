import sys
import time
import numpy as np
from pyparsing import line
import serial
import serial.tools.list_ports
import csv
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QGroupBox, QFileDialog,
    QStackedLayout, QGridLayout, QSizePolicy, QMessageBox, QFormLayout, QLineEdit
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from ecg.recording import ECGMenu

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
        self.grid_widget = QWidget()
        self.detailed_widget = QWidget()
        self.page_stack = QStackedLayout()
        self.page_stack.addWidget(self.grid_widget)
        self.page_stack.addWidget(self.detailed_widget)
        self.setLayout(self.page_stack)

        self.test_name = test_name
        self.leads = self.LEADS_MAP[test_name]
        self.buffer_size = 80
        self.data = {lead: [] for lead in self.leads}
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.serial_reader = None
        self.stacked_widget = stacked_widget
        self.lines = []
        self.axs = []
        self.canvases = []

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
            ("Exit", self.show_exit_page)
        ]
        for text, handler in menu_buttons:
            btn = QPushButton(text)
            btn.setFixedHeight(36)
            btn.clicked.connect(handler)
            menu_layout.addWidget(btn)
        menu_layout.addStretch(1)

        main_vbox = QVBoxLayout()
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
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.export_pdf_btn)
        btn_layout.addWidget(self.export_csv_btn)
        btn_layout.addWidget(self.back_btn)
        btn_layout.addWidget(self.ecg_plot_btn)
        main_vbox.addLayout(btn_layout)

        self.start_btn.clicked.connect(self.start_acquisition)
        self.stop_btn.clicked.connect(self.stop_acquisition)
        self.export_pdf_btn.clicked.connect(self.export_pdf)
        self.export_csv_btn.clicked.connect(self.export_csv)
        self.back_btn.clicked.connect(self.go_back)
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

    def show_12to1_graph(self):
        win = QWidget()
        win.setWindowTitle("12:1 ECG Graph")
        layout = QVBoxLayout(win)
        ordered_leads = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]
        self._12to1_lines = {}
        self._12to1_axes = {}
        for lead in ordered_leads:
            group = QGroupBox(lead)
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
        if self.timer.isActive():
            self._12to1_timer.start(100)
    
    def update_12to1_graph(self):
        for lead, line in self._12to1_lines.items():
            data = self.data.get(lead, [])
            ax = self._12to1_axes[lead]
            if data:
                if len(data) < self.buffer_size:
                    plot_data = np.full(self.buffer_size, np.nan)
                    plot_data[-len(data):] = data
                else:
                    plot_data = np.array(data[-self.buffer_size:])
                centered = plot_data - np.nanmean(plot_data)
                line.set_ydata(centered)
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
        fig = Figure(facecolor='#000')
        ax = fig.add_subplot(111)
        ax.set_facecolor('#000')
        # No fixed buffer_size for xlim, will update dynamically
        line, = ax.plot([], [], color=color, lw=2)
        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(canvas)
        self.detailed_widget.setLayout(layout)
        self.detailed_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.page_stack.setCurrentIndex(1)
        self._detailed_timer = QTimer(self)
        def update_detailed_plot():
            data = get_lead_data()
            if data and len(data) > 0:
                x = np.arange(len(data))
                centered = np.array(data) - np.mean(data)
                line.set_data(x, centered)
                ax.set_xlim(0, max(len(data)-1, 1))
                ymin = np.min(centered) - 100
                ymax = np.max(centered) + 100
                if ymin == ymax:
                    ymin, ymax = -500, 500
                ax.set_ylim(ymin, ymax)
            else:
                line.set_data([], [])
                ax.set_xlim(0, 1)
                ax.set_ylim(-500, 500)
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
            vbox = QVBoxLayout(group)
            fig = Figure(facecolor='#000', figsize=(6, 2.5))
            ax = fig.add_subplot(111)
            ax.set_facecolor('#000')
            ax.set_ylim(0, 999)
            ax.set_xlim(0, self.buffer_size)
            line, = ax.plot([0]*self.buffer_size, color='#00ff99', lw=1.5)
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
        self.stop_acquisition()
        if self.serial_reader:
            self.serial_reader.close()
        if self.stacked_widget:
            self.stacked_widget.setCurrentIndex(1)

    def show_connection_warning(self, extra_msg=""):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Connection Required")
        msg.setText("❤️ Please select a COM port and baud rate.\n\nStay healthy!" + ("\n\n" + extra_msg if extra_msg else ""))
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def show_save_ecg(self):
        QMessageBox.information(self, "Save ECG", "Save ECG clicked.")

    def show_open_ecg(self):
        QMessageBox.information(self, "Open ECG", "Open ECG clicked.")

    def show_working_mode(self):
        QMessageBox.information(self, "Working Mode", "Working Mode clicked.")

    def show_printer_setup(self):
        QMessageBox.information(self, "Printer Setup", "Printer Setup clicked.")

    def open_filter_settings(self):
        QMessageBox.information(self, "Set Filter", "Set Filter clicked.")

    def show_system_setup(self):
        QMessageBox.information(self, "System Setup", "System Setup clicked.")

    def show_factory_default_config(self):
        QMessageBox.information(self, "Load Default", "Load Default clicked.")

    def show_version_info(self):
        QMessageBox.information(self, "Version", "Version clicked.")

    def show_maintain_password(self):
        QMessageBox.information(self, "Factory Maintain", "Factory Maintain clicked.")

    def show_exit_page(self):
        self.close()

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication, QStackedWidget

    app = QApplication(sys.argv)
    stacked = QStackedWidget()
    # Use "12 Lead ECG Test" as the test_name
    ecg_page = ECGTestPage("12 Lead ECG Test", stacked)
    stacked.addWidget(ecg_page)
    stacked.setCurrentWidget(ecg_page)
    stacked.resize(1200, 900)
    stacked.show()
    sys.exit(app.exec_())