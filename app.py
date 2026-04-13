import sys
import os
import sqlite3
import random
import string
import time
from urllib.parse import urlparse
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QListWidget, QMessageBox, 
                             QInputDialog, QSystemTrayIcon, QStyle, QListWidgetItem, QDialog, QFormLayout)
from PyQt6.QtCore import Qt, QTimer
import pyperclip

from crypto_utils import generate_key, encrypt_data, decrypt_data
from cryptography.exceptions import InvalidKey

DB_PATH = "pwd_manager.db"

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.create_tables()

    def create_tables(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS passwords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site TEXT UNIQUE,
                username TEXT,
                enc_password TEXT
            )
        """)
        self.conn.commit()

    def get_meta(self, key):
        cur = self.conn.cursor()
        cur.execute("SELECT value FROM meta WHERE key = ?", (key,))
        row = cur.fetchone()
        return row[0] if row else None

    def set_meta(self, key, value):
        cur = self.conn.cursor()
        cur.execute("REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))
        self.conn.commit()

class LoginDialog(QDialog):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.key = None
        self.setWindowTitle("Password Manager Login")
        self.setFixedSize(300, 150)
        
        layout = QVBoxLayout()
        self.is_new = self.db.get_meta("salt") is None
        
        lbl = QLabel("Create Master Password:" if self.is_new else "Enter Master Password:")
        layout.addWidget(lbl)
        
        self.pwd_input = QLineEdit()
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.pwd_input)
        
        btn = QPushButton("Login" if not self.is_new else "Create")
        btn.clicked.connect(self.attempt_login)
        layout.addWidget(btn)
        
        self.setLayout(layout)

    def attempt_login(self):
        pwd = self.pwd_input.text().strip()
        if not pwd:
            QMessageBox.warning(self, "Error", "Password cannot be empty.")
            return

        if self.is_new:
            # Setup new master password
            salt = os.urandom(16)
            self.db.set_meta("salt", salt.hex())
            key = generate_key(pwd, salt)
            # Store a verification value
            verify_token = encrypt_data("VERIFIED", key)
            self.db.set_meta("verify", verify_token)
            self.key = key
            self.accept()
        else:
            salt = bytes.fromhex(self.db.get_meta("salt"))
            key = generate_key(pwd, salt)
            verify_token = self.db.get_meta("verify")
            try:
                decrypted = decrypt_data(verify_token, key)
                if decrypted == "VERIFIED":
                    self.key = key
                    self.accept()
            except Exception:
                QMessageBox.critical(self, "Failed", "Incorrect Master Password.")
                self.pwd_input.clear()

class AddPasswordDialog(QDialog):
    def __init__(self, existing_passwords):
        super().__init__()
        self.existing_passwords = existing_passwords
        self.setWindowTitle("Add Password")
        self.setFixedSize(350, 200)
        
        layout = QFormLayout()
        
        self.site_input = QLineEdit()
        self.user_input = QLineEdit()
        self.pwd_input = QLineEdit()
        
        layout.addRow("Site (Domain):", self.site_input)
        layout.addRow("Username/Email:", self.user_input)
        
        pwd_layout = QHBoxLayout()
        pwd_layout.addWidget(self.pwd_input)
        btn_gen = QPushButton("Generate Safe")
        btn_gen.clicked.connect(self.generate_pwd)
        pwd_layout.addWidget(btn_gen)
        
        layout.addRow("Password:", pwd_layout)
        
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.accept)
        layout.addRow("", btn_save)
        
        self.setLayout(layout)
        
    def generate_pwd(self):
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        while True:
            pwd = ''.join(random.choices(chars, k=16))
            # Rule 4: Generated password must not match any existing
            if pwd not in self.existing_passwords:
                self.pwd_input.setText(pwd)
                break

    def get_data(self):
        return self.site_input.text().strip(), self.user_input.text().strip(), self.pwd_input.text().strip()

class PasswordManager(QMainWindow):
    def __init__(self, db, key):
        super().__init__()
        self.db = db
        self.key = key
        self.setWindowTitle("Secure Password Manager")
        self.resize(600, 400)
        
        # System Tray logic (Feature 5)
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.tray_icon.show()
        
        self.setup_ui()
        self.load_passwords()
        
        # Clipboard monitoring
        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self.on_clipboard_change)
        self.last_clipboard_text = ""

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        top_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search site...")
        self.search_input.textChanged.connect(self.load_passwords)
        top_layout.addWidget(self.search_input)
        
        btn_add = QPushButton("Add New Password")
        btn_add.clicked.connect(self.add_password)
        top_layout.addWidget(btn_add)
        
        layout.addLayout(top_layout)
        
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.copy_password)
        layout.addWidget(self.list_widget)
        
        lbl_hint = QLabel("💡 Double click a site above to copy the password securely automatically.\n💡 Copy a URL in your browser to get an auto-notification of your password!")
        lbl_hint.setStyleSheet("color: gray;")
        layout.addWidget(lbl_hint)

    def get_all_decrypted_passwords(self):
        cur = self.db.conn.cursor()
        cur.execute("SELECT enc_password FROM passwords")
        pwds = []
        for row in cur.fetchall():
            try:
                pwds.append(decrypt_data(row[0], self.key))
            except:
                pass
        return pwds

    def add_password(self):
        dialog = AddPasswordDialog(self.get_all_decrypted_passwords())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            site, user, pwd = dialog.get_data()
            if not site or not pwd:
                QMessageBox.warning(self, "Warning", "Site and Password are required.")
                return
            
            enc_pwd = encrypt_data(pwd, self.key)
            cur = self.db.conn.cursor()
            try:
                cur.execute("INSERT OR REPLACE INTO passwords (site, username, enc_password) VALUES (?, ?, ?)", 
                            (site.lower(), user, enc_pwd))
                self.db.conn.commit()
                self.load_passwords()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save password: {e}")

    def load_passwords(self):
        search = self.search_input.text().lower()
        self.list_widget.clear()
        
        cur = self.db.conn.cursor()
        if search:
            cur.execute("SELECT id, site, username FROM passwords WHERE site LIKE ?", (f"%{search}%",))
        else:
            cur.execute("SELECT id, site, username FROM passwords")
            
        for row in cur.fetchall():
            db_id, site, user = row
            item = QListWidgetItem(f"[{site}]  User: {user}")
            item.setData(Qt.ItemDataRole.UserRole, db_id)
            self.list_widget.addItem(item)

    def copy_password(self, item):
        db_id = item.data(Qt.ItemDataRole.UserRole)
        cur = self.db.conn.cursor()
        cur.execute("SELECT site, enc_password FROM passwords WHERE id = ?", (db_id,))
        row = cur.fetchone()
        if row:
            site, enc_pwd = row
            try:
                pwd = decrypt_data(enc_pwd, self.key)
                pyperclip.copy(pwd)
                self.last_clipboard_text = pwd  # prevent self-triggering clipboard
                QMessageBox.information(self, "Copied", f"Password for '{site}' has been copied to your clipboard securely.\nPaste it by pressing Cmd+V.")
            except Exception as e:
                QMessageBox.critical(self, "Error", "Failed to decrypt password.")

    def on_clipboard_change(self):
        text = self.clipboard.text().strip().lower()
        if text == self.last_clipboard_text or not text:
            return
            
        self.last_clipboard_text = text
        
        # Check if clipboard contains a known site domain
        try:
            domain = urlparse(text).netloc if text.startswith("http") else text
            domain = domain.replace("www.", "")
            
            cur = self.db.conn.cursor()
            cur.execute("SELECT site, enc_password FROM passwords")
            for row in cur.fetchall():
                site, enc_pwd = row
                if site in text or site in domain:
                    # Found a match!
                    pwd = decrypt_data(enc_pwd, self.key)
                    pyperclip.copy(pwd)
                    self.last_clipboard_text = pwd
                    self.tray_icon.showMessage("Password Manager", f"Detected site '{site}'. Password automatically copied to clipboard!", QSystemTrayIcon.MessageIcon.Information, 3000)
                    break
        except Exception:
            pass

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) # Keep running for tray icon
    
    db = Database()
    
    login = LoginDialog(db)
    if login.exec() == QDialog.DialogCode.Accepted:
        key = login.key
        window = PasswordManager(db, key)
        window.show()
        
        # When main window closes, exit app completely
        app.setQuitOnLastWindowClosed(True)
        sys.exit(app.exec())

if __name__ == "__main__":
    main()
