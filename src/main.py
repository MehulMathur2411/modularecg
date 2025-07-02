import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox, QStackedWidget, QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from auth.sign_in import SignIn
from auth.sign_out import SignOut
from dashboard.dashboard import Dashboard
from splash_screen import SplashScreen


USER_DATA_FILE = "users.json"


def load_users():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    return {}


def save_users(users):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(users, f)


# Login/Register Dialog
class LoginRegisterDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ECG Monitor - Sign In / Sign Up")
        self.setFixedSize(350, 350)
        self.setStyleSheet("""
            QDialog { background: #fff; border-radius: 18px; }
            QLabel { font-size: 15px; color: #222; }
            QLineEdit { border: 2px solid #ff6600; border-radius: 8px; padding: 6px 10px; font-size: 15px; background: #f7f7f7; }
            QPushButton { background: #ff6600; color: white; border-radius: 10px; padding: 8px 0; font-size: 16px; font-weight: bold; }
            QPushButton:hover { background: #ff8800; }
        """)
        self.sign_in_logic = SignIn()
        self.init_ui()
        self.result = False
        self.username = None

    def init_ui(self):
        self.stacked = QStackedWidget(self)
        self.login_widget = self.create_login_widget()
        self.register_widget = self.create_register_widget()
        self.stacked.addWidget(self.login_widget)
        self.stacked.addWidget(self.register_widget)

        btn_layout = QHBoxLayout()
        self.login_tab = QPushButton("Sign In")
        self.signup_tab = QPushButton("Sign Up")
        self.login_tab.clicked.connect(lambda: self.stacked.setCurrentIndex(0))
        self.signup_tab.clicked.connect(lambda: self.stacked.setCurrentIndex(1))
        btn_layout.addWidget(self.login_tab)
        btn_layout.addWidget(self.signup_tab)

        main_layout = QVBoxLayout()
        title = QLabel("ECG Monitor")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        main_layout.addLayout(btn_layout)
        main_layout.addWidget(self.stacked)
        self.setLayout(main_layout)

    def create_login_widget(self):
        widget = QWidget()
        layout = QVBoxLayout()
        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText("Username")
        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Password")
        self.login_password.setEchoMode(QLineEdit.Password)
        login_btn = QPushButton("Sign In")
        login_btn.clicked.connect(self.handle_login)
        layout.addWidget(self.login_username)
        layout.addWidget(self.login_password)
        layout.addWidget(login_btn)
        widget.setLayout(layout)
        return widget

    def create_register_widget(self):
        widget = QWidget()
        layout = QVBoxLayout()
        self.reg_username = QLineEdit()
        self.reg_username.setPlaceholderText("Username")
        self.reg_password = QLineEdit()
        self.reg_password.setPlaceholderText("Password")
        self.reg_password.setEchoMode(QLineEdit.Password)
        self.reg_confirm = QLineEdit()
        self.reg_confirm.setPlaceholderText("Confirm Password")
        self.reg_confirm.setEchoMode(QLineEdit.Password)
        register_btn = QPushButton("Sign Up")
        register_btn.clicked.connect(self.handle_register)
        layout.addWidget(self.reg_username)
        layout.addWidget(self.reg_password)
        layout.addWidget(self.reg_confirm)
        layout.addWidget(register_btn)
        widget.setLayout(layout)
        return widget

    def handle_login(self):
        username = self.login_username.text()
        password = self.login_password.text()
        if self.sign_in_logic.sign_in_user(username, password):
            self.result = True
            self.username = username
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Invalid username or password.")

    def handle_register(self):
        username = self.reg_username.text()
        password = self.reg_password.text()
        confirm = self.reg_confirm.text()
        if not username or not password:
            QMessageBox.warning(self, "Error", "Username and password required.")
            return
        if password != confirm:
            QMessageBox.warning(self, "Error", "Passwords do not match.")
            return
        if not self.sign_in_logic.register_user(username, password):
            QMessageBox.warning(self, "Error", "Username already exists.")
            return
        QMessageBox.information(self, "Success", "Registration successful! You can now sign in.")
        self.stacked.setCurrentIndex(0)


def main():
    app = QApplication(sys.argv)
    splash = SplashScreen()
    splash.show()
    app.processEvents()
    login = LoginRegisterDialog()
    splash.finish(login)
    if login.exec_() == QDialog.Accepted and login.result:
        dashboard = Dashboard(username=login.username, role=None)
        dashboard.show()
        app.exec_()
        # On sign out, call SignOut logic if needed
        SignOut().sign_out_user(dashboard)
    else:
        sys.exit()


if __name__ == "__main__":
    main()