"""
Centralized design system for Library of Yore.

Keeping every color, radius, and stylesheet fragment in one place means the
main window, dialogs, wizard, and cards all stay visually consistent, and a
future re-theme only touches this file.
"""

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
# A warm, "reading lamp at night" dark theme: near-black slate surfaces with
# a soft antique-gold accent instead of the flatter #121212 / pure-gold combo
# the app started with.

BG_BASE = "#12141a"          # window background
BG_SUNKEN = "#0c0e12"        # recessed areas (scroll viewport, inputs on dark)
BG_SURFACE = "#1a1d24"       # cards, group boxes, panels
BG_SURFACE_2 = "#20242c"     # inputs, buttons, hovered rows
BG_SURFACE_3 = "#2a2f39"     # hovered buttons / raised elements

BORDER = "#2c313b"
BORDER_STRONG = "#3d4350"

TEXT_PRIMARY = "#eef0f3"
TEXT_SECONDARY = "#a8afbb"
TEXT_MUTED = "#6b7280"

ACCENT = "#d8b04a"           # antique gold, brand color
ACCENT_HOVER = "#e5c162"
ACCENT_PRESSED = "#b8942f"
ACCENT_TEXT_ON = "#181205"   # text drawn on top of accent-filled buttons

INFO = "#5aa9e6"             # ongoing
SUCCESS = "#5fb87a"
WARNING = "#e8a33d"          # hiatus
DANGER = "#e2564f"           # dropped
PURPLE = "#a687e0"           # planned

RADIUS = 8
RADIUS_SM = 6
RADIUS_LG = 12

FONT_FAMILY = "Segoe UI, Inter, -apple-system, sans-serif"

STATUS_COLORS = {
    "ongoing": INFO,
    "completed": ACCENT,
    "hiatus": WARNING,
    "dropped": DANGER,
    "planned": PURPLE,
}


def status_color(status: str) -> str:
    return STATUS_COLORS.get(status, TEXT_MUTED)


def status_badge_style(status: str) -> str:
    color = status_color(status)
    return f"""
        background-color: {color}26;
        color: {color};
        border: 1px solid {color}55;
        border-radius: {RADIUS_SM}px;
        padding: 3px 8px;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 0.4px;
    """


# ---------------------------------------------------------------------------
# Shared style fragments
# ---------------------------------------------------------------------------

_SCROLLBAR = f"""
    QScrollBar:vertical {{
        background: transparent;
        width: 12px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER_STRONG};
        border-radius: 5px;
        min-height: 32px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {TEXT_MUTED}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 12px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal {{
        background: {BORDER_STRONG};
        border-radius: 5px;
        min-width: 32px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {TEXT_MUTED}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
"""

_INPUTS = f"""
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background-color: {BG_SUNKEN};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        border-radius: {RADIUS_SM}px;
        padding: 7px 10px;
        selection-background-color: {ACCENT}55;
    }}
    QLineEdit:hover, QTextEdit:hover, QComboBox:hover {{ border: 1px solid {BORDER_STRONG}; }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
    QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
        border: 1px solid {ACCENT};
    }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox QAbstractItemView {{
        background-color: {BG_SURFACE_2};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_STRONG};
        selection-background-color: {ACCENT}33;
        outline: none;
    }}
"""

_BUTTONS = f"""
    QPushButton {{
        background-color: {BG_SURFACE_2};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_STRONG};
        border-radius: {RADIUS_SM}px;
        padding: 7px 14px;
        font-size: 12px;
        font-weight: 500;
    }}
    QPushButton:hover {{ background-color: {BG_SURFACE_3}; border-color: {TEXT_MUTED}; }}
    QPushButton:pressed {{ background-color: {BG_SURFACE}; }}
    QPushButton:disabled {{ color: {TEXT_MUTED}; background-color: {BG_SURFACE}; border-color: {BORDER}; }}
    QPushButton:checkable:checked {{ background-color: {ACCENT}22; border-color: {ACCENT}; color: {ACCENT}; }}

    QPushButton#primaryButton, QPushButton#saveButton {{
        background-color: {ACCENT};
        color: {ACCENT_TEXT_ON};
        border: none;
        font-weight: 700;
    }}
    QPushButton#primaryButton:hover, QPushButton#saveButton:hover {{ background-color: {ACCENT_HOVER}; }}
    QPushButton#primaryButton:pressed, QPushButton#saveButton:pressed {{ background-color: {ACCENT_PRESSED}; }}

    QPushButton#dangerButton {{ color: {DANGER}; }}
    QPushButton#dangerButton:hover {{ background-color: {DANGER}22; border-color: {DANGER}; }}
"""

_GROUPBOX = f"""
    QGroupBox {{
        background-color: {BG_SURFACE};
        color: {ACCENT};
        font-weight: 600;
        font-size: 12px;
        border: 1px solid {BORDER};
        border-radius: {RADIUS}px;
        margin-top: 14px;
        padding-top: 14px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
    }}
"""

_MISC = f"""
    QLabel {{ color: {TEXT_SECONDARY}; background: transparent; }}
    QCheckBox {{ color: {TEXT_SECONDARY}; spacing: 8px; }}
    QCheckBox::indicator {{
        width: 15px; height: 15px;
        border: 1px solid {BORDER_STRONG};
        border-radius: 4px;
        background: {BG_SUNKEN};
    }}
    QCheckBox::indicator:hover {{ border: 1px solid {ACCENT}88; }}
    QCheckBox::indicator:checked {{
        background: {ACCENT};
        border: 1px solid {ACCENT};
        image: none;
    }}
    QToolTip {{
        background-color: {BG_SURFACE_2};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_STRONG};
        padding: 4px 8px;
        border-radius: {RADIUS_SM}px;
    }}
    QProgressBar {{
        border: none;
        border-radius: {RADIUS_SM}px;
        background-color: {BG_SUNKEN};
        text-align: center;
        color: {TEXT_PRIMARY};
        font-size: 10px;
        font-weight: 600;
    }}
    QProgressBar::chunk {{
        background-color: {ACCENT};
        border-radius: {RADIUS_SM}px;
    }}
"""


def base_stylesheet() -> str:
    """Shared foundation used by both the main window and dialogs."""
    return f"""
        * {{ font-family: {FONT_FAMILY}; }}
        {_INPUTS}
        {_BUTTONS}
        {_GROUPBOX}
        {_MISC}
        {_SCROLLBAR}
    """


def main_window_stylesheet() -> str:
    return f"""
        QMainWindow {{ background-color: {BG_BASE}; }}
        QWidget {{ background-color: {BG_BASE}; color: {TEXT_PRIMARY}; }}
        {base_stylesheet()}
        #sidebar {{
            background-color: {BG_SURFACE};
            border-right: 1px solid {BORDER};
        }}
        #sidebarBrand {{
            color: {ACCENT};
            font-size: 15px;
            font-weight: 700;
        }}
        #statsLabel {{ color: {TEXT_MUTED}; font-size: 11px; }}
        #topBar {{ background-color: transparent; }}
        #emptyState {{ color: {TEXT_MUTED}; font-size: 15px; }}
        QMenuBar {{ background-color: {BG_SURFACE}; color: {TEXT_SECONDARY}; border-bottom: 1px solid {BORDER}; padding: 2px; }}
        QMenuBar::item {{ padding: 6px 10px; border-radius: {RADIUS_SM}px; }}
        QMenuBar::item:selected {{ background-color: {BG_SURFACE_2}; color: {TEXT_PRIMARY}; }}
        QMenu {{ background-color: {BG_SURFACE_2}; color: {TEXT_PRIMARY}; border: 1px solid {BORDER_STRONG}; border-radius: {RADIUS_SM}px; padding: 4px; }}
        QMenu::item {{ padding: 6px 20px; border-radius: {RADIUS_SM}px; }}
        QMenu::item:selected {{ background-color: {ACCENT}22; color: {ACCENT}; }}
        QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}
        QStatusBar {{ background-color: {BG_SURFACE}; color: {TEXT_MUTED}; border-top: 1px solid {BORDER}; }}
        QSplitter::handle {{ background-color: {BORDER}; }}
        QSplitter::handle:hover {{ background-color: {ACCENT}55; }}
    """


def dialog_stylesheet() -> str:
    return f"""
        QDialog {{ background-color: {BG_BASE}; color: {TEXT_PRIMARY}; }}
        {base_stylesheet()}
    """
