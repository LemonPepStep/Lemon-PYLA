import os
from PySide6.QtCore import Qt, QSize, Signal, QRectF
from PySide6.QtGui import (QPixmap, QPainter, QColor, QBrush, QLinearGradient,
                           QPainterPath, QFont, QPen, QIcon)
from PySide6.QtWidgets import (QFrame, QLabel, QVBoxLayout, QHBoxLayout,
                               QGraphicsDropShadowEffect, QWidget, QPushButton,
                               QSizePolicy)

from gui.qt.theme import COLORS, RARITY_COLORS, gradient_for
from gui.qt.meta import rarity_of, short_code, display_name


def apply_shadow(widget, blur=24, alpha=90, dy=6):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, dy)
    effect.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(effect)


class RarityBadge(QLabel):
    def __init__(self, rarity: str, parent=None):
        super().__init__(rarity, parent)
        c1, c2 = RARITY_COLORS.get(rarity, RARITY_COLORS["RARE"])
        self.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {c1}, stop:1 {c2});"
            f"color: white; border-radius: 6px; padding: 2px 6px;"
            f"font-size: 9px; font-weight: 800; letter-spacing: 1px;"
        )
        self.setFixedHeight(16)


class FighterTile(QFrame):
    """A colored gradient tile with the brawler's short-code, icon overlay, and a rarity badge."""
    clicked = Signal(str)

    def __init__(self, brawler: str, icon_path: str | None = None, size: int = 112, parent=None):
        super().__init__(parent)
        self.brawler = brawler
        self.rarity = rarity_of(brawler)
        self._size = size
        self._selected = False
        self._queued = False
        self.icon_pix = None
        if icon_path and os.path.exists(icon_path):
            pix = QPixmap(icon_path)
            if not pix.isNull():
                self.icon_pix = pix
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)

    def set_selected(self, selected: bool):
        self._selected = selected
        self.update()

    def set_queued(self, queued: bool):
        self._queued = queued
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.brawler)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(0, 0, self._size, self._size)
        path = QPainterPath()
        path.addRoundedRect(rect, 16, 16)

        c1_hex, c2_hex = gradient_for(self.brawler)
        grad = QLinearGradient(0, 0, self._size, self._size)
        grad.setColorAt(0, QColor(c1_hex))
        grad.setColorAt(1, QColor(c2_hex))
        p.fillPath(path, QBrush(grad))

        if self.icon_pix:
            scaled = self.icon_pix.scaled(self._size - 16, self._size - 16,
                                          Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (self._size - scaled.width()) / 2
            y = (self._size - scaled.height()) / 2 + 4
            p.setOpacity(0.95)
            p.drawPixmap(int(x), int(y), scaled)
            p.setOpacity(1.0)
        else:
            p.setPen(QColor(255, 255, 255, 230))
            font = QFont("Segoe UI", int(self._size * 0.28), QFont.Black)
            p.setFont(font)
            p.drawText(rect, Qt.AlignCenter, short_code(self.brawler))

        # Rarity badge top-left
        c1, c2 = RARITY_COLORS.get(self.rarity, RARITY_COLORS["RARE"])
        badge_rect = QRectF(8, 8, 34, 16)
        badge_path = QPainterPath()
        badge_path.addRoundedRect(badge_rect, 4, 4)
        bgrad = QLinearGradient(badge_rect.topLeft(), badge_rect.topRight())
        bgrad.setColorAt(0, QColor(c1))
        bgrad.setColorAt(1, QColor(c2))
        p.fillPath(badge_path, QBrush(bgrad))
        p.setPen(QColor("white"))
        p.setFont(QFont("Segoe UI", 7, QFont.Black))
        p.drawText(badge_rect, Qt.AlignCenter, self.rarity)

        # Queued dot
        if self._queued:
            p.setBrush(QColor("#22c55e"))
            p.setPen(Qt.NoPen)
            p.drawEllipse(self._size - 18, 8, 10, 10)

        # Selection border
        if self._selected:
            pen = QPen(QColor("#06b6d4"))
            pen.setWidth(3)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(rect.adjusted(1.5, 1.5, -1.5, -1.5), 15, 15)


class FighterCard(QFrame):
    clicked = Signal(str)

    def __init__(self, brawler: str, trophies: int, icon_path: str | None, parent=None):
        super().__init__(parent)
        self.brawler = brawler
        self.setObjectName("card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(6)

        self.tile = FighterTile(brawler, icon_path, size=112, parent=self)
        self.tile.clicked.connect(self.clicked.emit)
        lay.addWidget(self.tile, alignment=Qt.AlignHCenter)

        name = QLabel(display_name(brawler))
        name.setObjectName("fighterName")
        lay.addWidget(name)

        trow = QHBoxLayout()
        trow.setSpacing(4)
        star = QLabel("🏆")
        star.setStyleSheet("font-size: 12px;")
        tval = QLabel(str(trophies))
        tval.setObjectName("fighterTrophies")
        trow.addWidget(star)
        trow.addWidget(tval)
        trow.addStretch()
        lay.addLayout(trow)

        self.setFixedWidth(132)
        apply_shadow(self, blur=16, alpha=70, dy=4)

    def set_selected(self, s: bool):
        self.tile.set_selected(s)
        self.setProperty("selected", "true" if s else "false")
        self.style().unpolish(self); self.style().polish(self)

    def set_queued(self, q: bool):
        self.tile.set_queued(q)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.brawler)
        super().mousePressEvent(event)


class StatCard(QFrame):
    def __init__(self, label: str, value: str, delta: str | None = None,
                 delta_good: bool = True, accent: bool = False, sub: str | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)
        lbl = QLabel(label.upper())
        lbl.setObjectName("statLabel")
        lay.addWidget(lbl)
        val = QLabel(value)
        val.setObjectName("statValueAccent" if accent else "statValue")
        lay.addWidget(val)
        if delta:
            d = QLabel(delta)
            d.setObjectName("statDelta" if delta_good else "statDeltaBad")
            lay.addWidget(d)
        if sub:
            s = QLabel(sub)
            s.setStyleSheet(f"color: {COLORS['text_faint']}; font-size: 10px;")
            lay.addWidget(s)
        apply_shadow(self, blur=18, alpha=70, dy=4)


class SectionCard(QFrame):
    def __init__(self, title: str, subtitle: str | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(12)
        header = QHBoxLayout()
        header.setSpacing(10)
        icon = QLabel("◆")
        icon.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #8b5cf6,stop:1 #ec4899);"
            f"border-radius: 8px; padding: 4px 8px; color: white; font-size: 12px;")
        header.addWidget(icon)
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        t = QLabel(title)
        t.setObjectName("sectionTitle")
        text_col.addWidget(t)
        if subtitle:
            st = QLabel(subtitle.upper())
            st.setObjectName("subLabel")
            text_col.addWidget(st)
        header.addLayout(text_col)
        header.addStretch()
        outer.addLayout(header)

        self.body = QVBoxLayout()
        self.body.setSpacing(12)
        outer.addLayout(self.body)
        apply_shadow(self, blur=20, alpha=70, dy=4)

    def add_row(self, widget):
        self.body.addWidget(widget)


class FilterChip(QPushButton):
    def __init__(self, label: str, parent=None):
        super().__init__(label, parent)
        self.setObjectName("filterChip")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.toggled.connect(self._on_toggle)

    def _on_toggle(self, checked):
        self.setProperty("active", "true" if checked else "false")
        self.style().unpolish(self); self.style().polish(self)


class NavButton(QPushButton):
    def __init__(self, label: str, icon: str = "•", badge: str | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("navBtn")
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self._label_text = label
        self._icon_text = icon
        # Left padding large enough to clear the active accent bar (3px) + spacing
        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 0, 14, 0)
        lay.setSpacing(12)
        self._ic_lbl = QLabel(icon)
        self._ic_lbl.setStyleSheet("font-size: 17px; background: transparent;")
        self._ic_lbl.setFixedWidth(22)
        self._ic_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._ic_lbl)
        self._txt_lbl = QLabel(label)
        self._txt_lbl.setStyleSheet("background: transparent; font-weight: 600; font-size: 13px; letter-spacing: 0.2px;")
        lay.addWidget(self._txt_lbl)
        lay.addStretch()
        self._badge_label = None
        if badge is not None:
            self._make_badge(badge, lay)
        self.setMinimumHeight(48)
        self.toggled.connect(self._on_toggle)

    def _make_badge(self, text, layout):
        b = QLabel(text)
        b.setObjectName("navBadge")
        layout.addWidget(b)
        self._badge_label = b

    def _on_toggle(self, checked):
        self.setProperty("active", "true" if checked else "false")
        self.style().unpolish(self); self.style().polish(self)
        # Tint icon and text when active
        color = COLORS["accent_2"] if checked else COLORS["text_dim"]
        self._ic_lbl.setStyleSheet(f"font-size: 17px; background: transparent; color: {color};")
        self._txt_lbl.setStyleSheet(
            f"background: transparent; font-weight: {'700' if checked else '600'};"
            f" font-size: 13px; letter-spacing: 0.2px; color: {color if checked else COLORS['text']};"
        )

    def set_badge(self, text: str | None):
        if self._badge_label is None and text:
            self._make_badge(text, self.layout())
            return
        if self._badge_label:
            if text:
                self._badge_label.setText(text)
                self._badge_label.show()
            else:
                self._badge_label.hide()


class TimelineChart(QWidget):
    """Stacked win/loss bar chart — draws 28 bars (4 weeks of session data)."""

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.data = data or self._sample()

    @staticmethod
    def _sample():
        import random
        random.seed(42)
        out = []
        for _ in range(28):
            w = random.randint(6, 22)
            l = random.randint(2, 14)
            out.append((w, l))
        return out

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height() - 28
        n = len(self.data)
        if n == 0:
            return
        max_total = max((a + b) for a, b in self.data) or 1
        pad = 20
        avail = w - pad * 2
        bar_w = avail / n * 0.65
        gap = avail / n * 0.35
        for i, (wins, losses) in enumerate(self.data):
            x = pad + i * (bar_w + gap)
            total = wins + losses
            total_h = h * (total / max_total)
            wh = total_h * (wins / total) if total else 0
            lh = total_h - wh

            rect_w = QRectF(x, h - total_h, bar_w, wh)
            rect_l = QRectF(x, h - lh, bar_w, lh)

            path_w = QPainterPath()
            path_w.addRoundedRect(rect_w, 4, 4)
            p.fillPath(path_w, QColor("#22c55e"))

            path_l = QPainterPath()
            path_l.addRoundedRect(rect_l, 4, 4)
            p.fillPath(path_l, QColor("#ef4444"))

        # Day labels
        p.setPen(QColor(COLORS["text_faint"]))
        p.setFont(QFont("Segoe UI", 9, QFont.Bold))
        days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        for i, d in enumerate(days):
            cx = pad + (i * 4 + 1.5) * (bar_w + gap)
            p.drawText(int(cx - 15), h + 18, 40, 14, Qt.AlignCenter, d)
