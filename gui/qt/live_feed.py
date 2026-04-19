"""Live Feed page: captures console output from the bot thread and shows
real-time session stats (IPS, state, W/L, runtime)."""
import re
import sys
import time
from PySide6.QtCore import Qt, QObject, Signal, QTimer
from PySide6.QtGui import QFont, QTextCursor, QColor, QKeySequence, QShortcut, QTextDocument
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                               QLabel, QPushButton, QPlainTextEdit, QCheckBox,
                               QLineEdit)

from gui.qt.theme import COLORS
from gui.qt.widgets import apply_shadow
from gui.qt.match_log import load_entries, classify


class StdoutStreamer(QObject):
    """Redirects writes to a Qt signal so the GUI can display console output.
    Thread-safe: signal emission is auto-queued to the receiver's thread."""
    line_received = Signal(str)

    def __init__(self):
        super().__init__()
        self._buffer = ""
        self._real_stdout = sys.__stdout__

    def write(self, text):
        try:
            if self._real_stdout:
                self._real_stdout.write(text)
                self._real_stdout.flush()
        except Exception:
            pass
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line:
                self.line_received.emit(line)

    def flush(self):
        try:
            if self._real_stdout:
                self._real_stdout.flush()
        except Exception:
            pass


class StatBadge(QFrame):
    def __init__(self, label, value, accent=COLORS["accent"], parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(2)
        l = QLabel(label.upper())
        l.setStyleSheet(f"color: {COLORS['text_faint']}; font-size: 10px; font-weight: 700; letter-spacing: 1.3px;")
        self.val = QLabel(value)
        self.val.setStyleSheet(f"color: {accent}; font-size: 20px; font-weight: 800;")
        lay.addWidget(l)
        lay.addWidget(self.val)

    def set_value(self, v):
        self.val.setText(str(v))


class LiveFeedPage(QWidget):
    IPS_RE = re.compile(r"(\d+\.\d+)\s*IPS")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._autoscroll = True
        self._session_start_ts = None
        self._session_baseline = 0  # count of match_log entries when session started
        self._wins = 0
        self._losses = 0
        self._draws = 0
        self._last_ips = "—"
        self._current_state = "idle"
        self._all_lines: list[tuple[str, str, str]] = []  # (category, color, raw_line)
        self._search_text = ""
        self._filters = {"error": True, "warn": True, "info": True, "ips": True}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        # Title row
        tr = QHBoxLayout()
        t1 = QLabel("Live ")
        t1.setObjectName("pageTitle")
        t2 = QLabel("Feed")
        t2.setObjectName("pageTitleAccent")
        tr.addWidget(t1); tr.addWidget(t2); tr.addStretch()
        self._status_pill = QLabel("● IDLE")
        self._status_pill.setStyleSheet(
            f"background: {COLORS['bg_card']}; color: {COLORS['text_faint']};"
            f"border: 1px solid {COLORS['border']}; border-radius: 10px;"
            f"padding: 4px 12px; font-size: 11px; font-weight: 800; letter-spacing: 1px;")
        tr.addWidget(self._status_pill)
        root.addLayout(tr)

        # Stats row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self._b_ips = StatBadge("IPS", "—", accent=COLORS["accent_2"])
        self._b_state = StatBadge("STATE", "idle", accent=COLORS["cyan"])
        self._b_wins = StatBadge("WINS", "0", accent=COLORS["green"])
        self._b_losses = StatBadge("LOSSES", "0", accent=COLORS["red"])
        self._b_runtime = StatBadge("RUNTIME", "00:00:00", accent=COLORS["accent_hi"])
        for b in (self._b_ips, self._b_state, self._b_wins, self._b_losses, self._b_runtime):
            b.setMinimumWidth(120)
            apply_shadow(b, blur=16, alpha=60, dy=3)
            stats_row.addWidget(b, stretch=1)
        root.addLayout(stats_row)

        # Console panel
        panel = QFrame()
        panel.setObjectName("panel")
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(18, 16, 18, 16)
        pl.setSpacing(10)

        hdr = QHBoxLayout()
        ct = QLabel("CONSOLE OUTPUT")
        ct.setObjectName("subLabel")
        hdr.addWidget(ct); hdr.addStretch()

        # Filter toggles
        self._filter_cbs = {}
        for key, label in [("error", "Errors"), ("warn", "Warnings"),
                           ("info", "Info"), ("ips", "IPS")]:
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.toggled.connect(lambda checked, k=key: self._on_filter_toggle(k, checked))
            self._filter_cbs[key] = cb
            hdr.addWidget(cb)

        self._auto_cb = QCheckBox("Auto-scroll")
        self._auto_cb.setChecked(True)
        self._auto_cb.toggled.connect(self._on_autoscroll)
        hdr.addWidget(self._auto_cb)

        clear_btn = QPushButton("Clear")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet(
            f"background: {COLORS['bg_card_hi']}; color: {COLORS['text_dim']};"
            f"border: 1px solid {COLORS['border']}; border-radius: 8px;"
            f"padding: 4px 14px; font-weight: 700; font-size: 11px;")
        clear_btn.clicked.connect(self._clear_console)
        hdr.addWidget(clear_btn)
        pl.addLayout(hdr)

        # Search bar (Ctrl+F focus)
        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍  Find in console (Ctrl+F)   ·   type to filter lines")
        self._search.textChanged.connect(self._on_search_changed)
        self._search.returnPressed.connect(self._find_next)
        self._search.setStyleSheet(
            f"background: {COLORS['bg_card']}; color: {COLORS['text']};"
            f"border: 1px solid {COLORS['border']}; border-radius: 8px;"
            f"padding: 6px 10px; font-size: 12px;"
        )
        search_row.addWidget(self._search, stretch=1)
        next_btn = QPushButton("↓ Next")
        next_btn.setCursor(Qt.PointingHandCursor)
        next_btn.setStyleSheet(
            f"background: {COLORS['bg_card_hi']}; color: {COLORS['text_dim']};"
            f"border: 1px solid {COLORS['border']}; border-radius: 8px;"
            f"padding: 6px 12px; font-weight: 700; font-size: 11px;")
        next_btn.clicked.connect(self._find_next)
        search_row.addWidget(next_btn)
        pl.addLayout(search_row)

        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(3000)
        mono = QFont("Consolas", 10)
        mono.setStyleHint(QFont.Monospace)
        self.console.setFont(mono)
        self.console.setStyleSheet(
            f"background: #0a0c1f; color: {COLORS['text']};"
            f"border: 1px solid {COLORS['border']}; border-radius: 10px;"
            f"padding: 10px;")
        pl.addWidget(self.console, stretch=1)

        root.addWidget(panel, stretch=1)
        apply_shadow(panel, blur=22, alpha=70, dy=6)

        # Ctrl+F focuses search
        self._find_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self._find_shortcut.activated.connect(self._focus_search)

        # Poll timers
        self._ticker = QTimer(self)
        self._ticker.setInterval(1000)
        self._ticker.timeout.connect(self._tick)
        self._ticker.start()

    # ---------- Public API ----------
    def attach_streamer(self, streamer: StdoutStreamer):
        streamer.line_received.connect(self._on_line)

    def mark_session_started(self):
        self._session_start_ts = time.time()
        self._session_baseline = len(load_entries())
        self._wins = self._losses = self._draws = 0
        self._b_wins.set_value("0")
        self._b_losses.set_value("0")
        self.set_status("running")

    def mark_session_stopped(self):
        self.set_status("stopped")

    def set_status(self, state: str):
        colors = {
            "idle":    (COLORS["text_faint"], COLORS["bg_card"]),
            "running": (COLORS["green"],      "rgba(34,197,94,0.12)"),
            "stopped": (COLORS["red"],        "rgba(239,68,68,0.12)"),
        }
        fg, bg = colors.get(state, colors["idle"])
        self._status_pill.setText(f"● {state.upper()}")
        self._status_pill.setStyleSheet(
            f"background: {bg}; color: {fg};"
            f"border: 1px solid {fg}; border-radius: 10px;"
            f"padding: 4px 12px; font-size: 11px; font-weight: 800; letter-spacing: 1px;")

    # ---------- Internals ----------
    def _classify(self, line: str) -> tuple[str, str]:
        """Return (category, color) for a line."""
        low = line.lower()
        if any(k in low for k in ("error", "failed", "traceback", "[e:")):
            return "error", COLORS["red"]
        if any(k in low for k in ("warn", "[w:")):
            return "warn", COLORS["yellow"]
        if "ips" in low and self.IPS_RE.search(line):
            return "ips", COLORS["accent_2"]
        return "info", COLORS["text"]

    def _on_line(self, line: str):
        m = self.IPS_RE.search(line)
        if m:
            self._last_ips = m.group(1)
            self._b_ips.set_value(self._last_ips)

        category, color = self._classify(line)
        self._all_lines.append((category, color, line))
        # Cap buffer to match console's 3000-block limit
        if len(self._all_lines) > 3000:
            self._all_lines = self._all_lines[-3000:]

        if self._line_passes_filters(category, line):
            self._append_html(color, line)

    def _line_passes_filters(self, category: str, line: str) -> bool:
        if not self._filters.get(category, True):
            return False
        if self._search_text and self._search_text.lower() not in line.lower():
            return False
        return True

    def _append_html(self, color: str, line: str):
        text = self._escape(line)
        if self._search_text:
            # Highlight search matches
            import re as _re
            pattern = _re.compile(_re.escape(self._search_text), _re.IGNORECASE)
            text = pattern.sub(
                lambda m: f'<span style="background:#facc15;color:#1a1a1a;">{m.group(0)}</span>',
                text,
            )
        self.console.appendHtml(f'<span style="color:{color};">{text}</span>')
        if self._autoscroll:
            self.console.moveCursor(QTextCursor.End)

    def _re_render(self):
        self.console.clear()
        for cat, color, line in self._all_lines:
            if self._line_passes_filters(cat, line):
                self._append_html(color, line)

    def _on_filter_toggle(self, key: str, checked: bool):
        self._filters[key] = checked
        self._re_render()

    def _on_search_changed(self, text: str):
        self._search_text = text.strip()
        self._re_render()

    def _find_next(self):
        if not self._search_text:
            return
        if not self.console.find(self._search_text):
            # wrap to top
            cursor = self.console.textCursor()
            cursor.movePosition(QTextCursor.Start)
            self.console.setTextCursor(cursor)
            self.console.find(self._search_text)

    def _focus_search(self):
        self._search.setFocus()
        self._search.selectAll()

    @staticmethod
    def _escape(s: str) -> str:
        return (s.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;"))

    def _clear_console(self):
        self.console.clear()
        self._all_lines.clear()

    def _on_autoscroll(self, checked):
        self._autoscroll = checked
        if checked:
            self.console.moveCursor(QTextCursor.End)

    def _tick(self):
        # Runtime
        if self._session_start_ts:
            elapsed = int(time.time() - self._session_start_ts)
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
            self._b_runtime.set_value(f"{h:02d}:{m:02d}:{s:02d}")

            # Session W/L from match_log tail
            entries = load_entries()[self._session_baseline:]
            w = l = d = 0
            for e in entries:
                c = classify(e.get("result", ""))
                if c == "win": w += 1
                elif c == "loss": l += 1
                else: d += 1
            if (w, l, d) != (self._wins, self._losses, self._draws):
                self._wins, self._losses, self._draws = w, l, d
                self._b_wins.set_value(str(w))
                self._b_losses.set_value(str(l))
