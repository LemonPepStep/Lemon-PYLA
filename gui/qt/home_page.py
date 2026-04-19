from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QFrame, QPushButton, QSizePolicy)

from gui.qt.widgets import apply_shadow
from gui.qt.theme import COLORS
from gui.qt.sessions import recent_sessions, format_duration
from utils import load_toml_as_dict, save_dict_as_toml


ORIENTATIONS = [
    (3, "Vertical",   "portrait"),
    (5, "Horizontal", "landscape"),
]

GAMEMODES = {
    3: [
        ("brawlball",      "Brawl Ball",     "⚽"),
        ("showdown",       "Showdown Trio",  "💀"),
        ("other",          "Other",          "✦"),
    ],
    5: [
        ("basketbrawl",    "Basket Brawl",   "🏀"),
        ("brawlball_5v5",  "Brawl Ball 5v5", "⚽"),
    ],
}

EMULATORS = [
    ("LDPlayer",   "127.0.0.1:5555", "🟣"),
    ("BlueStacks", "127.0.0.1:5037", "🔵"),
    ("MEmu",       "127.0.0.1:21503", "🟢"),
    ("Others",     "custom device",   "⚙"),
]


class ChoiceCard(QPushButton):
    def __init__(self, title, subtitle, icon, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(76)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(12)
        ic = QLabel(icon)
        ic.setFixedSize(42, 42)
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #8b5cf6,stop:1 #ec4899);"
            f"border-radius: 10px; color: white; font-size: 18px; font-weight: 800;")
        lay.addWidget(ic)
        col = QVBoxLayout()
        col.setSpacing(2)
        t = QLabel(title)
        t.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: 800;")
        s = QLabel(subtitle.upper())
        s.setStyleSheet(f"color: {COLORS['text_faint']}; font-size: 9px; font-weight: 700; letter-spacing: 1.3px;")
        col.addWidget(t); col.addWidget(s)
        lay.addLayout(col)
        lay.addStretch()
        self._apply(False)
        self.toggled.connect(self._apply)

    def _apply(self, active):
        if active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 rgba(139,92,246,0.22), stop:1 rgba(236,72,153,0.18));
                    border: 1.5px solid {COLORS['accent_hi']};
                    border-radius: 14px;
                    text-align: left;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['bg_card']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 14px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background: {COLORS['bg_card_hi']};
                    border: 1px solid {COLORS['border_hi']};
                }}
            """)


class SectionCard(QFrame):
    def __init__(self, icon, title, subtitle, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 20)
        outer.setSpacing(14)
        hdr = QHBoxLayout()
        hdr.setSpacing(10)
        ic = QLabel(icon)
        ic.setFixedSize(32, 32)
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #f59e0b,stop:1 #ec4899);"
            f"border-radius: 8px; color: white; font-size: 14px; font-weight: 800;")
        hdr.addWidget(ic)
        col = QVBoxLayout()
        col.setSpacing(1)
        t = QLabel(title); t.setStyleSheet(f"color: {COLORS['text']}; font-size: 16px; font-weight: 800;")
        s = QLabel(subtitle.upper()); s.setStyleSheet(f"color: {COLORS['text_faint']}; font-size: 9px; font-weight: 700; letter-spacing: 1.5px;")
        col.addWidget(t); col.addWidget(s)
        hdr.addLayout(col); hdr.addStretch()
        outer.addLayout(hdr)
        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        outer.addLayout(self.body)
        apply_shadow(self, blur=20, alpha=70, dy=4)

    def add(self, widget):
        self.body.addWidget(widget)
    def add_layout(self, layout):
        self.body.addLayout(layout)


class HomePage(QWidget):
    config_changed = Signal()

    def __init__(self, version_str, parent=None):
        super().__init__(parent)
        self.version_str = version_str
        self.bot_cfg_path = "cfg/bot_config.toml"
        self.gen_cfg_path = "cfg/general_config.toml"
        self.bot = load_toml_as_dict(self.bot_cfg_path)
        self.gen = load_toml_as_dict(self.gen_cfg_path)
        self.bot.setdefault("gamemode_type", 3)
        self.bot.setdefault("gamemode", "brawlball")
        self.gen.setdefault("current_emulator", "LDPlayer")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        # Header
        head = QFrame()
        head.setObjectName("panel")
        hl = QVBoxLayout(head)
        hl.setContentsMargins(24, 22, 24, 22)
        hl.setSpacing(6)
        title_row = QHBoxLayout()
        t1 = QLabel("Welcome to ")
        t1.setObjectName("pageTitle")
        t2 = QLabel("PylaAI")
        t2.setObjectName("pageTitleAccent")
        title_row.addWidget(t1); title_row.addWidget(t2); title_row.addStretch()
        ver = QLabel(f"V{version_str}")
        ver.setObjectName("countPill")
        title_row.addWidget(ver)
        hl.addLayout(title_row)
        sub = QLabel("Pick your battlefield, mode and device — then jump to Brawlers to queue a run.")
        sub.setStyleSheet(f"color: {COLORS['text_faint']}; font-size: 12px;")
        hl.addWidget(sub)
        apply_shadow(head, blur=22, alpha=70, dy=6)
        root.addWidget(head)

        # Grid of the three sections
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)

        # ---- Map Orientation ----
        self.orient_card = SectionCard("🧭", "Map Orientation", "Choose map layout")
        self._orient_btns = {}
        orient_row = QHBoxLayout()
        orient_row.setSpacing(10)
        for code, name, desc in ORIENTATIONS:
            b = ChoiceCard(name, desc, "▯" if code == 3 else "▭")
            b.clicked.connect(lambda _, c=code: self._set_orientation(c))
            self._orient_btns[code] = b
            orient_row.addWidget(b)
        self.orient_card.add_layout(orient_row)
        grid.addWidget(self.orient_card, 0, 0)

        # ---- Game Mode ----
        self.mode_card = SectionCard("🎮", "Game Mode", "What the bot will play")
        self._mode_row_host = QWidget()
        self._mode_row = QHBoxLayout(self._mode_row_host)
        self._mode_row.setContentsMargins(0, 0, 0, 0)
        self._mode_row.setSpacing(10)
        self.mode_card.add(self._mode_row_host)
        grid.addWidget(self.mode_card, 0, 1)

        # ---- Emulator ----
        self.emu_card = SectionCard("📱", "Emulator Device", "Which emulator is running Brawl Stars")
        emu_grid = QGridLayout()
        emu_grid.setSpacing(10)
        self._emu_btns = {}
        for i, (name, dev, ic) in enumerate(EMULATORS):
            b = ChoiceCard(name, dev, ic)
            b.clicked.connect(lambda _, n=name: self._set_emulator(n))
            self._emu_btns[name] = b
            emu_grid.addWidget(b, i // 2, i % 2)
        self.emu_card.add_layout(emu_grid)
        grid.addWidget(self.emu_card, 1, 0, 1, 2)

        root.addLayout(grid)

        # ---- Recent Runs strip ----
        self.recent_card = SectionCard("⏱", "Recent Runs", "Last 3 bot sessions")
        self._recent_host = QWidget()
        self._recent_row = QHBoxLayout(self._recent_host)
        self._recent_row.setContentsMargins(0, 0, 0, 0)
        self._recent_row.setSpacing(10)
        self.recent_card.add(self._recent_host)
        root.addWidget(self.recent_card)

        root.addStretch()

        # Initial state
        self._refresh_orientation()
        self._rebuild_mode_row()
        self._refresh_emulator()
        self.refresh_recent_runs()

    # ---------- Recent runs ----------
    def refresh_recent_runs(self):
        while self._recent_row.count():
            it = self._recent_row.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)
        sessions = recent_sessions(3)
        if not sessions:
            empty = QLabel("No runs yet — start the bot to record a session.")
            empty.setStyleSheet(f"color: {COLORS['text_faint']}; font-size: 12px;")
            self._recent_row.addWidget(empty)
            self._recent_row.addStretch()
            return
        for s in sessions:
            self._recent_row.addWidget(self._build_run_card(s), stretch=1)
        # Pad with empty stretchers if fewer than 3
        for _ in range(3 - len(sessions)):
            self._recent_row.addStretch(1)

    def _build_run_card(self, s: dict) -> QFrame:
        reason_styles = {
            "user_stopped": ("#334155", "#94a3b8", "Stopped"),
            "crashed":      ("#7f1d1d", "#f87171", "Crashed"),
            "finished":     ("#14532d", "#4ade80", "Finished"),
        }
        bg, fg, label = reason_styles.get(s.get("reason", ""), ("#334155", "#94a3b8", s.get("reason", "unknown").title()))

        card = QFrame()
        card.setObjectName("card")
        card.setMinimumHeight(92)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(6)

        top = QHBoxLayout()
        dur = QLabel(format_duration(s.get("duration_s", 0)))
        dur.setStyleSheet(f"color: {COLORS['text']}; font-size: 18px; font-weight: 800;")
        top.addWidget(dur)
        top.addStretch()
        pill = QLabel(label.upper())
        pill.setStyleSheet(
            f"background: {bg}; color: {fg}; border-radius: 6px;"
            f"padding: 3px 8px; font-size: 9px; font-weight: 800; letter-spacing: 1.2px;"
        )
        top.addWidget(pill)
        lay.addLayout(top)

        w = int(s.get("wins", 0))
        l = int(s.get("losses", 0))
        d = int(s.get("draws", 0))
        total = w + l + d
        wr = int(round((w / total) * 100)) if total else 0
        stats = QLabel(f"{w}W · {l}L · {d}D  ·  {wr}% WR")
        stats.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px; font-weight: 700;")
        lay.addWidget(stats)

        try:
            import time as _t
            when = _t.strftime("%b %d · %H:%M", _t.localtime(s.get("end", 0)))
        except Exception:
            when = ""
        ts = QLabel(when)
        ts.setStyleSheet(f"color: {COLORS['text_faint']}; font-size: 10px; letter-spacing: 0.5px;")
        lay.addWidget(ts)

        apply_shadow(card, blur=14, alpha=60, dy=3)
        return card

    # ---------- handlers ----------
    def _set_orientation(self, code):
        self.bot["gamemode_type"] = code
        valid = [gm for gm, _, _ in GAMEMODES[code]]
        if self.bot.get("gamemode") not in valid:
            self.bot["gamemode"] = valid[0]
        save_dict_as_toml(self.bot, self.bot_cfg_path)
        self._refresh_orientation()
        self._rebuild_mode_row()
        self.config_changed.emit()

    def _refresh_orientation(self):
        cur = int(self.bot.get("gamemode_type", 3))
        for code, btn in self._orient_btns.items():
            btn.setChecked(code == cur)

    def _rebuild_mode_row(self):
        while self._mode_row.count():
            it = self._mode_row.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)
        code = int(self.bot.get("gamemode_type", 3))
        current = self.bot.get("gamemode", "brawlball")
        self._mode_btns = {}
        for gm, label, icon in GAMEMODES.get(code, []):
            b = ChoiceCard(label, gm.replace("_", " "), icon)
            b.setChecked(gm == current)
            b.clicked.connect(lambda _, g=gm: self._set_mode(g))
            self._mode_btns[gm] = b
            self._mode_row.addWidget(b)

    def _set_mode(self, gm):
        self.bot["gamemode"] = gm
        save_dict_as_toml(self.bot, self.bot_cfg_path)
        for name, btn in self._mode_btns.items():
            btn.setChecked(name == gm)
        self.config_changed.emit()

    def _set_emulator(self, name):
        self.gen["current_emulator"] = name
        save_dict_as_toml(self.gen, self.gen_cfg_path)
        self._refresh_emulator()
        self.config_changed.emit()

    def _refresh_emulator(self):
        cur = self.gen.get("current_emulator", "LDPlayer")
        for name, btn in self._emu_btns.items():
            btn.setChecked(name == cur)
