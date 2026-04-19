import json
import os
from PySide6.QtCore import Qt, Signal, QMimeData, QPoint
from PySide6.QtGui import QIcon, QPixmap, QDrag
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QLineEdit, QScrollArea, QFrame, QComboBox,
                               QPushButton, QCheckBox, QSpinBox, QSizePolicy)

from gui.qt.widgets import FighterCard, FilterChip, apply_shadow
from gui.qt.meta import rarity_of, rarity_rank, rarity_label, display_name, short_code
from gui.qt.theme import COLORS, RARITY_COLORS, gradient_for
from utils import load_toml_as_dict, save_dict_as_toml, save_brawler_icon


FIGHTERS_STATE_PATH = "cfg/fighters_state.json"


class QueueChip(QFrame):
    """Brawler icon chip with a small ✕ button to remove from queue.
    Drag to reorder, click to edit that brawler's config."""
    remove_requested = Signal(str)
    edit_requested = Signal(str)
    reorder_requested = Signal(str, str)  # dragged_brawler, target_brawler

    MIME_TYPE = "application/x-pyla-queue-chip"

    def __init__(self, brawler: str, parent=None):
        super().__init__(parent)
        self.brawler = brawler
        self.setFixedSize(42, 42)
        self.setCursor(Qt.PointingHandCursor)
        self.setAcceptDrops(True)
        self.setToolTip(f"{brawler.title()} — click to edit, drag to reorder")
        self._drag_start_pos = None

        c1, c2 = gradient_for(brawler)
        icon_path = f"./api/assets/brawler_icons/{brawler}.png"

        self._icon_lbl = QLabel(self)
        self._icon_lbl.setFixedSize(32, 32)
        self._icon_lbl.move(4, 5)
        self._icon_lbl.setAlignment(Qt.AlignCenter)
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path).scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._icon_lbl.setPixmap(pix)
        else:
            self._icon_lbl.setText(short_code(brawler))
            self._icon_lbl.setStyleSheet("color: white; font-weight: 800; font-size: 10px;")
        self._base_style = (
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {c1},stop:1 {c2});"
            f" border-radius: 8px;"
        )
        self._icon_lbl.setStyleSheet(self._icon_lbl.styleSheet() + self._base_style)

        x_btn = QPushButton("✕", self)
        x_btn.setFixedSize(16, 16)
        x_btn.move(26, 0)
        x_btn.setCursor(Qt.PointingHandCursor)
        x_btn.setStyleSheet(
            "background: #ef4444; color: white; border-radius: 8px;"
            "font-size: 9px; font-weight: 800; border: none; padding: 0;"
        )
        x_btn.clicked.connect(lambda: self.remove_requested.emit(self.brawler))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton) or self._drag_start_pos is None:
            return
        if (event.position().toPoint() - self._drag_start_pos).manhattanLength() < 8:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(self.MIME_TYPE, self.brawler.encode("utf-8"))
        drag.setMimeData(mime)
        drag.setPixmap(self.grab())
        drag.setHotSpot(self._drag_start_pos)
        drag.exec(Qt.MoveAction)
        self._drag_start_pos = None

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._drag_start_pos is not None:
            if (event.position().toPoint() - self._drag_start_pos).manhattanLength() < 8:
                self.edit_requested.emit(self.brawler)
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(self.MIME_TYPE):
            event.acceptProposedAction()
            self._icon_lbl.setStyleSheet(
                self._icon_lbl.styleSheet() + " border: 2px solid #22d3ee;"
            )

    def dragLeaveEvent(self, event):
        self._icon_lbl.setStyleSheet(self._base_style)

    def dropEvent(self, event):
        self._icon_lbl.setStyleSheet(self._base_style)
        if not event.mimeData().hasFormat(self.MIME_TYPE):
            return
        src = bytes(event.mimeData().data(self.MIME_TYPE)).decode("utf-8")
        if src != self.brawler:
            self.reorder_requested.emit(src, self.brawler)
        event.acceptProposedAction()


def _load_fighters_state():
    if not os.path.exists(FIGHTERS_STATE_PATH):
        return {}
    try:
        with open(FIGHTERS_STATE_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_fighters_state(state):
    os.makedirs(os.path.dirname(FIGHTERS_STATE_PATH), exist_ok=True)
    with open(FIGHTERS_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


class FightersPage(QWidget):
    queue_changed = Signal(int)

    def __init__(self, brawlers, parent=None):
        super().__init__(parent)
        self.brawlers = brawlers
        self.state = _load_fighters_state()
        saved_queue = self.state.get("__queue__", []) if isinstance(self.state, dict) else []
        self.queue = [b for b in saved_queue if b in brawlers]
        if "__queue__" in self.state:
            del self.state["__queue__"]
        self.selected = None   # str
        self._cards = {}       # brawler -> FighterCard
        self._current_filter = "All"
        self._search = ""

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        root.addWidget(self._build_grid_panel(), stretch=1)
        root.addWidget(self._build_configure_panel(), stretch=0)

        if self.brawlers:
            self._select_fighter(self.brawlers[0])
        # Emit initial queue count (after UI built)
        if self.queue:
            self._refresh_queue_row()
            for b in self.queue:
                if b in self._cards:
                    self._cards[b].set_queued(True)
            self.queue_changed.emit(len(self.queue))

    # ------- Grid panel -------
    def _build_grid_panel(self):
        panel = QFrame()
        panel.setObjectName("panel")
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(22, 20, 22, 20)
        outer.setSpacing(16)

        # Title row
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        t1 = QLabel("Select a ")
        t1.setObjectName("pageTitle")
        t2 = QLabel("Brawler")
        t2.setObjectName("pageTitleAccent")
        pill = QLabel(f"{len(self.brawlers)} UNITS")
        pill.setObjectName("countPill")
        title_row.addWidget(t1)
        title_row.addWidget(t2)
        title_row.addSpacing(10)
        title_row.addWidget(pill)
        title_row.addStretch()

        search = QLineEdit()
        search.setObjectName("search")
        search.setPlaceholderText("🔍   Search by name, role, trait...")
        search.setFixedWidth(320)
        search.textChanged.connect(self._on_search)
        title_row.addWidget(search)
        outer.addLayout(title_row)

        # Filter chips
        chips_row = QHBoxLayout()
        chips_row.setSpacing(8)
        self._chips = {}
        for label in ["All", "Queued", "Ultra Legendary", "Legendary", "Mythic", "Epic", "Super Rare", "Rare"]:
            c = FilterChip(label)
            if label == "All":
                c.setChecked(True)
            c.clicked.connect(lambda _, lbl=label: self._on_filter(lbl))
            self._chips[label] = c
            chips_row.addWidget(c)
        chips_row.addStretch()
        outer.addLayout(chips_row)

        # Grid
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        grid_host = QWidget()
        self.grid = QGridLayout(grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(12)
        self.scroll.setWidget(grid_host)

        for b in self.brawlers:
            icon_path = f"./api/assets/brawler_icons/{b}.png"
            if not os.path.exists(icon_path):
                try:
                    save_brawler_icon(b)
                except Exception:
                    pass
            card = FighterCard(b, self._trophies_for(b), icon_path)
            card.clicked.connect(self._select_fighter)
            self._cards[b] = card

        self._rebuild_grid()
        outer.addWidget(self.scroll, stretch=1)
        return panel

    def _trophies_for(self, brawler):
        s = self.state.get(brawler, {})
        return int(s.get("trophies", 0) or 0)

    def _rebuild_grid(self):
        # Clear grid
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        visible = [b for b in self.brawlers if self._matches(b)]
        cols = 5
        r = c = 0
        for b in visible:
            card = self._cards[b]
            card.set_queued(b in self.queue)
            card.set_selected(b == self.selected)
            self.grid.addWidget(card, r, c)
            c += 1
            if c >= cols:
                c = 0
                r += 1
        # push content up
        self.grid.setRowStretch(r + 1, 1)

    def _matches(self, b):
        if self._search and self._search.lower() not in b.lower():
            return False
        f = self._current_filter
        if f == "All":
            return True
        if f == "Queued":
            return b in self.queue
        rmap = {"Ultra Legendary": "ULEG", "Legendary": "LEG", "Mythic": "MYTH",
                "Epic": "EPIC", "Super Rare": "SR", "Rare": "RARE"}
        return rarity_of(b) == rmap.get(f, "")

    def _on_filter(self, label):
        self._current_filter = label
        for lbl, chip in self._chips.items():
            chip.setChecked(lbl == label)
        self._rebuild_grid()

    def _on_search(self, text):
        self._search = text.strip()
        self._rebuild_grid()

    def _select_fighter(self, brawler):
        self.selected = brawler
        for b, card in self._cards.items():
            card.set_selected(b == brawler)
        self._populate_config(brawler)

    # ------- Configure panel -------
    def _build_configure_panel(self):
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setFixedWidth(340)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(14)

        top_row = QHBoxLayout()
        t = QLabel("Configure Run")
        t.setObjectName("pageTitle")
        t.setStyleSheet("font-size: 18px; font-weight: 800;")
        top_row.addWidget(t)
        top_row.addStretch()
        hint = QLabel("PER BRAWLER")
        hint.setObjectName("countPill")
        top_row.addWidget(hint)
        lay.addLayout(top_row)

        # Selected header card
        self.sel_card = QFrame()
        self.sel_card.setObjectName("card")
        sel_lay = QHBoxLayout(self.sel_card)
        sel_lay.setContentsMargins(12, 12, 12, 12)
        sel_lay.setSpacing(12)
        self.sel_icon = QLabel()
        self.sel_icon.setFixedSize(52, 52)
        self.sel_icon.setAlignment(Qt.AlignCenter)
        sel_lay.addWidget(self.sel_icon)
        name_col = QVBoxLayout()
        name_col.setSpacing(2)
        self.sel_name = QLabel("—")
        self.sel_name.setStyleSheet("font-size: 15px; font-weight: 800;")
        self.sel_sub = QLabel("")
        self.sel_sub.setStyleSheet(f"color: {COLORS['text_faint']}; font-size: 10px; letter-spacing: 1.2px; font-weight: 700;")
        name_col.addWidget(self.sel_name)
        name_col.addWidget(self.sel_sub)
        sel_lay.addLayout(name_col)
        sel_lay.addStretch()
        apply_shadow(self.sel_card, blur=18, alpha=70, dy=4)
        lay.addWidget(self.sel_card)

        # Emulator
        lay.addWidget(self._sub_label("EMULATOR DEVICE"))
        self.emu_combo = QComboBox()
        self.emu_combo.addItems([
            "127.0.0.1:5555 · LDPlayer",
            "127.0.0.1:5565 · LDPlayer #2",
            "127.0.0.1:5037 · BlueStacks",
            "127.0.0.1:21503 · MEmu",
            "Others",
        ])
        gc = load_toml_as_dict("cfg/general_config.toml")
        cur = gc.get("current_emulator", "LDPlayer")
        for i in range(self.emu_combo.count()):
            if cur in self.emu_combo.itemText(i):
                self.emu_combo.setCurrentIndex(i)
                break
        self.emu_combo.currentTextChanged.connect(self._on_emu_change)
        lay.addWidget(self.emu_combo)

        # Push mode
        lay.addWidget(self._sub_label_row("PUSH MODE", "pick a goal"))
        mode_row = QHBoxLayout()
        mode_row.setSpacing(0)
        self.trophies_btn = QPushButton("🏆  Trophies")
        self.trophies_btn.setObjectName("toggleLeft")
        self.trophies_btn.setCheckable(True)
        self.trophies_btn.setChecked(True)
        self.wins_btn = QPushButton("✓  Wins")
        self.wins_btn.setObjectName("toggleRight")
        self.wins_btn.setCheckable(True)
        self.trophies_btn.clicked.connect(lambda: self._set_mode("trophies"))
        self.wins_btn.clicked.connect(lambda: self._set_mode("wins"))
        mode_row.addWidget(self.trophies_btn)
        mode_row.addWidget(self.wins_btn)
        lay.addLayout(mode_row)

        # Target + Current
        tc_row = QHBoxLayout()
        tc_row.setSpacing(10)
        target_col = QVBoxLayout()
        target_col.setSpacing(4)
        target_col.addWidget(self._sub_label("TARGET"))
        self.target_input = QLineEdit("1200")
        target_col.addWidget(self.target_input)
        cur_col = QVBoxLayout()
        cur_col.setSpacing(4)
        self.cur_label = QLabel("CURRENT TROPHIES")
        self.cur_label.setObjectName("subLabel")
        cur_col.addWidget(self.cur_label)
        self.cur_input = QLineEdit("0")
        cur_col.addWidget(self.cur_input)
        tc_row.addLayout(target_col)
        tc_row.addLayout(cur_col)
        lay.addLayout(tc_row)

        lay.addWidget(self._sub_label("WIN STREAK"))
        self.streak_input = QLineEdit("0")
        lay.addWidget(self.streak_input)

        self.auto_cb = QCheckBox("Bot auto-selects this brawler in lobby")
        self.auto_cb.setChecked(True)
        lay.addWidget(self.auto_cb)

        # Run duration
        dur_row = QHBoxLayout()
        dur_row.setSpacing(10)
        dur_lbl = QLabel("RUN FOR")
        dur_lbl.setObjectName("subLabel")
        dur_row.addWidget(dur_lbl)
        self.dur_input = QLineEdit(str(gc.get("run_for_minutes", 60)))
        self.dur_input.setFixedWidth(80)
        dur_row.addStretch()
        dur_row.addWidget(self.dur_input)
        min_lbl = QLabel("min")
        min_lbl.setStyleSheet(f"color: {COLORS['text_faint']}; font-weight: 700;")
        dur_row.addWidget(min_lbl)
        dur_frame = QFrame()
        dur_frame.setObjectName("card")
        dur_frame_lay = QHBoxLayout(dur_frame)
        dur_frame_lay.setContentsMargins(14, 12, 14, 12)
        for i in range(dur_row.count()):
            item = dur_row.itemAt(i)
        while dur_row.count():
            it = dur_row.takeAt(0)
            w = it.widget()
            if w:
                dur_frame_lay.addWidget(w)
            else:
                dur_frame_lay.addStretch()
        lay.addWidget(dur_frame)

        # Queue preview
        self.queue_row_label = QLabel("QUEUE")
        self.queue_row_label.setObjectName("subLabel")
        lay.addWidget(self.queue_row_label)

        self.queue_frame = QFrame()
        self.queue_frame.setObjectName("card")
        self.queue_lay = QHBoxLayout(self.queue_frame)
        self.queue_lay.setContentsMargins(10, 10, 10, 10)
        self.queue_lay.setSpacing(6)
        self.queue_empty = QLabel("—")
        self.queue_empty.setStyleSheet(f"color: {COLORS['text_faint']}; font-size: 11px;")
        self.queue_lay.addWidget(self.queue_empty)
        self.queue_lay.addStretch()
        lay.addWidget(self.queue_frame)

        lay.addStretch()

        add_btn = QPushButton("+ Add to Queue")
        add_btn.setObjectName("primary")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._add_to_queue)
        lay.addWidget(add_btn)

        apply_shadow(panel, blur=22, alpha=70, dy=6)
        self._mode = "trophies"
        return panel

    def _sub_label(self, text):
        l = QLabel(text)
        l.setObjectName("subLabel")
        return l

    def _sub_label_row(self, left, right):
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        l = QLabel(left); l.setObjectName("subLabel")
        r = QLabel(right); r.setStyleSheet(f"color: {COLORS['text_faint']}; font-size: 10px;")
        row.addWidget(l); row.addStretch(); row.addWidget(r)
        return w

    def _on_emu_change(self, text):
        token = text.split("·")[-1].strip() if "·" in text else text
        gc = load_toml_as_dict("cfg/general_config.toml")
        gc["current_emulator"] = token
        save_dict_as_toml(gc, "cfg/general_config.toml")

    def _set_mode(self, mode):
        self._mode = mode
        self.trophies_btn.setChecked(mode == "trophies")
        self.wins_btn.setChecked(mode == "wins")
        for b, on in [(self.trophies_btn, mode == "trophies"), (self.wins_btn, mode == "wins")]:
            b.setProperty("active", "true" if on else "false")
            b.style().unpolish(b); b.style().polish(b)
        self.cur_label.setText("CURRENT TROPHIES" if mode == "trophies" else "CURRENT WINS")

    def _populate_config(self, brawler):
        self.sel_name.setText(display_name(brawler))
        from gui.qt.meta import role_of
        self.sel_sub.setText(f"{rarity_label(rarity_of(brawler)).upper()} · {role_of(brawler)}")
        c1, c2 = gradient_for(brawler)
        icon_path = f"./api/assets/brawler_icons/{brawler}.png"
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path).scaled(52, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.sel_icon.setPixmap(pix)
            self.sel_icon.setStyleSheet(
                f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {c1},stop:1 {c2}); border-radius: 10px;")
        else:
            self.sel_icon.setPixmap(QPixmap())
            self.sel_icon.setText(short_code(brawler))
            self.sel_icon.setStyleSheet(
                f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {c1},stop:1 {c2});"
                f" border-radius: 10px; color: white; font-weight: 800; font-size: 16px;")
        s = self.state.get(brawler, {})
        self.target_input.setText(str(s.get("push_until", 1200)))
        self.cur_input.setText(str(s.get("trophies", 0) if s.get("type", "trophies") == "trophies" else s.get("wins", 0)))
        self.streak_input.setText(str(s.get("win_streak", 0)))
        self.auto_cb.setChecked(bool(s.get("automatically_pick", True)))
        self._set_mode(s.get("type", "trophies"))

    def _add_to_queue(self):
        if not self.selected:
            return
        try:
            target = int(self.target_input.text() or "0")
            current = int(self.cur_input.text() or "0")
            streak = int(self.streak_input.text() or "0")
        except ValueError:
            return
        entry = {
            "brawler": self.selected,
            "push_until": target,
            "trophies": current if self._mode == "trophies" else 0,
            "wins": current if self._mode == "wins" else 0,
            "type": self._mode,
            "automatically_pick": self.auto_cb.isChecked(),
            "win_streak": streak,
        }
        self.state[self.selected] = entry
        # save run_for_minutes
        try:
            mins = int(self.dur_input.text() or "60")
            gc = load_toml_as_dict("cfg/general_config.toml")
            gc["run_for_minutes"] = mins
            save_dict_as_toml(gc, "cfg/general_config.toml")
        except ValueError:
            pass

        if self.selected not in self.queue:
            self.queue.append(self.selected)
        self._persist_queue()
        self._refresh_queue_row()
        self._cards[self.selected].set_queued(True)
        self.queue_changed.emit(len(self.queue))

    def _remove_from_queue(self, brawler: str):
        if brawler in self.queue:
            self.queue.remove(brawler)
        self._persist_queue()
        self._refresh_queue_row()
        if brawler in self._cards:
            self._cards[brawler].set_queued(False)
        self.queue_changed.emit(len(self.queue))

    def _persist_queue(self):
        data = {"__queue__": self.queue, **self.state}
        _save_fighters_state(data)

    def _refresh_queue_row(self):
        while self.queue_lay.count():
            it = self.queue_lay.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)
        if not self.queue:
            self.queue_lay.addWidget(self.queue_empty)
            self.queue_empty.setParent(self.queue_frame)
            self.queue_empty.show()
        else:
            for b in self.queue:
                chip = QueueChip(b)
                chip.remove_requested.connect(self._remove_from_queue)
                chip.edit_requested.connect(self._edit_queued)
                chip.reorder_requested.connect(self._reorder_queue)
                self.queue_lay.addWidget(chip)
        self.queue_lay.addStretch()

    def _edit_queued(self, brawler: str):
        """Click a queue chip to load that brawler into the config panel."""
        if brawler not in self._cards:
            return
        self._select_fighter(brawler)
        self.scroll.ensureWidgetVisible(self._cards[brawler])

    def _reorder_queue(self, src: str, target: str):
        if src not in self.queue or target not in self.queue:
            return
        self.queue.remove(src)
        target_idx = self.queue.index(target)
        self.queue.insert(target_idx, src)
        self._persist_queue()
        self._refresh_queue_row()

    def build_brawler_data(self):
        """Return the final list of brawler configs for pyla_main."""
        if not self.queue and self.selected:
            self._add_to_queue()
        return [self.state[b] for b in self.queue if b in self.state]
