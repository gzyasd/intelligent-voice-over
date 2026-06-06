from __future__ import annotations

from PySide6.QtWidgets import QApplication

BACKGROUND = "#F5F5F7"
SURFACE = "#FFFFFF"
PRIMARY = "#007AFF"
SUCCESS = "#34C759"
WARNING = "#FF9500"
DANGER = "#FF3B30"
TEXT_PRIMARY = "#1D1D1F"
TEXT_SECONDARY = "#6E6E73"
BORDER = "#D2D2D7"

CARD_STYLE = f"""
QFrame {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
"""

PRIMARY_BUTTON_STYLE = f"""
QPushButton {{
    background: {PRIMARY};
    color: white;
    border: 0;
    border-radius: 10px;
    padding: 10px 16px;
    font-weight: 600;
}}
QPushButton:disabled {{
    background: #A7C7F7;
}}
"""

SECONDARY_BUTTON_STYLE = f"""
QPushButton {{
    background: {SURFACE};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 9px 14px;
}}
"""


def apply_app_theme(app: QApplication) -> None:
    app.setStyleSheet(
        f"""
        QWidget {{
            font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
            font-size: 13px;
            color: {TEXT_PRIMARY};
        }}
        QMainWindow, QWidget#AppRoot {{
            background: {BACKGROUND};
        }}
        QLabel#PageTitle {{
            font-size: 24px;
            font-weight: 700;
        }}
        QLabel#SecondaryText {{
            color: {TEXT_SECONDARY};
        }}
        """
    )
