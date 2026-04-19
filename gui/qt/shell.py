import sys
import time
import threading
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                               QLabel, QFrame, QStackedWidget, QPushButton,
                               QButtonGroup, QScrollArea, QGridLayout, QSizePolicy,
                               QGraphicsOpacityEffect, QMessageBox)

import utils
import bot_control
from gui.qt.theme import QSS, COLORS
from gui.qt.widgets import NavButton, apply_shadow
from gui.qt.fighters_page import FightersPage
from gui.qt.history_page import HistoryPage
from gui.qt.settings_page import SettingsPage
from gui.qt.home_page import HomePage
from gui.qt.live_feed import LiveFeedPage, StdoutStreamer
from gui.qt.sessions import log_session
from gui.qt.preflight import validate as preflight_validate
from gui.qt.meta import display_name


class Shell(QMainWindow):
    bot_crashed = Signal(str)

    def __init__(self, brawlers, version_str, pyla_main=None):
        super().__init__()
        self.setWindowTitle(f"PylaAI v{version_str}")
        self.resize(1500, 900)
        self.setMinimumSize(1280, 800)
        self.brawler_data = None
        self.pyla_main = pyla_main
        self._started_at = time.time()
        self._bot_thread = None
        self._bot_running = False
        self._session_start_ts = None
        self._streamer = None
        self._stop_reason = "user_stopped"
        self.bot_crashed.connect(self._on_bot_crashed)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        main = QHBoxLayout(root)
        main.setContentsMargins(18, 18, 18, 18)
        main.setSpacing(16)

        self.sidebar = self._build_sidebar(version_str)
        main.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.home_page = HomePage(version_str)
        self.fighters_page = FightersPage(brawlers)
        self.history_page = HistoryPage()
        self.settings_page = SettingsPage()
        self.live_feed_page = LiveFeedPage()
        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.fighters_page)
        self.stack.addWidget(self.history_page)
        self.stack.addWidget(self.live_feed_page)
        self.stack.addWidget(self.settings_page)
        main.addWidget(self.stack, stretch=1)

        # Toast banner overlay (hidden by default, positioned in resizeEvent)
        self._toast = QFrame(self)
        self._toast.setObjectName("toast")
        self._toast.setVisible(False)
        tl = QHBoxLayout(self._toast)
        tl.setContentsMargins(16, 12, 12, 12)
        tl.setSpacing(12)
        self._toast_icon = QLabel("⚠")
        self._toast_icon.setStyleSheet("color: white; font-size: 18px; font-weight: 800;")
        self._toast_msg = QLabel("")
        self._toast_msg.setStyleSheet("color: white; font-size: 13px; font-weight: 600;")
        self._toast_msg.setWordWrap(True)
        tl.addWidget(self._toast_icon)
        tl.addWidget(self._toast_msg, stretch=1)
        close_t = QPushButton("✕")
        close_t.setCursor(Qt.PointingHandCursor)
        close_t.setFixedSize(22, 22)
        close_t.setStyleSheet("background: transparent; color: white; border: none; font-weight: 800;")
        close_t.clicked.connect(self._hide_toast)
        tl.addWidget(close_t)
        self._toast.setStyleSheet(
            "QFrame#toast { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #b91c1c, stop:1 #ef4444); border-radius: 12px; }"
        )
        self._toast_effect = QGraphicsOpacityEffect(self._toast)
        self._toast.setGraphicsEffect(self._toast_effect)
        self._toast_anim = QPropertyAnimation(self._toast_effect, b"opacity", self)
        self._toast_anim.setDuration(250)
        self._toast_hide_timer = QTimer(self)
        self._toast_hide_timer.setSingleShot(True)
        self._toast_hide_timer.timeout.connect(self._hide_toast)

        self.fighters_page.queue_changed.connect(self._on_queue_changed)
        self._on_queue_changed(0)

        # Runtime ticker
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick_runtime)
        self._timer.start()

        self.setStyleSheet(QSS)

    def _build_sidebar(self, version_str):
        sb = QFrame()
        sb.setObjectName("sidebar")
        sb.setFixedWidth(240)
        lay = QVBoxLayout(sb)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        # Logo row
        logo_row = QHBoxLayout()
        logo_row.setSpacing(10)
        badge = QLabel("★")
        badge.setObjectName("logoBadge")
        badge.setFixedSize(36, 36)
        badge.setAlignment(Qt.AlignCenter)
        logo_row.addWidget(badge)
        logo_col = QVBoxLayout()
        logo_col.setSpacing(0)
        logo = QLabel("PylaAI")
        logo.setObjectName("logo")
        sub = QLabel(f"V{version_str} · ARENA BOT")
        sub.setObjectName("logoSub")
        logo_col.addWidget(logo)
        logo_col.addWidget(sub)
        logo_row.addLayout(logo_col)
        logo_row.addStretch()
        lay.addLayout(logo_row)
        lay.addSpacing(12)

        # Nav buttons
        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        entries = [
            ("Home", "⌂", None),
            ("Brawlers", "▦", "0"),
            ("Match History", "⏱", None),
            ("Live Feed", "◉", None),
            ("Settings", "⚙", None),
        ]
        self._nav_buttons = []
        for idx, (label, icon, badge_txt) in enumerate(entries):
            btn = NavButton(label, icon, badge_txt)
            btn.clicked.connect(lambda _, i=idx: self._switch_page(i))
            self._nav_group.addButton(btn, idx)
            lay.addWidget(btn)
            self._nav_buttons.append(btn)
        self._nav_buttons[0].setChecked(True)

        lay.addStretch()

        # Status box
        status = QFrame()
        status.setObjectName("statusBox")
        sl = QVBoxLayout(status)
        sl.setContentsMargins(14, 12, 14, 12)
        sl.setSpacing(6)

        def row(k, v, accent_color=None):
            r = QHBoxLayout()
            kl = QLabel(k.upper())
            kl.setObjectName("statusKey")
            vl = QLabel(v)
            vl.setObjectName("statusVal")
            if accent_color:
                vl.setStyleSheet(f"color: {accent_color}; font-weight: 800;")
            r.addWidget(kl)
            r.addStretch()
            r.addWidget(vl)
            return r, vl

        status_row_layout = QHBoxLayout()
        dot = QLabel("●")
        dot.setObjectName("statusDot")
        k = QLabel("BOT STATUS")
        k.setObjectName("statusKey")
        self._status_val = QLabel("Idle")
        self._status_val.setObjectName("statusVal")
        status_row_layout.addWidget(dot)
        status_row_layout.addWidget(k)
        status_row_layout.addStretch()
        status_row_layout.addWidget(self._status_val)
        sl.addLayout(status_row_layout)

        wl_row, self._wl_val = row("SESSION W/L", "0 / 0")
        sl.addLayout(wl_row)
        rt_row, self._rt_val = row("RUNTIME", "00:00:00")
        sl.addLayout(rt_row)
        lay.addWidget(status)

        # Start button
        self.start_btn = QPushButton("▶  START BOT")
        self.start_btn.setObjectName("startBot")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self._on_start)
        lay.addWidget(self.start_btn)

        # Pause button (hidden unless running)
        self.pause_btn = QPushButton("❚❚  PAUSE")
        self.pause_btn.setObjectName("pauseBtn")
        self.pause_btn.setCursor(Qt.PointingHandCursor)
        self.pause_btn.setVisible(False)
        self.pause_btn.clicked.connect(self._on_pause_toggle)
        self.pause_btn.setStyleSheet(
            f"QPushButton#pauseBtn {{"
            f" background: {COLORS['bg_card_hi']}; color: {COLORS['text']};"
            f" border: 1px solid {COLORS['border_hi']}; border-radius: 10px;"
            f" padding: 10px; font-weight: 800; font-size: 12px; letter-spacing: 1px; }}"
            f"QPushButton#pauseBtn:hover {{ background: {COLORS['bg_card']}; }}"
            f"QPushButton#pauseBtn[paused=\"true\"] {{"
            f" background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #f59e0b, stop:1 #fbbf24);"
            f" color: #1a1a1a; border: 1px solid #f59e0b; }}"
        )
        lay.addWidget(self.pause_btn)

        # Footer version hint
        vhint = QLabel(f"PYLA · v{version_str}")
        vhint.setAlignment(Qt.AlignCenter)
        vhint.setStyleSheet(f"color: {COLORS['text_faint']}; font-size: 9px; letter-spacing: 2px;")
        lay.addWidget(vhint)
        return sb

    def _build_stub(self, title, subtitle):
        w = QFrame()
        w.setObjectName("panel")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(40, 40, 40, 40)
        t = QLabel(title)
        t.setObjectName("pageTitle")
        s = QLabel(subtitle)
        s.setStyleSheet(f"color: {COLORS['text_faint']}; font-size: 13px;")
        lay.addWidget(t)
        lay.addWidget(s)
        lay.addStretch()
        return w

    def _switch_page(self, idx):
        self.stack.setCurrentIndex(idx)

    def _on_queue_changed(self, n):
        self._nav_buttons[1].set_badge(str(n) if n > 0 else None)
        self._refresh_start_tooltip()

    def _refresh_start_tooltip(self):
        try:
            queue = list(self.fighters_page.queue)
        except Exception:
            queue = []
        if not queue:
            self.start_btn.setToolTip("Queue is empty — add a brawler on the Brawlers page.")
            return
        try:
            gc = utils.load_toml_as_dict("cfg/general_config.toml")
            total_min = int(gc.get("run_for_minutes", 60) or 60)
        except Exception:
            total_min = 60
        chain = " → ".join(display_name(b) for b in queue)
        hours = total_min // 60
        mins = total_min % 60
        total_str = (f"{hours}h {mins:02d}m" if hours else f"{mins}m")
        self.start_btn.setToolTip(
            f"Will run: {chain}\n~{total_str} total · stops after timer"
        )

    def _tick_runtime(self):
        base = self._session_start_ts if self._bot_running else self._started_at
        elapsed = int(time.time() - base)
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        s = elapsed % 60
        self._rt_val.setText(f"{h:02d}:{m:02d}:{s:02d}")
        if self._bot_running:
            w = self.live_feed_page._wins
            l = self.live_feed_page._losses
            self._wl_val.setText(f"{w} / {l}")

    def _set_status(self, text, color=None):
        self._status_val.setText(text)
        if color:
            self._status_val.setStyleSheet(f"color: {color}; font-weight: 800;")

    def _on_start(self):
        if self._bot_running:
            self._on_stop()
            return
        data = self.fighters_page.build_brawler_data()

        # Pre-flight validation
        try:
            gc = utils.load_toml_as_dict("cfg/general_config.toml")
            emu = gc.get("current_emulator", "LDPlayer")
            auto_reconnect = str(gc.get("auto_reconnect_adb", "yes")).lower() in ("yes", "true")
        except Exception:
            emu = "LDPlayer"
            auto_reconnect = True
        problems = preflight_validate(data, emu, auto_reconnect=auto_reconnect)
        if problems:
            bullets = "  •  ".join(problems[:4])
            suffix = f" (+{len(problems) - 4} more)" if len(problems) > 4 else ""
            self.show_toast(f"Cannot start:  •  {bullets}{suffix}",
                            tone="error", duration_ms=9000)
            return

        self.brawler_data = data
        utils.save_brawler_data(data)

        # Redirect stdout so the Live Feed captures console output
        self._streamer = StdoutStreamer()
        self.live_feed_page.attach_streamer(self._streamer)
        sys.stdout = self._streamer
        sys.stderr = self._streamer

        self._session_start_ts = time.time()
        self.live_feed_page.mark_session_started()

        # Switch to Live Feed page
        self.stack.setCurrentIndex(3)
        self._nav_buttons[3].setChecked(True)

        # Update UI state
        self._bot_running = True
        self.start_btn.setText("■  STOP BOT")
        self.start_btn.setProperty("stopping", "true")
        self.start_btn.style().unpolish(self.start_btn); self.start_btn.style().polish(self.start_btn)
        self.pause_btn.setVisible(True)
        self.pause_btn.setText("❚❚  PAUSE")
        self.pause_btn.setProperty("paused", "false")
        self.pause_btn.style().unpolish(self.pause_btn); self.pause_btn.style().polish(self.pause_btn)
        self._set_status("Running", COLORS.get("green", "#22c55e"))

        # Clear any previous stop/pause request and launch bot in background
        bot_control.clear_stop()
        bot_control.clear_pause()

        if self.pyla_main:
            self._bot_thread = threading.Thread(
                target=self._run_bot, args=(data,), daemon=True)
            self._bot_thread.start()

        # Poll for thread exit so we can reset the UI if the bot finishes on its own
        self._exit_poll = QTimer(self)
        self._exit_poll.setInterval(500)
        self._exit_poll.timeout.connect(self._check_bot_alive)
        self._exit_poll.start()

    def _on_stop(self):
        if not self._bot_running:
            return
        # Confirm if session is very short (< 60s) — guards against accidental clicks
        if self._session_start_ts and (time.time() - self._session_start_ts) < 60:
            reply = QMessageBox.question(
                self, "Stop Bot?",
                "The bot has only been running for a few seconds. Stop anyway?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        self._stop_reason = "user_stopped"
        self.start_btn.setEnabled(False)
        self.start_btn.setText("■  STOPPING...")
        self.pause_btn.setEnabled(False)
        self._set_status("Stopping", COLORS.get("yellow", "#facc15"))
        print("[GUI] Stop requested — waiting for bot loop to exit...")
        bot_control.request_stop()

    def _on_pause_toggle(self):
        if not self._bot_running:
            return
        if bot_control.is_paused():
            bot_control.clear_pause()
            self.pause_btn.setText("❚❚  PAUSE")
            self.pause_btn.setProperty("paused", "false")
            self._set_status("Running", COLORS.get("green", "#22c55e"))
            print("[GUI] Resume requested.")
        else:
            bot_control.request_pause()
            self.pause_btn.setText("▶  RESUME")
            self.pause_btn.setProperty("paused", "true")
            self._set_status("Paused", COLORS.get("yellow", "#f59e0b"))
            print("[GUI] Pause requested — bot will hold between frames.")
        self.pause_btn.style().unpolish(self.pause_btn); self.pause_btn.style().polish(self.pause_btn)

    def _check_bot_alive(self):
        if self._bot_thread and not self._bot_thread.is_alive():
            self._exit_poll.stop()
            self._finalize_stop()

    def _finalize_stop(self):
        # Log the session before clearing state
        if self._session_start_ts:
            try:
                log_session(
                    start_ts=self._session_start_ts,
                    end_ts=time.time(),
                    wins=self.live_feed_page._wins,
                    losses=self.live_feed_page._losses,
                    draws=self.live_feed_page._draws,
                    reason=self._stop_reason,
                )
                if hasattr(self, "home_page") and hasattr(self.home_page, "refresh_recent_runs"):
                    self.home_page.refresh_recent_runs()
                if hasattr(self, "history_page") and hasattr(self.history_page, "refresh_sessions"):
                    self.history_page.refresh_sessions()
            except Exception as e:
                print(f"[GUI] Failed to log session: {e}")

        self._bot_running = False
        self._bot_thread = None
        self._session_start_ts = None
        self._stop_reason = "user_stopped"

        # Restore stdout
        try:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
        except Exception:
            pass

        self.live_feed_page.mark_session_stopped()
        self.start_btn.setEnabled(True)
        self.start_btn.setText("▶  START BOT")
        self.start_btn.setProperty("stopping", "false")
        self.start_btn.style().unpolish(self.start_btn); self.start_btn.style().polish(self.start_btn)
        bot_control.clear_pause()
        self.pause_btn.setVisible(False)
        self.pause_btn.setEnabled(True)
        self.pause_btn.setText("❚❚  PAUSE")
        self.pause_btn.setProperty("paused", "false")
        self.pause_btn.style().unpolish(self.pause_btn); self.pause_btn.style().polish(self.pause_btn)
        self._set_status("Idle", COLORS.get("text_faint", "#94a3b8"))

        try:
            gc = utils.load_toml_as_dict("cfg/general_config.toml")
            if str(gc.get("notify_on_session_end", "yes")).lower() in ("yes", "true"):
                reason_tone = {"crashed": "error", "finished": "success",
                               "user_stopped": "info"}.get(self._stop_reason, "info")
                w = getattr(self.live_feed_page, "_wins", 0)
                l = getattr(self.live_feed_page, "_losses", 0)
                self.show_toast(
                    f"Session ended ({self._stop_reason.replace('_', ' ')})  ·  {w}W / {l}L",
                    tone=reason_tone, duration_ms=5000)
        except Exception:
            pass

    def _run_bot(self, data):
        try:
            self.pyla_main(data)
            # Normal exit: either user pressed Stop or the bot timer ran out
            if not bot_control.is_stop_requested():
                self._stop_reason = "finished"
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"[ERROR] Bot crashed: {e}\n{tb}")
            self._stop_reason = "crashed"
            # Emit signal so toast is shown on main thread
            self.bot_crashed.emit(str(e) or e.__class__.__name__)

    # ---------- Toast / crash handling ----------
    def _on_bot_crashed(self, message: str):
        self.show_toast(f"Bot crashed: {message}", tone="error")

    def show_toast(self, message: str, tone: str = "error", duration_ms: int = 6000):
        gradients = {
            "error":   ("#b91c1c", "#ef4444", "⚠"),
            "warn":    ("#b45309", "#f59e0b", "⚠"),
            "success": ("#15803d", "#22c55e", "✓"),
            "info":    ("#1d4ed8", "#3b82f6", "ℹ"),
        }
        c1, c2, icon = gradients.get(tone, gradients["error"])
        self._toast.setStyleSheet(
            f"QFrame#toast {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {c1}, stop:1 {c2}); border-radius: 12px; }}"
        )
        self._toast_icon.setText(icon)
        self._toast_msg.setText(message)
        self._position_toast()
        self._toast.setVisible(True)
        self._toast.raise_()
        self._toast_anim.stop()
        self._toast_anim.setStartValue(self._toast_effect.opacity() or 0.0)
        self._toast_anim.setEndValue(1.0)
        self._toast_anim.start()
        self._toast_hide_timer.start(duration_ms)

    def _hide_toast(self):
        self._toast_hide_timer.stop()
        self._toast_anim.stop()
        self._toast_anim.setStartValue(self._toast_effect.opacity())
        self._toast_anim.setEndValue(0.0)
        try:
            self._toast_anim.finished.disconnect()
        except Exception:
            pass
        self._toast_anim.finished.connect(lambda: self._toast.setVisible(False))
        self._toast_anim.start()

    def _position_toast(self):
        w = min(560, max(320, self.width() - 80))
        self._toast.setFixedWidth(w)
        self._toast.adjustSize()
        x = (self.width() - self._toast.width()) // 2
        y = 24
        self._toast.move(x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_toast") and self._toast.isVisible():
            self._position_toast()

    def closeEvent(self, event):
        # If minimize-to-tray is enabled AND the bot is still running,
        # hide the window instead of closing so the bot keeps going.
        try:
            gc = utils.load_toml_as_dict("cfg/general_config.toml")
            minimize = str(gc.get("minimize_to_tray", "no")).lower() in ("yes", "true")
        except Exception:
            minimize = False
        if minimize and self._bot_running:
            event.ignore()
            self.hide()
            self.show_toast("PylaAI minimized — bot continues running in background.",
                            tone="info", duration_ms=4000)
            return
        if self._bot_running:
            try:
                bot_control.request_stop()
            except Exception:
                pass
        super().closeEvent(event)
