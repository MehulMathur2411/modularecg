import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox, QStackedWidget, QWidget, QInputDialog
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
        self.setFixedSize(500, 420)
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
        self.user_details = {}
        # Center the dialog
        self.center_on_screen()

    def center_on_screen(self):
        qr = self.frameGeometry()
        cp = QApplication.desktop().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def init_ui(self):
        main_layout = QHBoxLayout()
        # Left: Blank image
        left_img = QLabel()
        left_img.setFixedSize(120, 320)
        left_img.setStyleSheet("background: #f0f0f0; border-radius: 12px;")
        main_layout.addWidget(left_img)
        # Right: Login/Register stack
        right_layout = QVBoxLayout()
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
        title = QLabel("ECG Monitor")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(title)
        right_layout.addLayout(btn_layout)
        right_layout.addWidget(self.stacked)
        main_layout.addLayout(right_layout)
        self.setLayout(main_layout)

    def create_login_widget(self):
        widget = QWidget()
        layout = QVBoxLayout()
        self.login_email = QLineEdit()
        self.login_email.setPlaceholderText("Email")
        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Password")
        self.login_password.setEchoMode(QLineEdit.Password)
        login_btn = QPushButton("Sign In")
        login_btn.clicked.connect(self.handle_login)
        phone_btn = QPushButton("Login with Phone Number")
        phone_btn.clicked.connect(self.handle_phone_login)
        layout.addWidget(self.login_email)
        layout.addWidget(self.login_password)
        layout.addWidget(login_btn)
        layout.addWidget(phone_btn)
        widget.setLayout(layout)
        return widget

    def create_register_widget(self):
        widget = QWidget()
        layout = QVBoxLayout()
        self.reg_email = QLineEdit()
        self.reg_email.setPlaceholderText("Email")
        self.reg_password = QLineEdit()
        self.reg_password.setPlaceholderText("Password")
        self.reg_password.setEchoMode(QLineEdit.Password)
        self.reg_confirm = QLineEdit()
        self.reg_confirm.setPlaceholderText("Confirm Password")
        self.reg_confirm.setEchoMode(QLineEdit.Password)
        self.reg_fullname = QLineEdit()
        self.reg_fullname.setPlaceholderText("Full Name")
        self.reg_age = QLineEdit()
        self.reg_age.setPlaceholderText("Age")
        self.reg_gender = QLineEdit()
        self.reg_gender.setPlaceholderText("Gender")
        self.reg_contact = QLineEdit()
        self.reg_contact.setPlaceholderText("Contact Number")
        register_btn = QPushButton("Sign Up")
        register_btn.clicked.connect(self.handle_register)
        layout.addWidget(self.reg_email)
        layout.addWidget(self.reg_password)
        layout.addWidget(self.reg_confirm)
        layout.addWidget(self.reg_fullname)
        layout.addWidget(self.reg_age)
        layout.addWidget(self.reg_gender)
        layout.addWidget(self.reg_contact)
        layout.addWidget(register_btn)
        widget.setLayout(layout)
        return widget

    def handle_login(self):
        email = self.login_email.text()
        password = self.login_password.text()
        if self.sign_in_logic.sign_in_user(email, password):
            self.result = True
            self.username = email
            self.user_details = {}
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Invalid email or password.")

    def handle_phone_login(self):
        phone, ok = QInputDialog.getText(self, "Login with Phone Number", "Enter your phone number:")
        if ok and phone:
            # Here you would implement phone-based authentication logic
            QMessageBox.information(self, "Phone Login", f"Logged in with phone: {phone} (Demo)")
            self.result = True
            self.username = phone
            self.user_details = {'contact': phone}
            self.accept()

    def handle_register(self):
        email = self.reg_email.text()
        password = self.reg_password.text()
        confirm = self.reg_confirm.text()
        fullname = self.reg_fullname.text()
        age = self.reg_age.text()
        gender = self.reg_gender.text()
        contact = self.reg_contact.text()
        if not email or not password:
            QMessageBox.warning(self, "Error", "Email and password required.")
            return
        if password != confirm:
            QMessageBox.warning(self, "Error", "Passwords do not match.")
            return
        if not self.sign_in_logic.register_user(email, password):
            QMessageBox.warning(self, "Error", "Email already exists.")
            return
        if not fullname or not age or not gender or not contact:
            QMessageBox.warning(self, "Error", "All details required.")
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
    while True:
        if login.exec_() == QDialog.Accepted and login.result:
            dashboard = Dashboard(username=login.username, role=None)
            dashboard.show()
            app.exec_()
            # After dashboard closes (sign out), show login again (reuse dialog)
            login = LoginRegisterDialog()
        else:
            break


if __name__ == "__main__":
    main()