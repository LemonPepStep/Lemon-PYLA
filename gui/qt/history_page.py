import os
import time
from collections import defaultdict
from datetime import datetime, timedelta

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QPainterPath
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QFrame, QScrollArea, QPushButton, QComboBox,
                               QToolTip)

from gui.qt.widgets import StatCard, apply_shadow
from gui.qt.theme import COLORS, RARITY_COLORS, gradient_for
from gui.qt.meta import rarity_of, display_name, short_code, role_of
from gui.qt.match_log import load_entries, filter_range, classify, WIN_RESULTS, LOSS_RESULTS
from gui.qt.sessions import load_sessions, format_duration


RANGES = ["24h", "7d", "30d", "ALL"]


def _fmt_duration(seconds: float | None) -> str:
    if not seconds or seconds <= 0:
        return "—"
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


def _aggregate(entries: list[dict]) -> dict:
    per = defaultdict(lambda: {"wins": 0, "losses": 0, "draws": 0,
                                "delta": 0, "recent": [],
                                "duration_total": 0.0, "duration_count": 0,
                                "last_ts": 0.0})
    total_wins = total_losses = total_draws = 0
    trophies_delta = 0
    durations = []
    for e in entries:
        b = (e.get("brawler") or "").lower()
        if not b:
            continue
        cls = classify(e.get("result", ""))
        p = per[b]
        if cls == "win":
            p["wins"] += 1; total_wins += 1
        elif cls == "loss":
            p["losses"] += 1; total_losses += 1
        else:
            p["draws"] += 1; total_draws += 1
        d = e.get("delta")
        if isinstance(d, (int, float)):
            p["delta"] += d
            trophies_delta += d
        dur = e.get("duration_s")
        if isinstance(dur, (int, float)) and dur > 0:
            p["duration_total"] += dur
            p["duration_count"] += 1
            durations.append(dur)
        p["recent"].append(cls)
        ts = e.get("ts", 0) or 0
        if ts > p["last_ts"]:
            p["last_ts"] = ts
    # Best streak across all entries (chronological)
    best_streak = _longest_win_streak(entries)
    # Best streak brawler + date
    best_streak_brawler, best_streak_end_ts = _longest_win_streak_owner(entries)
    avg_dur = sum(durations) / len(durations) if durations else 0
    return {
        "per": per,
        "total_wins": total_wins,
        "total_losses": total_losses,
        "total_draws": total_draws,
        "trophies_delta": trophies_delta,
        "best_streak": best_streak,
        "best_streak_brawler": best_streak_brawler,
        "best_streak_end_ts": best_streak_end_ts,
        "avg_duration": avg_dur,
        "count": len(entries),
    }


def _longest_win_streak(entries):
    best = cur = 0
    for e in sorted(entries, key=lambda x: x.get("ts", 0)):
        if classify(e.get("result", "")) == "win":
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 0
    return best


def _longest_win_streak_owner(entries):
    """Return (brawler, end_ts) of the best per-brawler consecutive win run."""
    per_streak = defaultdict(int)
    best_n = 0
    best_b = None
    best_ts = 0.0
    sorted_entries = sorted(entries, key=lambda x: x.get("ts", 0))
    for e in sorted_entries:
        b = (e.get("brawler") or "").lower()
        if not b:
            continue
        if classify(e.get("result", "")) == "win":
            per_streak[b] += 1
            if per_streak[b] > best_n:
                best_n = per_streak[b]
                best_b = b
                best_ts = e.get("ts", 0)
        else:
            per_streak[b] = 0
    return best_b, best_ts


class DailyTimeline(QWidget):
    """Stacked win/loss bars, one per day, for the given date range."""

    BOTTOM_LABEL_AREA = 44

    def __init__(self, entries: list[dict], days: int = 7, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(240)
        self.setMouseTracking(True)
        self.days = days
        self.entries = entries
        self._bar_rects: list[tuple] = []  # list of (x, y, w, h, bucket)
        self._buckets = self._build_buckets()

    def _build_buckets(self):
        n = max(1, self.days)
        now = datetime.now()
        start = (now - timedelta(days=n - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
        buckets = [{"w": 0, "l": 0, "d": 0, "date": start + timedelta(days=i)} for i in range(n)]
        for e in self.entries:
            ts = e.get("ts")
            if not isinstance(ts, (int, float)):
                continue
            dt = datetime.fromtimestamp(ts)
            idx = (dt - start).days
            if 0 <= idx < n:
                cls = classify(e.get("result", ""))
                if cls == "win": buckets[idx]["w"] += 1
                elif cls == "loss": buckets[idx]["l"] += 1
                else: buckets[idx]["d"] += 1
        return buckets

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height() - self.BOTTOM_LABEL_AREA
        pad = 20
        n = max(1, self.days)
        avail = w - pad * 2
        bar_w = max(4, avail / n * 0.65)
        gap = avail / n - bar_w

        buckets = self._buckets
        self._bar_rects = []

        max_total = max((b["w"] + b["l"] + b["d"]) for b in buckets) or 1

        for i, bk in enumerate(buckets):
            x = pad + i * (bar_w + gap)
            total = bk["w"] + bk["l"] + bk["d"]
            # Record hover area across full column (entire bar zone) so tooltip works on empty days too
            self._bar_rects.append((x, 0, bar_w, h, bk))
            if total == 0:
                # faint base tick
                p.fillRect(int(x), h - 2, int(bar_w), 2, QColor(COLORS["border"]))
                continue
            total_h = h * (total / max_total)
            wh = total_h * (bk["w"] / total)
            lh = total_h * (bk["l"] / total)
            dh = total_h - wh - lh

            # Win (bottom)
            rect_w = (x, h - total_h, bar_w, wh)
            # Loss (middle)
            rect_l = (x, h - total_h + wh, bar_w, lh)
            # Draw (top) - accent color
            rect_d = (x, h - total_h + wh + lh, bar_w, dh)

            for (rx, ry, rw, rh), color in [
                (rect_w, QColor("#22c55e")),
                (rect_l, QColor("#ef4444")),
                (rect_d, QColor(COLORS["accent"])),
            ]:
                if rh <= 0:
                    continue
                path = QPainterPath()
                from PySide6.QtCore import QRectF
                path.addRoundedRect(QRectF(rx, ry, rw, rh), 3, 3)
                p.fillPath(path, color)

        # Labels
        p.setPen(QColor(COLORS["text_faint"]))
        p.setFont(QFont("Segoe UI", 8, QFont.Bold))
        # Pick up to 7 label positions evenly
        step = max(1, n // 7)
        for i in range(0, n, step):
            cx = pad + i * (bar_w + gap) + bar_w / 2
            d = buckets[i]["date"]
            if n <= 7:
                label = d.strftime("%a").upper()
            elif n <= 14:
                label = d.strftime("%d")
            else:
                label = d.strftime("%d %b") if i % max(1, n // 5) == 0 else ""
            if label:
                p.drawText(int(cx - 20), h + 10, 40, 14, Qt.AlignCenter, label)

    def mouseMoveEvent(self, event):
        x = event.position().x() if hasattr(event, "position") else event.x()
        y = event.position().y() if hasattr(event, "position") else event.y()
        for rx, ry, rw, rh, bk in self._bar_rects:
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                w_ = bk["w"]; l_ = bk["l"]; d_ = bk["d"]
                total = w_ + l_ + d_
                wr = int(round(100 * w_ / (w_ + l_))) if (w_ + l_) else 0
                date_str = bk["date"].strftime("%a %b %d")
                if total == 0:
                    text = f"<b>{date_str}</b><br/>No matches"
                else:
                    text = (f"<b>{date_str}</b><br/>"
                            f"{total} matches · {wr}% WR<br/>"
                            f"<span style='color:#22c55e'>{w_}W</span> · "
                            f"<span style='color:#ef4444'>{l_}L</span>"
                            + (f" · {d_}D" if d_ else ""))
                QToolTip.showText(event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos(), text, self)
                return
        QToolTip.hideText()


class PerFighterCard(QFrame):
    def __init__(self, brawler: str, stats: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        wins = stats["wins"]
        losses = stats["losses"]
        draws = stats["draws"]
        total = wins + losses + draws
        played = wins + losses
        wr = round(100 * wins / played, 1) if played else 0.0
        lr = 100 - wr if played else 0.0
        delta = stats["delta"]
        avg_dur = (stats["duration_total"] / stats["duration_count"]) if stats["duration_count"] else 0
        last_ts = stats["last_ts"]
        last_seen = _relative_time(last_ts) if last_ts else "never"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(10)
        icon = QLabel()
        icon.setFixedSize(52, 52)
        icon.setAlignment(Qt.AlignCenter)
        c1, c2 = gradient_for(brawler)
        icon_path = f"./api/assets/brawler_icons/{brawler}.png"
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon.setPixmap(pix)
            icon.setStyleSheet(
                f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {c1},stop:1 {c2}); border-radius: 10px;")
        else:
            icon.setText(short_code(brawler))
            icon.setStyleSheet(
                f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {c1},stop:1 {c2});"
                f"border-radius: 10px; color: white; font-weight: 800; font-size: 16px;")
        top.addWidget(icon)
        meta = QVBoxLayout()
        meta.setSpacing(2)
        rc1, rc2 = RARITY_COLORS.get(rarity_of(brawler), RARITY_COLORS["RARE"])
        rbadge = QLabel(rarity_of(brawler))
        rbadge.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {rc1},stop:1 {rc2});"
            f"color: white; border-radius: 4px; padding: 1px 6px; font-size: 9px; font-weight: 800;")
        rbadge.setFixedHeight(16)
        rbadge.setMaximumWidth(50)
        meta.addWidget(rbadge)
        name = QLabel(display_name(brawler))
        name.setStyleSheet("font-size: 15px; font-weight: 800;")
        meta.addWidget(name)
        role = QLabel(role_of(brawler).upper())
        role.setStyleSheet(f"color: {COLORS['text_faint']}; font-size: 10px; font-weight: 700; letter-spacing: 1.3px;")
        meta.addWidget(role)
        top.addLayout(meta)
        top.addStretch()
        outer.addLayout(top)

        games = QLabel(f"{total} games  ·  {wins}W / {losses}L" + (f" / {draws}D" if draws else ""))
        games.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px; font-weight: 600;")
        outer.addWidget(games)

        stats_row = QHBoxLayout()
        w_pct = QLabel(f"{wr}% WIN")
        w_pct.setStyleSheet(f"color: {COLORS['green']}; font-weight: 800; font-size: 12px;")
        l_pct = QLabel(f"{lr:.1f}% LOSS")
        l_pct.setStyleSheet(f"color: {COLORS['red']}; font-weight: 800; font-size: 12px;")
        stats_row.addWidget(w_pct); stats_row.addStretch(); stats_row.addWidget(l_pct)
        outer.addLayout(stats_row)

        # Gradient progress bar
        bar = QFrame()
        bar.setFixedHeight(6)
        cut = max(0.01, min(0.99, wr / 100)) if played else 0.0
        bar.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 #22c55e, stop:{cut} #22c55e,"
            f"stop:{min(0.999, cut + 0.001)} #ef4444, stop:1 #ef4444);"
            f"border-radius: 3px;")
        outer.addWidget(bar)

        # Last 20 matches (real)
        last_20 = stats["recent"][-20:]
        mini = QHBoxLayout()
        mini.setSpacing(3)
        for cls in last_20:
            sq = QFrame()
            sq.setFixedSize(10, 14)
            color = {"win": COLORS["green"], "loss": COLORS["red"]}.get(cls, COLORS["accent"])
            sq.setStyleSheet(f"background: {color}; border-radius: 2px;")
            mini.addWidget(sq)
        for _ in range(20 - len(last_20)):
            sq = QFrame()
            sq.setFixedSize(10, 14)
            sq.setStyleSheet(f"background: {COLORS['border']}; border-radius: 2px;")
            mini.addWidget(sq)
        mini.addStretch()
        outer.addLayout(mini)

        # Bottom stats
        foot = QHBoxLayout()
        td = QLabel("TROPHY Δ")
        td.setObjectName("subLabel")
        tv = QLabel(f"{delta:+d}" if isinstance(delta, int) else f"{delta:+.0f}")
        tv.setStyleSheet(f"color: {COLORS['green'] if delta >= 0 else COLORS['red']}; font-weight: 800; font-size: 12px;")
        av = QLabel("AVG TIME"); av.setObjectName("subLabel")
        avv = QLabel(_fmt_duration(avg_dur))
        avv.setStyleSheet(f"color: {COLORS['text']}; font-weight: 800; font-size: 12px;")
        ls = QLabel("LAST SEEN"); ls.setObjectName("subLabel")
        lsv = QLabel(last_seen)
        lsv.setStyleSheet(f"color: {COLORS['text']}; font-weight: 700; font-size: 12px;")

        for widgets in ((td, tv), (av, avv), (ls, lsv)):
            col = QVBoxLayout()
            col.setSpacing(2)
            col.addWidget(widgets[0])
            col.addWidget(widgets[1])
            foot.addLayout(col)
            foot.addStretch()
        outer.addLayout(foot)

        apply_shadow(self, blur=18, alpha=70, dy=4)


def _relative_time(ts: float) -> str:
    if not ts:
        return "—"
    diff = time.time() - ts
    if diff < 60:
        return "now"
    if diff < 3600:
        return f"{int(diff // 60)}m"
    if diff < 86400:
        return f"{int(diff // 3600)}h"
    if diff < 86400 * 2:
        return "yest"
    if diff < 86400 * 7:
        return f"{int(diff // 86400)}d"
    return datetime.fromtimestamp(ts).strftime("%d %b")


class HistoryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._range = "7d"
        self._sort = "GAMES"
        self._session_filter = None  # None = all, otherwise (start, end)

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(14)

        # Title row
        self._title_row = QHBoxLayout()
        t1 = QLabel("Match ")
        t1.setObjectName("pageTitle")
        t2 = QLabel("History")
        t2.setObjectName("pageTitleAccent")
        self._title_row.addWidget(t1)
        self._title_row.addWidget(t2)
        self._title_row.addStretch()

        self._range_btns = {}
        range_frame = QFrame()
        range_frame.setObjectName("tabPill")
        rlay = QHBoxLayout(range_frame)
        rlay.setContentsMargins(4, 4, 4, 4)
        rlay.setSpacing(2)
        for r in RANGES:
            b = QPushButton(r)
            b.setObjectName("tabPillBtn")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            if r == self._range:
                b.setChecked(True); b.setProperty("active", "true")
            b.clicked.connect(lambda _, rng=r: self._set_range(rng))
            self._range_btns[r] = b
            rlay.addWidget(b)
        self._title_row.addWidget(range_frame)
        self._root.addLayout(self._title_row)

        # Session filter row
        sess_row = QHBoxLayout()
        sess_lbl = QLabel("SESSION")
        sess_lbl.setObjectName("subLabel")
        sess_row.addWidget(sess_lbl)
        self._session_combo = QComboBox()
        self._session_combo.setStyleSheet(
            f"background: {COLORS['bg_card']}; color: {COLORS['text']};"
            f"border: 1px solid {COLORS['border']}; border-radius: 8px;"
            f"padding: 4px 10px; font-size: 11px; font-weight: 700;"
        )
        self._session_combo.setMinimumWidth(280)
        self._session_combo.currentIndexChanged.connect(self._on_session_changed)
        sess_row.addWidget(self._session_combo)
        sess_row.addStretch()
        self._root.addLayout(sess_row)
        self._populate_sessions()

        # Subtitle
        self._subtitle = QLabel("")
        self._subtitle.setStyleSheet(f"color: {COLORS['text_faint']}; font-size: 11px;")
        self._root.addWidget(self._subtitle)

        # Body container (rebuilt when range changes)
        self._body = QVBoxLayout()
        self._body.setSpacing(14)
        self._root.addLayout(self._body)
        self._root.addStretch()

        self._rebuild()

    def _set_range(self, rng):
        self._range = rng
        for r, b in self._range_btns.items():
            active = r == rng
            b.setChecked(active)
            b.setProperty("active", "true" if active else "false")
            b.style().unpolish(b); b.style().polish(b)
        self._rebuild()

    def _set_sort(self, sort_key):
        self._sort = sort_key
        self._rebuild()

    def _populate_sessions(self):
        self._session_combo.blockSignals(True)
        self._session_combo.clear()
        self._session_combo.addItem("All matches (ignore session)", userData=None)
        sessions = load_sessions()
        for s in reversed(sessions[-20:]):
            try:
                import time as _t
                when = _t.strftime("%b %d · %H:%M", _t.localtime(s.get("start", 0)))
            except Exception:
                when = "?"
            label = (f"{when}  ·  {format_duration(s.get('duration_s', 0))}"
                     f"  ·  {int(s.get('wins', 0))}W/{int(s.get('losses', 0))}L"
                     f"  ·  {s.get('reason', '')}")
            self._session_combo.addItem(label, userData=(s.get("start", 0), s.get("end", 0)))
        self._session_combo.blockSignals(False)

    def _on_session_changed(self, idx: int):
        self._session_filter = self._session_combo.itemData(idx)
        self._rebuild()

    def refresh_sessions(self):
        """Called externally when a new session is logged."""
        self._populate_sessions()

    def _clear_body(self):
        while self._body.count():
            item = self._body.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
            else:
                lay = item.layout()
                if lay:
                    self._clear_layout(lay)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

    def _rebuild(self):
        self._clear_body()

        all_entries = load_entries()
        if self._session_filter:
            s_start, s_end = self._session_filter
            entries = [e for e in all_entries
                       if s_start <= e.get("ts", 0) <= s_end]
        else:
            entries = filter_range(all_entries, self._range)
        agg = _aggregate(entries)

        # Subtitle
        rng_desc = {"24h": "Last 24 hours", "7d": "Last 7 days",
                    "30d": "Last 30 days", "ALL": "All time"}[self._range]
        self._subtitle.setText(
            f"{rng_desc}  ·  {agg['count']} matches recorded"
            + ("  ·  auto-tracked from bot runs" if agg['count'] else "  ·  no matches yet — run the bot to populate")
        )

        # Stat cards row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)

        total = agg["count"]
        prev_entries = self._previous_period_entries(all_entries)
        prev_count = len(prev_entries)
        delta_pct = _delta_pct(total, prev_count)
        stats_row.addWidget(StatCard("Total Matches", str(total),
                                     delta=_fmt_delta_pct(delta_pct, " vs prev period"),
                                     delta_good=(delta_pct is None or delta_pct >= 0)))

        played = agg["total_wins"] + agg["total_losses"]
        wr = round(100 * agg["total_wins"] / played, 1) if played else 0.0
        stats_row.addWidget(StatCard("Win Rate", f"{wr}%", accent=True,
                                     sub=f"{agg['total_wins']}W / {agg['total_losses']}L"
                                         + (f" / {agg['total_draws']}D" if agg['total_draws'] else "")))

        td = agg["trophies_delta"]
        td_str = f"{int(td):+d}" if td == int(td) else f"{td:+.0f}"
        stats_row.addWidget(StatCard("Trophies Gained", td_str,
                                     delta=f"{'▲' if td >= 0 else '▼'} tracked",
                                     delta_good=td >= 0))

        bs_b = agg["best_streak_brawler"]
        bs_when = (datetime.fromtimestamp(agg["best_streak_end_ts"]).strftime("%a %H:%M")
                   if agg["best_streak_end_ts"] else "—")
        stats_row.addWidget(StatCard("Best Streak", f"{agg['best_streak']}W",
                                     sub=f"{display_name(bs_b)} · {bs_when}" if bs_b else "—"))

        avg = _fmt_duration(agg["avg_duration"])
        stats_row.addWidget(StatCard("Avg Match", avg,
                                     delta="—" if avg == "—" else "tracked",
                                     delta_good=True))
        self._body.addLayout(stats_row)

        # Timeline
        tl_card = QFrame()
        tl_card.setObjectName("card")
        tl_lay = QVBoxLayout(tl_card)
        tl_lay.setContentsMargins(18, 16, 18, 16)
        tl_hdr = QHBoxLayout()
        tl_t = QLabel("Session Timeline")
        tl_t.setObjectName("sectionTitle")
        tl_hdr.addWidget(tl_t); tl_hdr.addStretch()
        legend = QHBoxLayout()
        for color, label in [(COLORS["green"], "Win"), (COLORS["red"], "Loss"), (COLORS["accent"], "Draw")]:
            dot = QLabel("●"); dot.setStyleSheet(f"color: {color}; font-size: 12px;")
            txt = QLabel(label); txt.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px;")
            legend.addWidget(dot); legend.addWidget(txt); legend.addSpacing(8)
        tl_hdr.addLayout(legend)
        tl_lay.addLayout(tl_hdr)
        days_for_range = {"24h": 1, "7d": 7, "30d": 30, "ALL": 30}[self._range]
        if self._range == "ALL" and all_entries:
            oldest = min(e.get("ts", time.time()) for e in all_entries)
            days_for_range = max(7, min(90, int((time.time() - oldest) / 86400) + 1))
        tl_lay.addWidget(DailyTimeline(entries, days=days_for_range))
        apply_shadow(tl_card, blur=20, alpha=70, dy=4)
        self._body.addWidget(tl_card)

        # Per-fighter performance
        pf_card = QFrame()
        pf_card.setObjectName("card")
        pf_lay = QVBoxLayout(pf_card)
        pf_lay.setContentsMargins(18, 16, 18, 16)
        hdr = QHBoxLayout()
        t = QLabel("Per-Brawler Performance")
        t.setObjectName("sectionTitle")
        hdr.addWidget(t); hdr.addStretch()
        sort_lbl = QLabel("SORT")
        sort_lbl.setObjectName("subLabel")
        hdr.addWidget(sort_lbl)
        self._sort_btns = {}
        for r in ["GAMES", "WIN RATE", "TROPHIES"]:
            b = QPushButton(r)
            b.setObjectName("tabPillBtn")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            if r == self._sort:
                b.setChecked(True); b.setProperty("active", "true")
            b.clicked.connect(lambda _, rr=r: self._set_sort(rr))
            self._sort_btns[r] = b
            hdr.addWidget(b)
        pf_lay.addLayout(hdr)

        per = agg["per"]
        items = list(per.items())
        if self._sort == "GAMES":
            items.sort(key=lambda kv: -(kv[1]["wins"] + kv[1]["losses"] + kv[1]["draws"]))
        elif self._sort == "WIN RATE":
            def wr_key(kv):
                played = kv[1]["wins"] + kv[1]["losses"]
                return -(kv[1]["wins"] / played if played else 0)
            items.sort(key=wr_key)
        else:
            items.sort(key=lambda kv: -kv[1]["delta"])

        grid = QGridLayout()
        grid.setSpacing(12)
        if not items:
            empty = QLabel("No match history in this range. Run the bot to populate.")
            empty.setStyleSheet(f"color: {COLORS['text_faint']}; font-size: 12px; padding: 24px;")
            grid.addWidget(empty, 0, 0)
        for i, (brawler, stats) in enumerate(items[:9]):
            grid.addWidget(PerFighterCard(brawler, stats), i // 3, i % 3)
        pf_lay.addLayout(grid)
        apply_shadow(pf_card, blur=20, alpha=70, dy=4)
        self._body.addWidget(pf_card)

    def _previous_period_entries(self, all_entries):
        now = time.time()
        windows = {"24h": 86400, "7d": 7 * 86400, "30d": 30 * 86400, "ALL": None}
        span = windows.get(self._range)
        if span is None:
            return []
        prev_start = now - 2 * span
        prev_end = now - span
        return [e for e in all_entries if prev_start <= e.get("ts", 0) < prev_end]


def _delta_pct(cur: int, prev: int):
    if prev == 0:
        return None if cur == 0 else 100.0
    return round(100 * (cur - prev) / prev, 1)


def _fmt_delta_pct(delta, suffix=""):
    if delta is None:
        return "—"
    sign = "▲" if delta >= 0 else "▼"
    return f"{sign} {abs(delta):.1f}%{suffix}"
