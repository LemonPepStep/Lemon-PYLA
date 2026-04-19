from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QFrame, QPushButton, QSlider, QLineEdit,
                               QCheckBox, QSizePolicy)

from gui.qt.widgets import apply_shadow
from gui.qt.theme import COLORS
from utils import load_toml_as_dict, save_dict_as_toml


class SliderRow(QWidget):
    def __init__(self, label, value, lo, hi, step, on_change, fmt="{:.2f}", parent=None):
        super().__init__(parent)
        self._fmt = fmt
        self._lo = lo; self._hi = hi; self._step = step
        self._on_change = on_change

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {COLORS['text']}; font-size: 13px;")
        lbl.setMinimumWidth(200)
        lay.addWidget(lbl)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(int((hi - lo) / step))
        self.slider.setValue(int((value - lo) / step))
        self.slider.valueChanged.connect(self._on_slide)
        lay.addWidget(self.slider, stretch=1)

        self.field = QLineEdit(fmt.format(value))
        self.field.setFixedWidth(72)
        self.field.setAlignment(Qt.AlignCenter)
        self.field.editingFinished.connect(self._on_field)
        lay.addWidget(self.field)

    def _on_slide(self, idx):
        v = self._lo + idx * self._step
        self.field.setText(self._fmt.format(v))
        self._on_change(v)

    def _on_field(self):
        try:
            v = float(self.field.text())
        except ValueError:
            return
        v = max(self._lo, min(self._hi, v))
        self.slider.setValue(int((v - self._lo) / self._step))
        self.field.setText(self._fmt.format(v))
        self._on_change(v)


class SettingsCard(QFrame):
    def __init__(self, icon, title, subtitle, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 18)
        outer.setSpacing(14)

        hdr = QHBoxLayout()
        hdr.setSpacing(10)
        ic = QLabel(icon)
        ic.setFixedSize(32, 32)
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #8b5cf6,stop:1 #ec4899);"
            f"border-radius: 8px; color: white; font-size: 14px; font-weight: 800;")
        hdr.setAlignment(Qt.AlignTop)
        hdr.addWidget(ic, 0, Qt.AlignTop)
        col_w = QWidget()
        col = QVBoxLayout(col_w)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(2)
        t = QLabel(title)
        t.setStyleSheet(f"color: {COLORS['text']}; font-size: 15px; font-weight: 800;")
        t.setFixedHeight(20)
        s = QLabel(subtitle.upper())
        s.setStyleSheet(f"color: {COLORS['text_faint']}; font-size: 9px; font-weight: 700; letter-spacing: 1.5px;")
        s.setFixedHeight(12)
        col.addWidget(t)
        col.addWidget(s)
        col.addStretch()
        hdr.addWidget(col_w, 0, Qt.AlignTop)
        hdr.addStretch()
        outer.addLayout(hdr)

        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        outer.addLayout(self.body)

        apply_shadow(self, blur=20, alpha=70, dy=4)

    def add(self, widget):
        self.body.addWidget(widget)


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bot_cfg_path = "cfg/bot_config.toml"
        self.gen_cfg_path = "cfg/general_config.toml"
        self.time_cfg_path = "cfg/time_tresholds.toml"
        self.bot = load_toml_as_dict(self.bot_cfg_path)
        self.gen = load_toml_as_dict(self.gen_cfg_path)
        self.time = load_toml_as_dict(self.time_cfg_path)

        # Defaults
        self.bot.setdefault("minimum_movement_delay", 0.1)
        self.bot.setdefault("unstuck_movement_delay", 2.0)
        self.bot.setdefault("unstuck_movement_hold_time", 1.0)
        self.bot.setdefault("wall_detection_confidence", 0.9)
        self.bot.setdefault("entity_detection_confidence", 0.6)
        self.bot.setdefault("super_pixels_minimum", 1800)
        self.bot.setdefault("gadget_pixels_minimum", 1300)
        self.bot.setdefault("hypercharge_pixels_minimum", 2000)
        self.gen.setdefault("cpu_or_gpu", "auto")
        self.gen.setdefault("long_press_star_drop", "no")
        self.gen.setdefault("max_ips", "auto")
        self.gen.setdefault("trophies_multiplier", 1)
        # New reliability / quality-of-life defaults
        self.gen.setdefault("auto_restart_on_crash", "yes")
        self.gen.setdefault("auto_reconnect_adb", "yes")
        self.gen.setdefault("stale_frame_timeout_s", 8)
        self.gen.setdefault("notify_on_session_end", "yes")
        self.gen.setdefault("notify_on_crash", "yes")
        self.gen.setdefault("save_debug_screenshots", "no")
        self.gen.setdefault("minimize_to_tray", "no")
        self.gen.setdefault("log_verbosity", "normal")
        self.time.setdefault("super", 0.3)
        self.time.setdefault("gadget", 0.5)
        self.time.setdefault("hypercharge", 0.3)
        self.time.setdefault("wall_detection", 0.2)
        self.time.setdefault("state_check", 5.0)
        self.time.setdefault("no_detection_proceed", 2.0)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        # Title row
        tr = QHBoxLayout()
        t1 = QLabel("Bot ")
        t1.setObjectName("pageTitle")
        t2 = QLabel("Settings")
        t2.setObjectName("pageTitleAccent")
        saved = QLabel("ALL CHANGES SAVED")
        saved.setStyleSheet(
            f"background: {COLORS['bg_card']}; border: 1px solid {COLORS['green']};"
            f"color: {COLORS['green']}; border-radius: 8px; padding: 4px 10px;"
            f"font-size: 10px; font-weight: 800; letter-spacing: 1px;")
        tr.addWidget(t1); tr.addWidget(t2)
        tr.addSpacing(10); tr.addWidget(saved); tr.addStretch()

        # Tabs
        tab_frame = QFrame()
        tab_frame.setObjectName("tabPill")
        tab_lay = QHBoxLayout(tab_frame)
        tab_lay.setContentsMargins(4, 4, 4, 4)
        tab_lay.setSpacing(2)
        self._tabs = {}
        for name in ["Additional Settings", "Timers"]:
            b = QPushButton(name)
            b.setObjectName("tabPillBtn")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            if name == "Additional Settings":
                b.setChecked(True); b.setProperty("active", "true")
            b.clicked.connect(lambda _, btn=b, n=name: self._switch_tab(btn, n))
            self._tabs[name] = b
            tab_lay.addWidget(b)
        tr.addWidget(tab_frame)
        root.addLayout(tr)

        # Pages
        self.additional_widget = self._build_additional()
        self.timers_widget = self._build_timers()
        root.addWidget(self.additional_widget)
        root.addWidget(self.timers_widget)
        self.timers_widget.hide()
        root.addStretch()

    def _switch_tab(self, btn, name):
        for n, b in self._tabs.items():
            on = b is btn
            b.setChecked(on)
            b.setProperty("active", "true" if on else "false")
            b.style().unpolish(b); b.style().polish(b)
        self.additional_widget.setVisible(name == "Additional Settings")
        self.timers_widget.setVisible(name == "Timers")

    def _save_bot(self, key, val):
        self.bot[key] = val
        save_dict_as_toml(self.bot, self.bot_cfg_path)

    def _save_gen(self, key, val):
        self.gen[key] = val
        save_dict_as_toml(self.gen, self.gen_cfg_path)

    def _save_time(self, key, val):
        self.time[key] = val
        save_dict_as_toml(self.time, self.time_cfg_path)

    def _build_additional(self):
        w = QWidget()
        grid = QGridLayout(w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)

        move = SettingsCard("→", "Movement", "Bot motion timing")
        move.add(SliderRow("Minimum Movement Delay", float(self.bot["minimum_movement_delay"]), 0.0, 1.0, 0.01,
                           lambda v: self._save_bot("minimum_movement_delay", round(v, 2))))
        move.add(SliderRow("Unstuck Movement Delay", float(self.bot["unstuck_movement_delay"]), 0.0, 5.0, 0.05,
                           lambda v: self._save_bot("unstuck_movement_delay", round(v, 2))))
        move.add(SliderRow("Unstucking Duration", float(self.bot["unstuck_movement_hold_time"]), 0.0, 3.0, 0.05,
                           lambda v: self._save_bot("unstuck_movement_hold_time", round(v, 2))))

        detect = SettingsCard("◎", "Detection Confidence", "Model thresholds")
        detect.add(SliderRow("Wall Detection Confidence", float(self.bot["wall_detection_confidence"]), 0.0, 1.0, 0.01,
                             lambda v: self._save_bot("wall_detection_confidence", round(v, 2))))
        detect.add(SliderRow("Player / Enemy Confidence", float(self.bot["entity_detection_confidence"]), 0.0, 1.0, 0.01,
                             lambda v: self._save_bot("entity_detection_confidence", round(v, 2))))

        compute = SettingsCard("▦", "Compute", "Runtime & rate")
        compute.add(self._toggle_row("USE GPU", ["cpu", "auto"], self.gen["cpu_or_gpu"],
                                     lambda v: self._save_gen("cpu_or_gpu", v)))
        compute.add(self._checkbox_row("LONGPRESS STAR_DROP",
                                        str(self.gen["long_press_star_drop"]).lower() in ["yes", "true"],
                                        lambda v: self._save_gen("long_press_star_drop", "yes" if v else "no")))
        compute.add(self._max_ips_row())

        pixels = SettingsCard("⚡", "Pixel Thresholds", "Ability detection")
        pixels.add(SliderRow("Super (yellow)", float(self.bot["super_pixels_minimum"]), 0, 5000, 50,
                             lambda v: self._save_bot("super_pixels_minimum", int(v)), fmt="{:.0f}"))
        pixels.add(SliderRow("Gadget (green)", float(self.bot["gadget_pixels_minimum"]), 0, 5000, 50,
                             lambda v: self._save_bot("gadget_pixels_minimum", int(v)), fmt="{:.0f}"))
        pixels.add(SliderRow("Hypercharge (purple)", float(self.bot["hypercharge_pixels_minimum"]), 0, 5000, 50,
                             lambda v: self._save_bot("hypercharge_pixels_minimum", int(v)), fmt="{:.0f}"))

        reliability = SettingsCard("🛡", "Reliability", "Auto-recovery")
        reliability.add(self._checkbox_row("AUTO RESTART ON CRASH",
                                           str(self.gen["auto_restart_on_crash"]).lower() in ["yes", "true"],
                                           lambda v: self._save_gen("auto_restart_on_crash", "yes" if v else "no")))
        reliability.add(self._checkbox_row("AUTO RECONNECT ADB",
                                           str(self.gen["auto_reconnect_adb"]).lower() in ["yes", "true"],
                                           lambda v: self._save_gen("auto_reconnect_adb", "yes" if v else "no")))
        reliability.add(SliderRow("Stale Frame Timeout", float(self.gen["stale_frame_timeout_s"]), 2, 30, 1,
                                  lambda v: self._save_gen("stale_frame_timeout_s", int(v)), fmt="{:.0f}s"))

        notif = SettingsCard("🔔", "Notifications", "Alerts & logging")
        notif.add(self._checkbox_row("NOTIFY ON SESSION END",
                                     str(self.gen["notify_on_session_end"]).lower() in ["yes", "true"],
                                     lambda v: self._save_gen("notify_on_session_end", "yes" if v else "no")))
        notif.add(self._checkbox_row("NOTIFY ON CRASH",
                                     str(self.gen["notify_on_crash"]).lower() in ["yes", "true"],
                                     lambda v: self._save_gen("notify_on_crash", "yes" if v else "no")))
        notif.add(self._checkbox_row("SAVE DEBUG SCREENSHOTS",
                                     str(self.gen["save_debug_screenshots"]).lower() in ["yes", "true"],
                                     lambda v: self._save_gen("save_debug_screenshots", "yes" if v else "no")))
        notif.add(self._checkbox_row("MINIMIZE TO TRAY",
                                     str(self.gen["minimize_to_tray"]).lower() in ["yes", "true"],
                                     lambda v: self._save_gen("minimize_to_tray", "yes" if v else "no")))
        notif.add(self._toggle_row("LOG VERBOSITY", ["quiet", "normal", "debug"],
                                   self.gen["log_verbosity"],
                                   lambda v: self._save_gen("log_verbosity", v)))

        grid.addWidget(move, 0, 0)
        grid.addWidget(detect, 0, 1)
        grid.addWidget(compute, 1, 0)
        grid.addWidget(pixels, 1, 1)
        grid.addWidget(reliability, 2, 0)
        grid.addWidget(notif, 2, 1)
        return w

    def _toggle_row(self, label, options, current, on_change):
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        l = QLabel(label)
        l.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px; font-weight: 700; letter-spacing: 1.3px;")
        lay.addWidget(l)
        lay.addStretch()
        btns = {}
        for opt in options:
            b = QPushButton(opt.upper() if isinstance(opt, str) else str(opt))
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(32)
            b.setFixedWidth(70)
            btns[opt] = b
            lay.addWidget(b)

        def apply_styles(chosen):
            for k, b in btns.items():
                active = k == chosen
                if active:
                    b.setStyleSheet(
                        f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #8b5cf6,stop:1 #a78bfa);"
                        f"color: white; border: none; border-radius: 8px; font-weight: 800; font-size: 11px;")
                else:
                    b.setStyleSheet(
                        f"background: {COLORS['bg_card_hi']}; color: {COLORS['text_dim']};"
                        f"border: 1px solid {COLORS['border']}; border-radius: 8px; font-weight: 700; font-size: 11px;")

        apply_styles(current)
        for opt, b in btns.items():
            def make(o=opt):
                def handler():
                    apply_styles(o)
                    on_change(o)
                return handler
            b.clicked.connect(make())
        return w

    def _checkbox_row(self, label, value, on_change):
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        l = QLabel(label)
        l.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px; font-weight: 700; letter-spacing: 1.3px;")
        lay.addWidget(l)
        lay.addStretch()
        cb = QCheckBox()
        cb.setChecked(value)
        cb.toggled.connect(on_change)
        lay.addWidget(cb)
        return w

    def _max_ips_row(self):
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        l = QLabel("MAX IPS")
        l.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px; font-weight: 700; letter-spacing: 1.3px;")
        lay.addWidget(l)
        lay.addStretch()
        field = QLineEdit(str(self.gen.get("max_ips", "auto")))
        field.setFixedWidth(80)
        field.setAlignment(Qt.AlignCenter)

        def on_done():
            val = field.text().strip()
            if val.lower() == "auto":
                self._save_gen("max_ips", "auto")
            else:
                try:
                    self._save_gen("max_ips", int(val))
                except ValueError:
                    field.setText(str(self.gen.get("max_ips", "auto")))

        field.editingFinished.connect(on_done)
        lay.addWidget(field)
        unit = QLabel("fps")
        unit.setStyleSheet(f"color: {COLORS['text_faint']}; font-size: 11px;")
        lay.addWidget(unit)
        return w

    def _build_timers(self):
        w = QWidget()
        grid = QGridLayout(w)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)

        abilities = SettingsCard("⏱", "Ability Check Rates", "How often to poll state")
        abilities.add(SliderRow("Super Delay", float(self.time["super"]), 0.05, 5.0, 0.05,
                                lambda v: self._save_time("super", round(v, 2))))
        abilities.add(SliderRow("Gadget Delay", float(self.time["gadget"]), 0.05, 5.0, 0.05,
                                lambda v: self._save_time("gadget", round(v, 2))))
        abilities.add(SliderRow("Hypercharge Delay", float(self.time["hypercharge"]), 0.05, 5.0, 0.05,
                                lambda v: self._save_time("hypercharge", round(v, 2))))

        environment = SettingsCard("⌖", "Environment", "World detection cadence")
        environment.add(SliderRow("Wall Detection", float(self.time["wall_detection"]), 0.05, 5.0, 0.05,
                                  lambda v: self._save_time("wall_detection", round(v, 2))))
        environment.add(SliderRow("State Check", float(self.time["state_check"]), 0.5, 30.0, 0.5,
                                  lambda v: self._save_time("state_check", round(v, 2))))
        environment.add(SliderRow("No-Detection Proceed", float(self.time["no_detection_proceed"]), 0.5, 30.0, 0.5,
                                  lambda v: self._save_time("no_detection_proceed", round(v, 2))))

        grid.addWidget(abilities, 0, 0)
        grid.addWidget(environment, 0, 1)
        return w
