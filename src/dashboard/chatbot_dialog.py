import os
import sys
import json
# Ensure .env is loaded before anything else
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
except ImportError:
    # Fallback: manual .env loader
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.strip() and not line.strip().startswith('#') and '=' in line:
                    k, v = line.strip().split('=', 1)
                    os.environ.setdefault(k, v)

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout, QListWidget, QListWidgetItem, QMessageBox, QWidget, QFrame, QSizePolicy
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QIcon, QFont

# Helper for PyInstaller asset compatibility
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', relative_path)

CHAT_HISTORY_FILE = resource_path('chat_history.json')

class ChatbotThread(QThread):
    response_ready = pyqtSignal(str)
    def __init__(self, prompt, api_key):
        super().__init__()
        self.prompt = prompt
        self.api_key = api_key
    def run(self):
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            # Use a supported Gemini model for text generation
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(self.prompt)
            reply = response.text
            self.response_ready.emit(reply)
        except Exception as e:
            self.response_ready.emit(f"Error: {str(e)}")

class ChatbotDialog(QDialog):
    def __init__(self, parent=None, user_id=None, dashboard_data_func=None):
        super().__init__(parent)
        self.setWindowTitle("AI Health Chatbot")
        self.setMinimumSize(600, 600)
        self.setStyleSheet("""
            QDialog {
                background: #f4f7fa;
                border-radius: 18px;
            }
            QLabel#HeaderTitle {
                color: #2453ff;
                font-size: 22px;
                font-weight: bold;
            }
            QLabel#HeaderDesc {
                color: #888;
                font-size: 13px;
            }
            QListWidget#ChatList {
                background: #f9fbff;
                border: none;
                border-radius: 12px;
                padding: 12px;
            }
            QTextEdit#InputBox {
                background: #fff;
                border: 2px solid #2453ff;
                border-radius: 12px;
                font-size: 15px;
                padding: 10px;
                color: #222;
            }
            QPushButton#SendBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2453ff, stop:1 #ff3380);
                color: white;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                padding: 10px 28px;
            }
            QPushButton#SendBtn:disabled {
                background: #ccc;
                color: #fff;
            }
        """)
        # Use Gemini API key directly for testing
        self.api_key = "AIzaSyACyIVYnAua6BsmdK2I7-cWefmiAxWFKzA"
        self.user_id = user_id or "default"
        self.dashboard_data_func = dashboard_data_func
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        # Header
        header = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(QIcon(resource_path('assets/vheart2.png')).pixmap(40, 40))
        header.addWidget(icon)
        title_col = QVBoxLayout()
        title = QLabel("AI Health Chatbot")
        title.setObjectName("HeaderTitle")
        desc = QLabel("Ask health questions. Get safe, friendly suggestions. Not a diagnosis.")
        desc.setObjectName("HeaderDesc")
        title_col.addWidget(title)
        title_col.addWidget(desc)
        header.addLayout(title_col)
        header.addStretch(1)
        layout.addLayout(header)
        # Chat area
        self.chat_list = QListWidget()
        self.chat_list.setObjectName("ChatList")
        self.chat_list.setSpacing(10)
        self.chat_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.chat_list, 4)
        # History (collapsible)
        self.history_list = QListWidget()
        self.history_list.setMaximumHeight(100)
        self.history_list.setObjectName("ChatList")
        layout.addWidget(QLabel("Previous Suggestions:"))
        layout.addWidget(self.history_list)
        self.load_history()
        # Input area
        input_row = QHBoxLayout()
        self.input_box = QTextEdit()
        self.input_box.setObjectName("InputBox")
        self.input_box.setFixedHeight(48)
        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("SendBtn")
        self.send_btn.setFixedHeight(48)
        self.send_btn.setMinimumWidth(100)
        self.send_btn.clicked.connect(self.send_message)
        input_row.addWidget(self.input_box, 4)
        input_row.addWidget(self.send_btn, 1)
        layout.addLayout(input_row)
        self.setLayout(layout)
        self.history_list.itemClicked.connect(self.show_history_item)
        if not self.api_key:
            self.add_message("[Error: OpenAI API key not set. Please set the OPENAI_API_KEY environment variable.]", sender="AI")
            self.send_btn.setEnabled(False)
    def add_message(self, text, sender="user"):
        item = QListWidgetItem()
        bubble = QWidget()
        bubble_layout = QHBoxLayout(bubble)
        bubble_layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(text)
        label.setWordWrap(True)
        label.setFont(QFont("Segoe UI", 13))
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        if sender == "user":
            label.setStyleSheet("background: #2453ff; color: white; border-radius: 14px; padding: 10px 16px; margin: 2px 0 2px 40px;")
            bubble_layout.addStretch(1)
            bubble_layout.addWidget(label, 0, Qt.AlignRight)
        else:
            label.setStyleSheet("background: #fff; color: #222; border: 2px solid #ff3380; border-radius: 14px; padding: 10px 16px; margin: 2px 40px 2px 0;")
            bubble_layout.addWidget(label, 0, Qt.AlignLeft)
            bubble_layout.addStretch(1)
        bubble.setLayout(bubble_layout)
        item.setSizeHint(bubble.sizeHint())
        self.chat_list.addItem(item)
        self.chat_list.setItemWidget(item, bubble)
        self.chat_list.scrollToBottom()
    def load_history(self):
        self.history = []
        if os.path.exists(CHAT_HISTORY_FILE):
            try:
                with open(CHAT_HISTORY_FILE, 'r') as f:
                    all_hist = json.load(f)
                    self.history = all_hist.get(self.user_id, [])
            except Exception:
                self.history = []
        self.history_list.clear()
        for item in self.history:
            lw_item = QListWidgetItem(item['question'][:60] + ("..." if len(item['question']) > 60 else ""))
            lw_item.setData(1000, item)
            self.history_list.addItem(lw_item)
    def save_history(self):
        all_hist = {}
        if os.path.exists(CHAT_HISTORY_FILE):
            try:
                with open(CHAT_HISTORY_FILE, 'r') as f:
                    all_hist = json.load(f)
            except Exception:
                all_hist = {}
        all_hist[self.user_id] = self.history
        with open(CHAT_HISTORY_FILE, 'w') as f:
            json.dump(all_hist, f, indent=2)
    def send_message(self):
        user_msg = self.input_box.toPlainText().strip()
        if not user_msg:
            return
        dashboard_info = ""
        if self.dashboard_data_func:
            dashboard_info = self.dashboard_data_func()
        full_prompt = user_msg + ("\n\nDashboard Data:\n" + dashboard_info if dashboard_info else "")
        self.add_message(user_msg, sender="user")
        self.input_box.clear()
        self.send_btn.setEnabled(False)
        self.thread = ChatbotThread(full_prompt, self.api_key)
        self.thread.response_ready.connect(self.display_response)
        self.thread.start()
        self._pending_question = user_msg
    def display_response(self, reply):
        self.add_message(reply, sender="AI")
        self.history.append({'question': self._pending_question, 'answer': reply})
        self.save_history()
        self.load_history()
        self.send_btn.setEnabled(True)
    def show_history_item(self, item):
        data = item.data(1000)
        if data:
            self.chat_list.clear()
            self.add_message(data['question'], sender="user")
            self.add_message(data['answer'], sender="AI")
