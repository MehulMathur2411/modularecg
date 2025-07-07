from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QTableWidget, QTableWidgetItem, QDialog, QHBoxLayout, QPushButton, QFrame
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from utils.heartbeat_widget import heartbeat_image_widget

class NavPricing(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel("<h2>Pricing</h2><p>See our pricing plans for PulseMonitor.</p>")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        # Pricing table
        table = QTableWidget(4, 3)
        table.setHorizontalHeaderLabels(["Type", "Monthly Price", "Features"])
        plans = [
            ("12-Lead Portable ECG", "₹3,000 – ₹6,000", "Clinical-grade accuracy, detailed waveform capture"),
            ("Wireless / Smart ECG Patch", "₹4,000 – ₹8,000", "Real-time monitoring, mobile app integration"),
            ("Cloud-Based ECG Platform", "₹1,000 – ₹5,000", "Web dashboard, secure data storage, AI-powered reports"),
            ("Enterprise/Clinic Setup", "₹10,000 – ₹25,000+", "Multi-device access, EHR integration, bulk storage")
        ]
        for row, (ptype, price, features) in enumerate(plans):
            table.setItem(row, 0, QTableWidgetItem(ptype))
            table.setItem(row, 1, QTableWidgetItem(price))
            table.setItem(row, 2, QTableWidgetItem(features))
        table.resizeColumnsToContents()
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(table)
        self.setLayout(layout)

class PricingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pricing Plans")
        self.setMinimumSize(900, 700)
        self.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff7f2, stop:1 #ffe5d0);")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        # Title
        title = QLabel("Pricing plans for every need")
        title.setFont(QFont("Segoe UI", 32, QFont.Bold))
        title.setStyleSheet("color: #ff6600; margin-bottom: 8px; letter-spacing: 1px;")
        title.setAlignment(Qt.AlignHCenter)
        subtitle = QLabel("Transparent pricing. No hidden fees. Choose the plan that fits your clinic or personal use best.")
        subtitle.setFont(QFont("Segoe UI", 14))
        subtitle.setStyleSheet("color: #b85c00; margin-bottom: 32px;")
        subtitle.setAlignment(Qt.AlignHCenter)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        # Pricing cards
        cards_row = QHBoxLayout()
        cards_row.setSpacing(32)
        plans = [
            {
                'name': '12-Lead Portable ECG',
                'price': '₹3,000 – ₹6,000',
                'features': [
                    'Clinical-grade accuracy',
                    'Detailed waveform capture'
                ],
                'highlight': False
            },
            {
                'name': 'Wireless / Smart ECG Patch',
                'price': '₹4,000 – ₹8,000',
                'features': [
                    'Real-time monitoring',
                    'Mobile app integration'
                ],
                'highlight': False
            },
            {
                'name': 'Cloud-Based ECG Platform',
                'price': '₹1,000 – ₹5,000',
                'features': [
                    'Web dashboard',
                    'Secure data storage',
                    'AI-powered reports'
                ],
                'highlight': True
            },
            {
                'name': 'Enterprise/Clinic Setup',
                'price': '₹10,000 – ₹25,000+',
                'features': [
                    'Multi-device access',
                    'EHR integration',
                    'Bulk storage'
                ],
                'highlight': False
            }
        ]
        for plan in plans:
            card = QFrame()
            card.setFrameShape(QFrame.StyledPanel)
            card.setMinimumWidth(220)
            card.setMaximumWidth(260)
            card.setStyleSheet(f"""
                QFrame {{
                    background: {'#fff' if not plan['highlight'] else '#fff3e6'};
                    border-radius: 18px;
                    border: 2.5px solid {'#ffd6b3' if not plan['highlight'] else '#ff6600'};
                    box-shadow: 0 8px 32px rgba(255,102,0,0.10);
                }}
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(18, 18, 18, 18)
            card_layout.setSpacing(10)
            if plan['highlight']:
                pop = QLabel("Most popular ✨")
                pop.setFont(QFont("Segoe UI", 12, QFont.Bold))
                pop.setStyleSheet("color: #fff; background: #ff6600; border-radius: 8px; padding: 6px 16px; margin-bottom: 10px; letter-spacing: 0.5px;")
                pop.setAlignment(Qt.AlignHCenter)
                card_layout.addWidget(pop)
            name = QLabel(plan['name'])
            name.setFont(QFont("Segoe UI", 15, QFont.Bold))
            name.setWordWrap(True)
            name.setStyleSheet(f"color: {'#ff6600' if plan['highlight'] else '#b85c00'}; margin-bottom: 2px; letter-spacing: 0.5px;")
            name.setAlignment(Qt.AlignHCenter)
            price = QLabel(f"{plan['price']} <span style='color:#b85c00;font-size:15px;'>/month</span>")
            price.setFont(QFont("Segoe UI", 22, QFont.Bold))
            price.setStyleSheet("color: #ff6600; margin-bottom: 8px;")
            price.setAlignment(Qt.AlignHCenter)
            price.setTextFormat(Qt.RichText)
            card_layout.addWidget(name)
            card_layout.addWidget(price)
            # Features
            for feat in plan['features']:
                feat_row = QHBoxLayout()
                check = QLabel("✓")
                check.setFont(QFont("Segoe UI", 14, QFont.Bold))
                check.setStyleSheet(f"color: {'#ff6600' if plan['highlight'] else '#b85c00'}; margin-right: 8px;")
                feat_lbl = QLabel(feat)
                feat_lbl.setFont(QFont("Segoe UI", 12))
                feat_lbl.setWordWrap(True)
                feat_lbl.setStyleSheet(f"color: {'#b85c00' if not plan['highlight'] else '#ff6600'};")
                feat_row.addWidget(check)
                feat_row.addWidget(feat_lbl)
                feat_row.addStretch(1)
                card_layout.addLayout(feat_row)
            card_layout.addSpacing(8)
            btn = QPushButton("Get started")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {'#ff6600' if plan['highlight'] else '#fff3e6'};
                    color: {'white' if plan['highlight'] else '#ff6600'};
                    border-radius: 8px;
                    font-size: 15px;
                    font-weight: bold;
                    padding: 10px 0;
                }}
                QPushButton:hover {{
                    background: {'#b85c00' if plan['highlight'] else '#ffe5d0'};
                }}
            """)
            btn.setMinimumHeight(36)
            card_layout.addWidget(btn)
            card_layout.addStretch(1)
            cards_row.addWidget(card)
        layout.addSpacing(24)
        layout.addLayout(cards_row)
        # Add heartbeat image at the bottom
        layout.addSpacing(16)
        layout.addWidget(heartbeat_image_widget())
        layout.addStretch(1)

def show_pricing_dialog(parent=None):
    dlg = PricingDialog(parent)
    dlg.exec_()
