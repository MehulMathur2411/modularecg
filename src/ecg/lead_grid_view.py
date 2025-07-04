from PyQt5.QtWidgets import QWidget, QGridLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

class LeadGridView(QWidget):
    def __init__(self, leads, data, rows=3, cols=4, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{rows} x {cols} ECG Lead Grid")
        self.setStyleSheet("background: #000;")
        layout = QGridLayout(self)
        idx = 0
        for r in range(rows):
            for c in range(cols):
                if idx < len(leads):
                    fig = Figure(figsize=(2, 1.5), facecolor='#000')
                    ax = fig.add_subplot(111)
                    ax.set_facecolor('#000')
                    ax.tick_params(axis='x', colors='#00ff00')
                    ax.tick_params(axis='y', colors='#00ff00')
                    for spine in ax.spines.values():
                        spine.set_visible(False)
                    ax.set_ylabel(leads[idx], color='#00ff00', fontsize=10, labelpad=6)
                    ax.set_xticks([])
                    ax.set_yticks([])
                    d = data.get(leads[idx], [])
                    if d:
                        y = np.array(d[-500:]) - np.mean(d[-500:])
                        x = np.arange(len(y))
                        ax.plot(x, y, color="#00ff00", lw=1)
                    canvas = FigureCanvas(fig)
                    layout.addWidget(canvas, r, c)
                    idx += 1
        self.setLayout(layout)
