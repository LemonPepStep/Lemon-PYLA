import sys
from PySide6.QtWidgets import QApplication

import utils


class QtApp:
    """Drop-in replacement for the legacy gui.main.App, using PySide6."""

    def __init__(self, brawlers, pyla_main):
        self.brawlers = brawlers
        self.pyla_main = pyla_main

    def start(self, pyla_version, get_latest_version=None):
        app = QApplication.instance() or QApplication(sys.argv)

        from gui.qt.login import run_login
        if not run_login():
            return

        from gui.qt.shell import Shell
        shell = Shell(self.brawlers, pyla_version, pyla_main=self.pyla_main)
        shell.show()
        app.exec()
