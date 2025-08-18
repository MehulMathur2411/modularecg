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

    # @staticmethod
    # def show_all_leads(leads, data, buffer_size=500, parent=None):
    #     from PyQt5.QtGui import QPixmap, QPalette, QColor
    #     import os
        
    #     # Create a modal dialog instead of replacing the layout
    #     dialog = QDialog(parent)
    #     dialog.setWindowTitle("12-Lead ECG View - All Leads")
    #     dialog.setModal(True)
    #     dialog.resize(1200, 800)
    #     dialog.setStyleSheet("""
    #         QDialog {
    #             background: #000;
    #             border: 2px solid #ff6600;
    #             border-radius: 15px;
    #         }
    #     """)
        
    #     # Main layout for dialog
    #     main_layout = QVBoxLayout(dialog)
    #     main_layout.setContentsMargins(20, 20, 20, 20)
    #     main_layout.setSpacing(15)
        
    #     # Top control panel
    #     top_panel = QFrame()
    #     top_panel.setStyleSheet("""
    #         QFrame {
    #             background: rgba(255, 255, 255, 0.1);
    #             border: 2px solid rgba(255, 255, 255, 0.3);
    #             border-radius: 15px;
    #             padding: 10px;
    #         }
    #     """)
    #     top_layout = QHBoxLayout(top_panel)
    #     top_layout.setContentsMargins(15, 10, 15, 10)
    #     top_layout.setSpacing(20)
        
    #     # Close button (left side)
    #     close_btn = QPushButton("Close")
    #     close_btn.setStyleSheet("""
    #         QPushButton {
    #             background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
    #                 stop:0 #ff6600, stop:1 #ff8c42);
    #             color: white;
    #             border: 2px solid #ff6600;
    #             border-radius: 10px;
    #             padding: 10px 20px;
    #             font-weight: bold;
    #             font-size: 14px;
    #             min-width: 100px;
    #         }
    #         QPushButton:hover {
    #             background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
    #                 stop:0 #ff8c42, stop:1 #ff6600);
    #             border: 2px solid #ff8c42;
    #         }
    #     """)
        
    #     # Mode control buttons (right side)
    #     light_mode_btn = QPushButton("Light Mode")
    #     dark_mode_btn = QPushButton("Dark Mode")
    #     graph_mode_btn = QPushButton("Graph Mode")
        
    #     # Style the mode buttons
    #     button_style = """
    #         QPushButton {
    #             background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
    #                 stop:0 #4CAF50, stop:1 #45a049);
    #             color: white;
    #             border: 2px solid #4CAF50;
    #             border-radius: 8px;
    #             padding: 8px 16px;
    #             font-weight: bold;
    #             min-width: 100px;
    #         }
    #         QPushButton:hover {
    #             background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
    #                 stop:0 #45a049, stop:1 #4CAF50);
    #             border: 2px solid #45a049;
    #         }
    #     """
        
    #     light_mode_btn.setStyleSheet(button_style)
    #     dark_mode_btn.setStyleSheet(button_style)
    #     graph_mode_btn.setStyleSheet(button_style)
        
    #     # Add widgets to top panel
    #     top_layout.addWidget(close_btn)
    #     top_layout.addStretch()
    #     top_layout.addWidget(light_mode_btn)
    #     top_layout.addWidget(dark_mode_btn)
    #     top_layout.addWidget(graph_mode_btn)
        
    #     main_layout.addWidget(top_panel)
        
    #     # Create the matplotlib figure
    #     num_leads = len(leads)
    #     fig = Figure(figsize=(14, num_leads * 1.8), facecolor='#000')
    #     axes = []
    #     lines = []
        
    #     for idx, lead in enumerate(leads):
    #         ax = fig.add_subplot(num_leads, 1, idx+1)
    #         ax.set_facecolor('#000')
    #         ax.tick_params(axis='x', colors='#00ff00')
    #         ax.tick_params(axis='y', colors='#00ff00')
    #         for spine in ax.spines.values():
    #             spine.set_visible(False)
    #         ax.set_ylabel(lead, color='#00ff00', fontsize=14, labelpad=15)
    #         ax.set_xticks([])
    #         ax.set_yticks([])
    #         line, = ax.plot(np.arange(buffer_size), [np.nan]*buffer_size, color="#00ff00", lw=2.0)
    #         axes.append(ax)
    #         lines.append(line)
        
    #     canvas = FigureCanvas(fig)
    #     main_layout.addWidget(canvas)
        
    #     # Mode state variables
    #     current_mode = "dark"
    #     background_images = []
        
    #     def clear_background_images():
    #         nonlocal background_images
    #         for ax in axes:
    #             if hasattr(ax, '_background_image') and ax._background_image:
    #                 try:
    #                     ax._background_image.remove()
    #                 except:
    #                     pass
    #                 delattr(ax, '_background_image')
    #         background_images = []
        
    #     def apply_light_mode():
    #         nonlocal current_mode
    #         current_mode = "light"
    #         clear_background_images()
            
    #         dialog.setStyleSheet("""
    #             QDialog {
    #                 background: rgba(255, 255, 255, 0.95);
    #                 border: 2px solid #ff6600;
    #                 border-radius: 15px;
    #             }
    #         """)
            
    #         fig.patch.set_facecolor('#ffffff')
    #         for ax in axes:
    #             ax.set_facecolor('#ffffff')
    #             ax.tick_params(axis='x', colors='#333333')
    #             ax.tick_params(axis='y', colors='#333333')
    #             ax.set_ylabel(ax.get_ylabel(), color='#333333', fontsize=14, labelpad=15)
    #             for spine in ax.spines.values():
    #                 spine.set_visible(True)
    #                 spine.set_color('#333333')
            
    #         for line in lines:
    #             line.set_color('#0066cc')
    #             line.set_linewidth(2.0)
            
    #         canvas.draw()
            
    #         light_mode_btn.setStyleSheet(button_style.replace("#4CAF50", "#ff6600").replace("#45a049", "#ff8c42"))
    #         dark_mode_btn.setStyleSheet(button_style)
    #         graph_mode_btn.setStyleSheet(button_style)
        
    #     def apply_dark_mode():
    #         nonlocal current_mode
    #         current_mode = "dark"
    #         clear_background_images()
            
    #         dialog.setStyleSheet("""
    #             QDialog {
    #                 background: rgba(0, 0, 0, 0.95);
    #                 border: 2px solid #ff6600;
    #                 border-radius: 15px;
    #             }
    #         """)
            
    #         fig.patch.set_facecolor('#000')
    #         for ax in axes:
    #             ax.set_facecolor('#000')
    #             ax.tick_params(axis='x', colors='#00ff00')
    #             ax.tick_params(axis='y', colors='#00ff00')
    #             ax.set_ylabel(ax.get_ylabel(), color='#00ff00', fontsize=14, labelpad=15)
    #             for spine in ax.spines.values():
    #                 spine.set_visible(False)
            
    #         for line in lines:
    #             line.set_color('#00ff00')
    #             line.set_linewidth(2.0)
            
    #         canvas.draw()
            
    #         light_mode_btn.setStyleSheet(button_style)
    #         dark_mode_btn.setStyleSheet(button_style.replace("#4CAF50", "#ff6600").replace("#45a049", "#ff8c42"))
    #         graph_mode_btn.setStyleSheet(button_style)
        
    #     def apply_graph_mode():
    #         nonlocal current_mode
    #         current_mode = "graph"
    #         clear_background_images()
            
    #         dialog.setStyleSheet("""
    #             QDialog {
    #                 background: rgba(240, 240, 240, 0.95);
    #                 border: 2px solid #ff6600;
    #                 border-radius: 15px;
    #             }
    #         """)
            
    #         fig.patch.set_facecolor('#ffffff')
            
    #         try:
    #             bg_path = "ecg_bgimg.png"
    #             if os.path.exists(bg_path):
    #                 bg_img = QPixmap(bg_path)
    #                 if not bg_img.isNull():
    #                     import matplotlib.image as mpimg
    #                     temp_path = "temp_bg.png"
    #                     bg_img.save(temp_path)
    #                     bg_matplotlib = mpimg.imread(temp_path)
                        
    #                     for ax in axes:
    #                         ax.set_facecolor('#ffffff')
    #                         ax.tick_params(axis='x', colors='#333333')
    #                         ax.tick_params(axis='y', colors='#333333')
    #                         ax.set_ylabel(ax.get_ylabel(), color='#333333', fontsize=14, labelpad=15)
    #                         for spine in ax.spines.values():
    #                             spine.set_visible(True)
    #                             spine.set_color('#333333')
                            
    #                         ax._background_image = ax.imshow(bg_matplotlib, extent=[0, buffer_size-1, -500, 500], 
    #                                                     aspect='auto', alpha=0.4, zorder=0)
    #                         background_images.append(ax._background_image)
                        
    #                     for line in lines:
    #                         line.set_color('#ff0000')
    #                         line.set_linewidth(2.5)
                        
    #                     if os.path.exists(temp_path):
    #                         os.remove(temp_path)
                        
    #                     canvas.draw()
    #                 else:
    #                     apply_light_mode()
    #             else:
    #                 apply_light_mode()
                    
    #         except Exception as e:
    #             print(f"Error applying graph mode: {e}")
    #             apply_light_mode()
            
    #         light_mode_btn.setStyleSheet(button_style)
    #         dark_mode_btn.setStyleSheet(button_style)
    #         graph_mode_btn.setStyleSheet(button_style.replace("#4CAF50", "#ff6600").replace("#45a049", "#ff8c42"))
        
    #     # Connect mode buttons
    #     light_mode_btn.clicked.connect(apply_light_mode)
    #     dark_mode_btn.clicked.connect(apply_dark_mode)
    #     graph_mode_btn.clicked.connect(apply_graph_mode)
        
    #     # Close button functionality
    #     close_btn.clicked.connect(dialog.accept)
        
    #     # Apply default mode
    #     apply_dark_mode()
        
    #     def update_overlay():
    #         for idx, lead in enumerate(leads):
    #             d = data.get(lead, [])
    #             line = lines[idx]
    #             ax = axes[idx]
    #             plot_data = np.full(buffer_size, np.nan)
                
    #             if d:
    #                 n = min(len(d), buffer_size)
    #                 centered = np.array(d[-n:]) - np.mean(d[-n:])
    #                 if n < buffer_size:
    #                     stretched = np.interp(
    #                         np.linspace(0, n-1, buffer_size),
    #                         np.arange(n),
    #                         centered
    #                     )
    #                     plot_data[:] = stretched
    #                 else:
    #                     plot_data[-n:] = centered
                    
    #                 ymin = np.min(centered) - 100
    #                 ymax = np.max(centered) + 100
    #                 if ymin == ymax:
    #                     ymin, ymax = -500, 500
    #                 ax.set_ylim(ymin, ymax)
    #             else:
    #                 ax.set_ylim(-500, 500)
                
    #             ax.set_xlim(0, buffer_size-1)
    #             line.set_ydata(plot_data)
            
    #         canvas.draw_idle()
        
    #     timer = QTimer(dialog)
    #     timer.timeout.connect(update_overlay)
    #     timer.start(100)
        
    #     def stop_timer():
    #         timer.stop()
        
    #     dialog.destroyed.connect(stop_timer)
        
    #     # Show the dialog
    #     dialog.exec_()
        
    #     return dialog
