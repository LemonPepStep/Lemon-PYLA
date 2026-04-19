from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QFrame)

from gui.qt.theme import QSS, COLORS
from gui.qt.widgets import apply_shadow
from gui.api import check_if_exists
from utils import api_base_url, load_toml_as_dict, save_dict_as_toml


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.authenticated = False
        self.setWindowTitle("PylaAI · Login")
        self.setFixedSize(460, 300)
        self.setStyleSheet(QSS)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        card = QFrame()
        card.setObjectName("panel")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(26, 24, 26, 24)
        lay.setSpacing(14)

        header = QHBoxLayout()
        badge = QLabel("★")
        badge.setObjectName("logoBadge")
        badge.setFixedSize(44, 44)
        badge.setAlignment(Qt.AlignCenter)
        header.addWidget(badge)
        col = QVBoxLayout()
        t = QLabel("PylaAI")
        t.setObjectName("logo")
        s = QLabel("ENTER YOUR API KEY")
        s.setObjectName("logoSub")
        col.addWidget(t); col.addWidget(s)
        header.addLayout(col)
        header.addStretch()
        lay.addLayout(header)

        lbl = QLabel("API Key")
        lbl.setObjectName("subLabel")
        lay.addWidget(lbl)

        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Paste your key…")
        self.entry.setEchoMode(QLineEdit.Password)
        lay.addWidget(self.entry)

        self.msg = QLabel("")
        self.msg.setStyleSheet(f"color: {COLORS['red']}; font-size: 11px;")
        lay.addWidget(self.msg)

        btn = QPushButton("Login")
        btn.setObjectName("primary")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self._on_login)
        lay.addWidget(btn)

        apply_shadow(card, blur=28, alpha=120, dy=8)
        root.addWidget(card)

    def _on_login(self):
        key = self.entry.text().strip()
        if check_if_exists(key):
            save_dict_as_toml({"key": key}, "./cfg/login.toml")
            self.authenticated = True
            self.accept()
        else:
            self.msg.setText("Invalid API Key")


def run_login() -> bool:
    if api_base_url == "localhost":
        return True
    existing = load_toml_as_dict("./cfg/login.toml").get("key")
    if existing and check_if_exists(existing):
        return True
    dlg = LoginDialog()
    dlg.exec()
    return dlg.authenticated
