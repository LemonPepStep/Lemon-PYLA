COLORS = {
    "bg": "#0f1020",
    "bg_panel": "#161832",
    "bg_card": "#1b1e3d",
    "bg_card_hi": "#232748",
    "border": "#2a2f55",
    "border_hi": "#3a4075",
    "text": "#e6e8ff",
    "text_dim": "#9aa0c7",
    "text_faint": "#6b6f99",
    "accent": "#8b5cf6",
    "accent_hi": "#a78bfa",
    "accent_2": "#f59e0b",
    "green": "#22c55e",
    "red": "#ef4444",
    "pink": "#ec4899",
    "cyan": "#06b6d4",
    "blue": "#3b82f6",
    "yellow": "#fbbf24",
    "legendary": "#22c55e",
    "epic": "#a855f7",
    "rare": "#3b82f6",
    "common": "#94a3b8",
}

RARITY_COLORS = {
    "ULEG":  ("#ec4899", "#f43f5e"),
    "LEG":   ("#ca8a04", "#facc15"),
    "MYTH":  ("#b91c1c", "#ef4444"),
    "EPIC":  ("#7c3aed", "#a855f7"),
    "SR":    ("#0891b2", "#22d3ee"),
    "RARE":  ("#2563eb", "#3b82f6"),
    "COM":   ("#475569", "#64748b"),
}

CARD_GRADIENTS = [
    ("#7c3aed", "#ec4899"),
    ("#f97316", "#ef4444"),
    ("#f59e0b", "#f97316"),
    ("#06b6d4", "#3b82f6"),
    ("#4338ca", "#6366f1"),
    ("#059669", "#22c55e"),
    ("#3b82f6", "#6366f1"),
    ("#f97316", "#f59e0b"),
    ("#9a3412", "#b91c1c"),
    ("#b45309", "#d97706"),
    ("#9f1239", "#be123c"),
    ("#0ea5e9", "#22d3ee"),
    ("#dc2626", "#f97316"),
    ("#6d28d9", "#a855f7"),
    ("#15803d", "#22c55e"),
    ("#1d4ed8", "#2563eb"),
    ("#c2410c", "#f59e0b"),
    ("#be185d", "#ec4899"),
    ("#0d9488", "#14b8a6"),
    ("#7e22ce", "#c026d3"),
]

def gradient_for(name: str):
    h = 0
    for ch in name:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return CARD_GRADIENTS[h % len(CARD_GRADIENTS)]


QSS = f"""
* {{
    font-family: 'Segoe UI', 'Inter', sans-serif;
    color: {COLORS['text']};
}}

QWidget#root {{
    background: {COLORS['bg']};
}}

QWidget#sidebar {{
    background: {COLORS['bg_panel']};
    border-right: 1px solid {COLORS['border']};
}}

QLabel#logo {{
    color: {COLORS['text']};
    font-size: 22px;
    font-weight: 800;
    letter-spacing: 0.5px;
}}
QLabel#logoSub {{
    color: {COLORS['text_faint']};
    font-size: 10px;
    letter-spacing: 2px;
}}
QLabel#logoBadge {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f59e0b, stop:1 #ec4899);
    border-radius: 10px;
    color: white;
    font-size: 18px;
    font-weight: 800;
    padding: 6px;
}}

QPushButton#navBtn {{
    background: transparent;
    color: {COLORS['text_dim']};
    text-align: left;
    padding: 0px 0px;
    border: none;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton#navBtn:hover {{
    background: rgba(255,255,255,0.04);
    color: {COLORS['text']};
}}
QPushButton#navBtn[active="true"] {{
    background: rgba(245, 158, 11, 0.08);
    color: {COLORS['text']};
    border-left: 3px solid {COLORS['accent_2']};
    border-radius: 0px;
    border-top-right-radius: 10px;
    border-bottom-right-radius: 10px;
}}
QLabel#navBadge {{
    background: {COLORS['pink']};
    color: white;
    border-radius: 10px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: 800;
}}

QFrame#statusBox {{
    background: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
}}
QLabel#statusKey {{
    color: {COLORS['text_faint']};
    font-size: 10px;
    letter-spacing: 1.5px;
    font-weight: 700;
}}
QLabel#statusVal {{
    color: {COLORS['text']};
    font-size: 12px;
    font-weight: 700;
}}
QLabel#statusDot {{
    color: {COLORS['green']};
    font-size: 14px;
}}

QPushButton#startBot {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #22c55e, stop:1 #10b981);
    color: white;
    border: none;
    border-radius: 14px;
    padding: 14px;
    font-size: 16px;
    font-weight: 800;
    letter-spacing: 1px;
}}
QPushButton#startBot:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #16a34a, stop:1 #059669);
}}
QPushButton#startBot[stopping="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ef4444, stop:1 #b91c1c);
}}
QPushButton#startBot[stopping="true"]:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #dc2626, stop:1 #991b1b);
}}

QLabel#pageTitle {{
    font-size: 28px;
    font-weight: 800;
}}
QLabel#pageTitleAccent {{
    font-size: 28px;
    font-weight: 800;
    color: {COLORS['accent_2']};
}}
QLabel#countPill {{
    background: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
    padding: 4px 10px;
    color: {COLORS['text_dim']};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}}

QLineEdit#search {{
    background: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    padding: 10px 14px 10px 36px;
    color: {COLORS['text']};
    font-size: 13px;
}}
QLineEdit#search:focus {{
    border: 1px solid {COLORS['accent']};
}}

QPushButton#filterChip {{
    background: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    padding: 6px 14px;
    color: {COLORS['text_dim']};
    font-size: 12px;
    font-weight: 700;
}}
QPushButton#filterChip:hover {{
    background: {COLORS['bg_card_hi']};
    color: {COLORS['text']};
}}
QPushButton#filterChip[active="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8b5cf6, stop:1 #7c3aed);
    color: white;
    border: 1px solid {COLORS['accent_hi']};
}}

QFrame#panel {{
    background: {COLORS['bg_panel']};
    border: 1px solid {COLORS['border']};
    border-radius: 16px;
}}
QFrame#card {{
    background: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 14px;
}}
QFrame#card[selected="true"] {{
    border: 2px solid {COLORS['cyan']};
}}

QLabel#fighterName {{
    color: {COLORS['text']};
    font-size: 13px;
    font-weight: 700;
}}
QLabel#fighterTrophies {{
    color: {COLORS['yellow']};
    font-size: 11px;
    font-weight: 700;
}}

QLabel#sectionTitle {{
    color: {COLORS['text']};
    font-size: 16px;
    font-weight: 800;
}}
QLabel#subLabel {{
    color: {COLORS['text_faint']};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
}}

QComboBox {{
    background: {COLORS['bg_card_hi']};
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
    padding: 8px 12px;
    color: {COLORS['text']};
    font-size: 13px;
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {COLORS['bg_panel']};
    color: {COLORS['text']};
    selection-background-color: {COLORS['accent']};
    border: 1px solid {COLORS['border']};
}}

QLineEdit, QSpinBox {{
    background: {COLORS['bg_card_hi']};
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
    padding: 8px 12px;
    color: {COLORS['text']};
    font-size: 13px;
}}
QLineEdit:focus, QSpinBox:focus {{
    border: 1px solid {COLORS['accent']};
}}

QPushButton#toggleLeft, QPushButton#toggleRight {{
    background: {COLORS['bg_card_hi']};
    border: 1px solid {COLORS['border']};
    color: {COLORS['text_dim']};
    padding: 10px 16px;
    font-weight: 700;
    font-size: 13px;
}}
QPushButton#toggleLeft {{ border-top-left-radius: 10px; border-bottom-left-radius: 10px; }}
QPushButton#toggleRight {{ border-top-right-radius: 10px; border-bottom-right-radius: 10px; }}
QPushButton#toggleLeft[active="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f59e0b, stop:1 #f97316);
    color: white;
    border: 1px solid #f59e0b;
}}
QPushButton#toggleRight[active="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8b5cf6, stop:1 #7c3aed);
    color: white;
    border: 1px solid {COLORS['accent']};
}}

QPushButton#primary {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8b5cf6, stop:1 #ec4899);
    color: white;
    border: none;
    border-radius: 12px;
    padding: 12px 18px;
    font-weight: 800;
    font-size: 13px;
}}
QPushButton#primary:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c3aed, stop:1 #db2777);
}}

QCheckBox {{ color: {COLORS['text']}; font-size: 12px; spacing: 8px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border-radius: 5px;
    border: 1px solid {COLORS['border_hi']};
    background: {COLORS['bg_card_hi']};
}}
QCheckBox::indicator:checked {{
    background: {COLORS['accent']};
    border: 1px solid {COLORS['accent_hi']};
    image: none;
}}

QSlider::groove:horizontal {{
    height: 6px;
    background: {COLORS['bg_card_hi']};
    border-radius: 3px;
}}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8b5cf6, stop:1 #a78bfa);
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: white;
    width: 16px;
    margin: -6px 0;
    border-radius: 8px;
    border: 2px solid {COLORS['accent']};
}}

QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {COLORS['border_hi']}; border-radius: 5px; min-height: 20px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; }}
QScrollBar::handle:horizontal {{ background: {COLORS['border_hi']}; border-radius: 5px; min-width: 20px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

QLabel#statValue {{ font-size: 26px; font-weight: 800; color: {COLORS['text']}; }}
QLabel#statValueAccent {{ font-size: 26px; font-weight: 800; color: {COLORS['accent_2']}; }}
QLabel#statLabel {{ color: {COLORS['text_faint']}; font-size: 10px; font-weight: 700; letter-spacing: 1.5px; }}
QLabel#statDelta {{ color: {COLORS['green']}; font-size: 11px; font-weight: 700; }}
QLabel#statDeltaBad {{ color: {COLORS['red']}; font-size: 11px; font-weight: 700; }}

QFrame#tabPill {{
    background: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
}}
QPushButton#tabPillBtn {{
    background: transparent;
    border: none;
    padding: 6px 14px;
    color: {COLORS['text_dim']};
    font-weight: 700;
    font-size: 12px;
    border-radius: 8px;
}}
QPushButton#tabPillBtn[active="true"] {{
    background: {COLORS['accent']};
    color: white;
}}
"""
