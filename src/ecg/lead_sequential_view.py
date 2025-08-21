from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QDialog, QFrame
from PyQt5.QtCore import Qt, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

class LorenzDialog(QDialog):
    def __init__(self, lead_name, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Lorenz (Poincaré) Plot - {lead_name}")
        self.setStyleSheet("background: #000;")
        self.resize(400, 400)
        layout = QVBoxLayout(self)
        fig = Figure(figsize=(4, 4), facecolor='#000')
        ax = fig.add_subplot(111)
        ax.set_facecolor('#000')
        ax.tick_params(axis='x', colors='#ff6600')
        ax.tick_params(axis='y', colors='#ff6600')
        for spine in ax.spines.values():
            spine.set_color('#ff6600')
        ax.set_title("Lorenz Plot", color='#ff6600')
        ax.set_xlabel("x[n]", color='#ff6600')
        ax.set_ylabel("x[n+1]", color='#ff6600')
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)
        # Compute Lorenz points
        d = np.array(data)
        if len(d) > 1:
            d = d - np.mean(d)
            x = d[:-1]
            y = d[1:]
            ax.scatter(x, y, s=6, c="#00ff00", alpha=0.7)
            ax.set_xlim(np.min(x)-50, np.max(x)+50)
            ax.set_ylim(np.min(y)-50, np.max(y)+50)
        else:
            ax.text(0.5, 0.5, "Not enough data", color="#ff6600", ha="center", va="center")
        canvas.draw()

class LeadSequentialView(QWidget):
    def __init__(self, leads, data, buffer_size=500, parent=None):
        super().__init__(parent)

        # Initialize settings manager
        from utils.settings_manager import SettingsManager
        self.settings_manager = SettingsManager()

        self.setWindowTitle("ECG Lead Viewer - Sequential")
        self.setStyleSheet("background: #000;")
        self.resize(1000, 400)
        self.leads = leads
        self.data = data
        self.buffer_size = buffer_size
        self.current_idx = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(100)

        layout = QVBoxLayout(self)
        self.lead_label = QLabel()
        self.lead_label.setAlignment(Qt.AlignHCenter)
        self.lead_label.setStyleSheet("color: #00ff00; font-size: 28px; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(self.lead_label)
        self.fig = Figure(facecolor='#000', figsize=(8, 4))
        self.ax = self.fig.add_subplot(211)
        self.ax.set_facecolor('#000')
        self.ax.tick_params(axis='x', colors='#00ff00')
        self.ax.tick_params(axis='y', colors='#00ff00')
        for spine in self.ax.spines.values():
            spine.set_visible(False)
        self.line, = self.ax.plot([], [], color="#00ff00", lw=2)
        # --- Mini-graphs for all 12 leads ---
        self.mini_figs = []
        self.mini_axes = []
        self.mini_lines = []
        self.mini_canvases = []
        mini_layout = QHBoxLayout()
        for i, l in enumerate(self.leads):
            mini_fig = Figure(figsize=(1.2, 1), facecolor='#000')
            mini_ax = mini_fig.add_subplot(111)
            mini_ax.set_facecolor('#000')
            mini_ax.tick_params(axis='x', colors='#00ff00', labelsize=6)
            mini_ax.tick_params(axis='y', colors='#00ff00', labelsize=6)
            for spine in mini_ax.spines.values():
                spine.set_visible(False)
            mini_ax.set_xticks([])
            mini_ax.set_yticks([])
            mini_ax.set_title(l, color='#ff6600', fontsize=8)
            mini_line, = mini_ax.plot([], [], color="#00ff00", lw=1)
            mini_canvas = FigureCanvas(mini_fig)
            mini_canvas.setFixedSize(80, 50)
            # --- Make mini-graph clickable ---
            def make_onclick(idx):
                def onclick(event):
                    lead_name = self.leads[idx]
                    d = self.data.get(lead_name, [])
                    dlg = LorenzDialog(lead_name, d, self)
                    dlg.exec_()
                return onclick
            mini_canvas.mpl_connect('button_press_event', make_onclick(i))
            mini_layout.addWidget(mini_canvas)
            self.mini_figs.append(mini_fig)
            self.mini_axes.append(mini_ax)
            self.mini_lines.append(mini_line)
            self.mini_canvases.append(mini_canvas)
        layout.addLayout(mini_layout)
        # --- Card-style metrics row (only for 2-lead view) ---
        if len(self.leads) == 2:
            metrics_layout = QHBoxLayout()
            metrics_layout.setSpacing(32)
            metrics_layout.setContentsMargins(32, 20, 32, 20)
            self.metric_cards = []
            metric_names = ["PR Int", "QRS D", "QTc In", "Arrhy"]
            for name in metric_names:
                card = QWidget()
                card.setStyleSheet("""
                    background: #fff;
                    border: 2.5px solid #ff6600;
                    border-radius: 20px;
                    min-width: 170px;
                    min-height: 110px;
                    max-height: 130px;
                """)
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(12, 12, 12, 12)
                label = QLabel(name)
                label.setAlignment(Qt.AlignHCenter)
                label.setStyleSheet("color: #ff6600; font-size: 22px; font-weight: bold;")
                value = QLabel("--")
                value.setAlignment(Qt.AlignHCenter)
                value.setStyleSheet("color: #222; font-size: 38px; font-weight: bold;")
                card_layout.addWidget(label)
                card_layout.addWidget(value)
                metrics_layout.addWidget(card)
                self.metric_cards.append((label, value))
            metrics_row = QWidget()
            metrics_row.setLayout(metrics_layout)
            metrics_row.setFixedHeight(150)
            layout.addWidget(metrics_row)
        # ...existing code...

    def update_plot(self):
        lead = self.leads[self.current_idx]
        self.lead_label.setText(f"Lead: {lead}")
        data = self.data.get(lead, [])

        # Apply gain setting to the displayed data
        gain_factor = self.settings_manager.get_wave_gain() / 10.0

        # Main plot (scrolling window)
        if data:
            x = np.arange(len(data))
            centered = np.array(data) - np.mean(data)
            self.line.set_data(x, centered)

            ylim = 500 * gain_factor
            self.ax.set_xlim(0, max(len(data)-1, 1))
            ymin = np.min(centered) - ylim * 0.2
            ymax = np.max(centered) + ylim * 0.2
            if ymin == ymax:
                ymin, ymax = -ylim, ylim
            self.ax.set_ylim(ymin, ymax)
        else:
            self.line.set_data([], [])
            self.ax.set_xlim(0, 1)
            self.ax.set_ylim(-500, 500)
        # --- Mini-graphs for all 12 leads ---
        n_points = 60
        for i, l in enumerate(self.leads):
            d = self.data.get(l, [])
            mini_line = self.mini_lines[i]
            mini_ax = self.mini_axes[i]
            if d:
                d = np.array(d) - np.mean(d)
                d = d * gain_factor 
                if len(d) > n_points:
                    idxs = np.linspace(0, len(d)-1, n_points).astype(int)
                    d_lorez = d[idxs]
                    x_lorez = np.linspace(0, len(d)-1, n_points)
                else:
                    d_lorez = d
                    x_lorez = np.arange(len(d))
                mini_line.set_data(x_lorez, d_lorez)
                mini_ax.set_xlim(0, max(len(d)-1, 1))
                ylim = 500 * gain_factor
                ymin = np.min(d_lorez) - ylim * 0.2
                ymax = np.max(d_lorez) + ylim * 0.2
                if ymin == ymax:
                    ymin, ymax = -ylim, ylim
                mini_ax.set_ylim(ymin, ymax)
            else:
                mini_line.set_data([], [])
                mini_ax.set_xlim(0, 1)
                mini_ax.set_ylim(-500, 500)
            self.mini_canvases[i].draw()
        # ...existing code...

    def prev_lead(self):
        self.current_idx = (self.current_idx - 1) % len(self.leads)
        self.update_plot()

    def next_lead(self):
        self.current_idx = (self.current_idx + 1) % len(self.leads)
        self.update_plot()
