"""Theme system for the Intelligent Voice Over application.

Uses Qt dynamic properties (e.g. widget.setProperty("cssClass", "card"))
combined with an application-level stylesheet.  When the theme changes,
re-applying the stylesheet instantly updates all widgets that have
cssClass properties set – no widget-level setStyleSheet() needed.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QLabel, QProgressBar, QPushButton, QWidget


# ── Color palette ──────────────────────────────────────────────────────────

# Light (default)
LIGHT_BG = "#F5F5F7"
LIGHT_SURFACE = "#FFFFFF"
LIGHT_PRIMARY = "#007AFF"
LIGHT_SUCCESS = "#34C759"
LIGHT_WARNING = "#FF9500"
LIGHT_DANGER = "#FF3B30"
LIGHT_TEXT_PRIMARY = "#1D1D1F"
LIGHT_TEXT_SECONDARY = "#6E6E73"
LIGHT_BORDER = "#D2D2D7"
LIGHT_HOVER_OVERLAY = "#E8E8ED"
LIGHT_PRESSED_OVERLAY = "#D1D1D6"
LIGHT_SHADOW_COLOR = "rgba(0, 0, 0, 0.08)"
LIGHT_FOCUS_RING = LIGHT_PRIMARY
LIGHT_PRIMARY_HOVER = "#006AE0"
LIGHT_PRIMARY_PRESSED = "#0055B3"
LIGHT_DANGER_HOVER = "#E0342B"

# Dark
DARK_BG = "#1C1C1E"
DARK_SURFACE = "#2C2C2E"
DARK_PRIMARY = "#0A84FF"
DARK_SUCCESS = "#30D158"
DARK_WARNING = "#FF9F0A"
DARK_DANGER = "#FF453A"
DARK_TEXT_PRIMARY = "#F5F5F7"
DARK_TEXT_SECONDARY = "#8E8E93"
DARK_BORDER = "#3A3A3C"
DARK_HOVER_OVERLAY = "#48484A"
DARK_PRESSED_OVERLAY = "#5A5A5E"
DARK_SHADOW_COLOR = "rgba(0, 0, 0, 0.3)"
DARK_FOCUS_RING = DARK_PRIMARY
DARK_PRIMARY_HOVER = "#409CFF"
DARK_PRIMARY_PRESSED = "#0070E0"
DARK_DANGER_HOVER = "#FF6961"

# Legacy aliases (for modules that import them directly)
BACKGROUND = LIGHT_BG
SURFACE = LIGHT_SURFACE
PRIMARY = LIGHT_PRIMARY
SUCCESS = LIGHT_SUCCESS
WARNING = LIGHT_WARNING
DANGER = LIGHT_DANGER
TEXT_PRIMARY = LIGHT_TEXT_PRIMARY
TEXT_SECONDARY = LIGHT_TEXT_SECONDARY
BORDER = LIGHT_BORDER
DARK_BACKGROUND = DARK_BG
DARK_SURFACE = DARK_SURFACE
DARK_TEXT_PRIMARY = DARK_TEXT_PRIMARY
DARK_TEXT_SECONDARY = DARK_TEXT_SECONDARY
DARK_BORDER = DARK_BORDER

# ── Active theme state ──────────────────────────────────────────────────────

_active_theme: str = "light"
_theme_change_callbacks: list[Callable[[str], None]] = []


def get_active_theme() -> str:
    """Return the currently active resolved theme ('light' or 'dark')."""
    return _active_theme


def on_theme_changed(callback: Callable[[str], None]) -> None:
    """Register a callback to be called when the theme changes.

    The callback receives one argument: the new resolved theme ('light' or 'dark').
    """
    _theme_change_callbacks.append(callback)


def _notify_theme_changed(resolved: str) -> None:
    for cb in _theme_change_callbacks:
        try:
            cb(resolved)
        except Exception:
            pass


# ── System theme detection ─────────────────────────────────────────────────

def resolve_theme_mode(mode: str) -> str:
    """Resolve 'system' to 'light' or 'dark' based on OS colour scheme."""
    if mode != "system":
        return mode
    try:
        app = QApplication.instance()
        if app is not None and isinstance(app, QApplication):
            hints = app.styleHints()
            scheme = hints.colorScheme()
            from PySide6.QtCore import Qt
            return "dark" if scheme == Qt.ColorScheme.Dark else "light"
    except Exception:
        pass
    return "light"


# ── Qt palette helpers ──────────────────────────────────────────────────────

def _light_palette() -> QPalette:
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor(LIGHT_BG))
    p.setColor(QPalette.ColorRole.WindowText, QColor(LIGHT_TEXT_PRIMARY))
    p.setColor(QPalette.ColorRole.Base, QColor(LIGHT_SURFACE))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor("#E8E8ED"))
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor(LIGHT_SURFACE))
    p.setColor(QPalette.ColorRole.ToolTipText, QColor(LIGHT_TEXT_PRIMARY))
    p.setColor(QPalette.ColorRole.Text, QColor(LIGHT_TEXT_PRIMARY))
    p.setColor(QPalette.ColorRole.Button, QColor(LIGHT_SURFACE))
    p.setColor(QPalette.ColorRole.ButtonText, QColor(LIGHT_TEXT_PRIMARY))
    p.setColor(QPalette.ColorRole.BrightText, QColor(LIGHT_DANGER))
    p.setColor(QPalette.ColorRole.Link, QColor(LIGHT_PRIMARY))
    p.setColor(QPalette.ColorRole.Highlight, QColor(LIGHT_PRIMARY))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(LIGHT_TEXT_SECONDARY))
    return p


def _dark_palette() -> QPalette:
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor(DARK_BG))
    p.setColor(QPalette.ColorRole.WindowText, QColor(DARK_TEXT_PRIMARY))
    p.setColor(QPalette.ColorRole.Base, QColor(DARK_SURFACE))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor("#38383A"))
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor(DARK_SURFACE))
    p.setColor(QPalette.ColorRole.ToolTipText, QColor(DARK_TEXT_PRIMARY))
    p.setColor(QPalette.ColorRole.Text, QColor(DARK_TEXT_PRIMARY))
    p.setColor(QPalette.ColorRole.Button, QColor(DARK_SURFACE))
    p.setColor(QPalette.ColorRole.ButtonText, QColor(DARK_TEXT_PRIMARY))
    p.setColor(QPalette.ColorRole.BrightText, QColor(DARK_DANGER))
    p.setColor(QPalette.ColorRole.Link, QColor(DARK_PRIMARY))
    p.setColor(QPalette.ColorRole.Highlight, QColor(DARK_PRIMARY))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor("#000000"))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(DARK_TEXT_SECONDARY))
    return p


# ── CSS class helpers (set on widgets instead of setStyleSheet) ────────────

def mark_card(widget: QWidget) -> None:
    """Mark a QFrame as a card-style container."""
    widget.setProperty("cssClass", "card")


def mark_primary_button(button: QPushButton) -> None:
    """Mark a QPushButton with primary accent style."""
    button.setProperty("cssClass", "primary")


def mark_secondary_button(button: QPushButton) -> None:
    """Mark a QPushButton with secondary/outline style."""
    button.setProperty("cssClass", "secondary")


def mark_compact_button(button: QPushButton) -> None:
    """Mark a QPushButton with compact style."""
    button.setProperty("cssClass", "compact")


def mark_section_label(label: QLabel) -> None:
    """Mark a QLabel with section-label style."""
    label.setProperty("cssClass", "sectionLabel")


def mark_status_badge(widget: QLabel, status: str) -> None:
    """Mark a QLabel status badge with a status-specific style.

    Accepted status values: ready, warning, danger, missing, failed,
    unchecked, applied.
    """
    valid = {
        "ready", "warning", "danger", "missing", "failed",
        "unchecked", "applied",
    }
    widget.setProperty("cssClass", status if status in valid else "unchecked")


def mark_card_disabled(widget: QWidget) -> None:
    """Mark a QFrame as a disabled/muted card (dim background)."""
    widget.setProperty("cssClass", "cardDisabled")


def mark_card_highlighted(widget: QWidget) -> None:
    """Mark a QFrame as a highlighted card (primary border)."""
    widget.setProperty("cssClass", "cardHighlighted")


def mark_progress_idle(bar: QProgressBar) -> None:
    """Mark a QProgressBar with idle (muted) chunk colour."""
    bar.setProperty("cssClass", "progressIdle")


def mark_progress_running(bar: QProgressBar) -> None:
    """Mark a QProgressBar with running (primary) chunk colour."""
    bar.setProperty("cssClass", "progressRunning")


def mark_progress_paused(bar: QProgressBar) -> None:
    """Mark a QProgressBar with paused (warning) chunk colour."""
    bar.setProperty("cssClass", "progressPaused")


def mark_sidebar(widget: QWidget) -> None:
    """Mark a QFrame as the app sidebar."""
    widget.setProperty("cssClass", "sidebar")


def mark_nav_button(button: QPushButton) -> None:
    """Mark a QPushButton as a sidebar navigation button."""
    button.setProperty("cssClass", "nav")


def mark_stage_list_item(button: QPushButton) -> None:
    """Mark a QPushButton as a stage list navigation item."""
    button.setProperty("cssClass", "stageListItem")


def mark_provider_item(widget: QWidget) -> None:
    """Mark a QFrame as a provider item row."""
    widget.setProperty("cssClass", "providerItem")


def mark_kind_badge(label: QLabel) -> None:
    """Mark a QLabel as a kind badge (local/cloud)."""
    label.setProperty("cssClass", "kindBadge")


def mark_sub_text(label: QLabel) -> None:
    """Mark a QLabel as secondary/sub text."""
    label.setProperty("cssClass", "subText")


def mark_stage_panel(widget: QWidget) -> None:
    """Mark a QFrame as the right-side stage panel."""
    widget.setProperty("cssClass", "stagePanel")


def mark_heading1(label: QLabel) -> None:
    """Mark a QLabel with heading1 style (24px, bold)."""
    label.setProperty("cssClass", "heading1")


def mark_heading2(label: QLabel) -> None:
    """Mark a QLabel with heading2 style (18px, bold)."""
    label.setProperty("cssClass", "heading2")


def mark_heading3(label: QLabel) -> None:
    """Mark a QLabel with heading3 style (16px, semibold)."""
    label.setProperty("cssClass", "heading3")


def mark_body_text(label: QLabel) -> None:
    """Mark a QLabel with body text style (14px)."""
    label.setProperty("cssClass", "bodyText")


def mark_caption_text(label: QLabel) -> None:
    """Mark a QLabel with caption text style (12px)."""
    label.setProperty("cssClass", "captionText")


def mark_danger_button(button: QPushButton) -> None:
    """Mark a QPushButton with danger/destructive style."""
    button.setProperty("cssClass", "dangerButton")


def mark_dialog(widget: QWidget) -> None:
    """Mark a QWidget as a dialog container."""
    widget.setProperty("cssClass", "dialog")


def mark_status_dot(label: QLabel, status: str) -> None:
    """Mark a QLabel as a status indicator dot.

    Accepted status values: ready, warning, danger, unchecked.
    """
    valid = {"ready", "warning", "danger", "unchecked"}
    label.setProperty("cssClass", f"statusDot_{status}" if status in valid else "statusDot_unchecked")


def mark_item_title(label: QLabel) -> None:
    """Mark a QLabel as an item title (semibold, 13px)."""
    label.setProperty("cssClass", "itemTitle")


def mark_status_success(label: QLabel) -> None:
    """Mark a QLabel with success color text."""
    label.setProperty("cssClass", "statusSuccess")


def mark_status_danger(label: QLabel) -> None:
    """Mark a QLabel with danger color text."""
    label.setProperty("cssClass", "statusDanger")


def mark_status_warning(label: QLabel) -> None:
    """Mark a QLabel with warning color text."""
    label.setProperty("cssClass", "statusWarning")


def mark_warning_text(label: QLabel) -> None:
    """Mark a QLabel with warning color text."""
    label.setProperty("cssClass", "warningText")


def mark_error_border(widget: QWidget) -> None:
    """Mark a widget with error border state."""
    widget.setProperty("cssClass", "errorBorder")


def mark_icon_button(button: QPushButton) -> None:
    """Mark a QPushButton as an icon-only button."""
    button.setProperty("cssClass", "iconButton")


def mark_scheme_detail_frame(widget: QWidget) -> None:
    """Mark a QFrame as a scheme detail frame."""
    widget.setProperty("cssClass", "schemeDetailFrame")


def mark_scheme_list_item(button: QPushButton) -> None:
    """Mark a QPushButton as a scheme list item in the left panel."""
    button.setProperty("cssClass", "schemeListItem")


def mark_scheme_list_panel(widget: QWidget) -> None:
    """Mark a QFrame as the scheme list left panel."""
    widget.setProperty("cssClass", "schemeListPanel")


def mark_link_button(button: QPushButton) -> None:
    """Mark a QPushButton as an inline text link."""
    button.setProperty("cssClass", "linkButton")


def mark_elapsed_label(label: QLabel) -> None:
    """Mark a QLabel as an elapsed time label (semibold)."""
    label.setProperty("cssClass", "elapsedLabel")


def active_color(name: str) -> str:
    """Return the active theme's colour for a semantic name.

    Accepted names: primary, danger, success, warning, text_secondary,
    surface, border, bg, text, hover_overlay, pressed_overlay,
    shadow_color, focus_ring, primary_hover, primary_pressed, danger_hover.
    """
    is_dark = _active_theme == "dark"
    colors = {
        "primary": DARK_PRIMARY if is_dark else LIGHT_PRIMARY,
        "danger": DARK_DANGER if is_dark else LIGHT_DANGER,
        "success": DARK_SUCCESS if is_dark else LIGHT_SUCCESS,
        "warning": DARK_WARNING if is_dark else LIGHT_WARNING,
        "text_secondary": DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY,
        "surface": DARK_SURFACE if is_dark else LIGHT_SURFACE,
        "border": DARK_BORDER if is_dark else LIGHT_BORDER,
        "bg": DARK_BG if is_dark else LIGHT_BG,
        "text": DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY,
        "hover_overlay": DARK_HOVER_OVERLAY if is_dark else LIGHT_HOVER_OVERLAY,
        "pressed_overlay": DARK_PRESSED_OVERLAY if is_dark else LIGHT_PRESSED_OVERLAY,
        "shadow_color": DARK_SHADOW_COLOR if is_dark else LIGHT_SHADOW_COLOR,
        "focus_ring": DARK_FOCUS_RING if is_dark else LIGHT_FOCUS_RING,
        "primary_hover": DARK_PRIMARY_HOVER if is_dark else LIGHT_PRIMARY_HOVER,
        "primary_pressed": DARK_PRIMARY_PRESSED if is_dark else LIGHT_PRIMARY_PRESSED,
        "danger_hover": DARK_DANGER_HOVER if is_dark else LIGHT_DANGER_HOVER,
    }
    return colors.get(name, "#CCCCCC")


# ── Application-level stylesheet builder ───────────────────────────────────

def _build_stylesheet(bg: str, surface: str, primary: str, danger: str,
                      success: str, warning: str,
                      text: str, text_sec: str, border: str,
                      disabled_primary: str,
                      hover_bg: str, primary_bg: str,
                      hover_overlay: str, pressed_overlay: str,
                      shadow_color: str, focus_ring: str,
                      primary_hover: str, primary_pressed: str,
                      danger_hover: str) -> str:
    return f"""
    /* ── Base ── */
    QWidget {{
        font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
        font-size: 13px;
        color: {text};
    }}
    QMainWindow, QWidget#AppRoot {{
        background: {bg};
    }}

    /* ── Card ── */
    QFrame[cssClass="card"] {{
        background: {surface};
        border: 1px solid {border};
        border-radius: 12px;
    }}
    QFrame[cssClass="cardDisabled"] {{
        background: {bg};
        border: 1px solid {border};
        border-radius: 10px;
    }}
    QFrame[cssClass="cardHighlighted"] {{
        background: {surface};
        border: 2px solid {primary};
        border-radius: 10px;
    }}

    /* ── Typography ── */
    QLabel[cssClass="heading1"] {{
        font-size: 24px;
        font-weight: 700;
        color: {text};
    }}
    QLabel[cssClass="heading2"] {{
        font-size: 18px;
        font-weight: 700;
        color: {text};
    }}
    QLabel[cssClass="heading3"] {{
        font-size: 16px;
        font-weight: 600;
        color: {text};
    }}
    QLabel[cssClass="bodyText"] {{
        font-size: 14px;
        font-weight: 400;
        color: {text};
    }}
    QLabel[cssClass="captionText"] {{
        font-size: 12px;
        font-weight: 400;
        color: {text_sec};
    }}

    /* ── Item title ── */
    QLabel[cssClass="itemTitle"] {{
        font-weight: 600;
        font-size: 13px;
        color: {text};
    }}

    /* ── Warning text ── */
    QLabel[cssClass="warningText"] {{
        color: {warning};
        font-size: 12px;
    }}

    /* ── Error border ── */
    QLineEdit[cssClass="errorBorder"] {{
        border: 1px solid {danger};
    }}

    /* ── Elapsed label ── */
    QLabel[cssClass="elapsedLabel"] {{
        font-weight: 600;
        color: {text_sec};
    }}

    /* ── Scheme detail frame ── */
    QFrame[cssClass="schemeDetailFrame"] {{
        padding: 8px;
    }}

    /* ── Icon button ── */
    QPushButton[cssClass="iconButton"] {{
        border: none;
        font-size: 14px;
        background: transparent;
        padding: 4px;
    }}
    QPushButton[cssClass="iconButton"]:hover {{
        background: {hover_overlay};
        border-radius: 4px;
    }}

    /* ── Primary button ── */
    QPushButton[cssClass="primary"] {{
        background: {primary};
        color: white;
        border: 0;
        border-radius: 10px;
        padding: 10px 16px;
        font-weight: 600;
    }}
    QPushButton[cssClass="primary"]:hover {{
        background: {primary_hover};
    }}
    QPushButton[cssClass="primary"]:pressed {{
        background: {primary_pressed};
    }}
    QPushButton[cssClass="primary"]:disabled {{
        background: {disabled_primary};
    }}

    /* ── Secondary button ── */
    QPushButton[cssClass="secondary"] {{
        background: {surface};
        color: {text};
        border: 1px solid {border};
        border-radius: 10px;
        padding: 9px 14px;
    }}
    QPushButton[cssClass="secondary"]:hover {{
        background: {hover_overlay};
    }}
    QPushButton[cssClass="secondary"]:pressed {{
        background: {pressed_overlay};
    }}

    /* ── Compact button ── */
    QPushButton[cssClass="compact"] {{
        background: {surface};
        color: {text};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 6px 12px;
        font-size: 12px;
    }}
    QPushButton[cssClass="compact"]:hover {{
        background: {hover_overlay};
    }}
    QPushButton[cssClass="compact"]:pressed {{
        background: {pressed_overlay};
    }}

    /* ── Danger button ── */
    QPushButton[cssClass="dangerButton"] {{
        color: {danger};
        background: transparent;
        border: 1px solid {danger};
        border-radius: 10px;
        padding: 9px 14px;
    }}
    QPushButton[cssClass="dangerButton"]:hover {{
        background: {danger};
        color: white;
    }}
    QPushButton[cssClass="dangerButton"]:pressed {{
        background: {danger_hover};
        color: white;
    }}

    /* ── Dialog ── */
    QWidget[cssClass="dialog"] {{
        background: {surface};
        border-radius: 12px;
    }}

    /* ── Status dot ── */
    QLabel[cssClass="statusDot_ready"] {{
        color: {success};
        font-size: 16px;
    }}
    QLabel[cssClass="statusDot_warning"] {{
        color: {warning};
        font-size: 16px;
    }}
    QLabel[cssClass="statusDot_danger"] {{
        color: {danger};
        font-size: 16px;
    }}
    QLabel[cssClass="statusDot_unchecked"] {{
        color: {text_sec};
        font-size: 16px;
    }}

    /* ── Section label ── */
    QLabel[cssClass="sectionLabel"] {{
        font-weight: 600;
        color: {text_sec};
        font-size: 12px;
    }}

    /* ── Page title ── */
    QLabel#PageTitle {{
        font-size: 24px;
        font-weight: 700;
    }}

    /* ── Secondary text ── */
    QLabel#SecondaryText {{
        color: {text_sec};
    }}
    QLabel#DangerText {{
        color: {danger};
        font-weight: 600;
    }}

    /* ── QTabWidget ── */
    QTabWidget {{
        background: {bg};
    }}
    QTabWidget::pane {{
        background: {surface};
        border: 1px solid {border};
        border-top: 2px solid {primary};
        border-radius: 0px 0px 10px 10px;
        padding: 12px;
    }}
    QTabBar::tab {{
        background: transparent;
        color: {text_sec};
        padding: 10px 20px;
        margin-right: 2px;
        border: none;
        border-bottom: 2px solid transparent;
        font-size: 13px;
    }}
    QTabBar::tab:hover {{
        color: {text};
        border-bottom-color: {hover_overlay};
    }}
    QTabBar::tab:selected {{
        color: {primary};
        border-bottom: 2px solid {primary};
        font-weight: 600;
    }}

    /* ── QComboBox ── */
    QComboBox {{
        padding: 6px 10px;
        border: 1px solid {border};
        border-radius: 8px;
        background: {surface};
        color: {text};
        min-width: 120px;
    }}
    QComboBox:focus {{
        border: 2px solid {focus_ring};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background: {surface};
        color: {text};
        selection-background-color: {primary};
        selection-color: white;
        border: 1px solid {border};
        border-radius: 4px;
    }}

    /* ── Line edit ── */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background: {surface};
        border: 1px solid {border};
        border-radius: 6px;
        padding: 6px 10px;
        color: {text};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border: 2px solid {focus_ring};
        padding: 5px 9px;
    }}

    /* ── QListWidget / QTableWidget ── */
    QListWidget, QTableWidget, QTreeWidget {{
        background: {surface};
        border: 1px solid {border};
        border-radius: 8px;
        color: {text};
        alternate-background-color: {hover_overlay};
    }}
    QListWidget {{
        padding: 6px;
    }}
    QListWidget::item {{
        padding: 10px 8px;
        border-radius: 8px;
    }}
    QListWidget::item:selected, QTableWidget::item:selected {{
        background: {primary_bg};
        color: {primary};
    }}
    QHeaderView::section {{
        background: {surface};
        color: {text_sec};
        border: none;
        border-bottom: 1px solid {border};
        padding: 6px 10px;
        font-weight: 600;
    }}

    /* ── QScrollBar ── */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {border};
        border-radius: 4px;
        min-height: 32px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {text_sec};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
    }}

    /* ── Splitter ── */
    QSplitter::handle {{
        background: {border};
    }}

    /* ── QCheckBox / QRadioButton ── */
    QCheckBox, QRadioButton {{
        spacing: 8px;
        color: {text};
    }}

    /* ── QGroupBox ── */
    QGroupBox {{
        font-weight: bold;
        padding-top: 16px;
        margin-top: 8px;
        border: 1px solid {border};
        border-radius: 10px;
        padding: 16px 12px 12px 12px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: {text};
    }}

    /* ── QProgressBar ── */
    QProgressBar {{
        border: 1px solid {border};
        border-radius: 6px;
        text-align: center;
        background: {hover_overlay};
        height: 20px;
    }}
    QProgressBar::chunk {{
        background: {primary};
        border-radius: 5px;
    }}
    QProgressBar[cssClass="progressIdle"]::chunk {{
        background: {text_sec};
    }}
    QProgressBar[cssClass="progressRunning"]::chunk {{
        background: {primary};
    }}
    QProgressBar[cssClass="progressPaused"]::chunk {{
        background: {warning};
    }}

    /* ── Status badge ── */
    QLabel[cssClass="ready"], QLabel[cssClass="applied"] {{
        color: {success};
        background: {surface};
        border: 1px solid {success};
        border-radius: 10px;
        padding: 3px 9px;
        font-size: 12px;
        font-weight: 600;
    }}
    QLabel[cssClass="warning"] {{
        color: {warning};
        background: {surface};
        border: 1px solid {warning};
        border-radius: 10px;
        padding: 3px 9px;
        font-size: 12px;
        font-weight: 600;
    }}
    QLabel[cssClass="danger"], QLabel[cssClass="missing"],
    QLabel[cssClass="failed"] {{
        color: {danger};
        background: {surface};
        border: 1px solid {danger};
        border-radius: 10px;
        padding: 3px 9px;
        font-size: 12px;
        font-weight: 600;
    }}
    QLabel[cssClass="unchecked"] {{
        color: {text_sec};
        background: {surface};
        border: 1px solid {border};
        border-radius: 10px;
        padding: 3px 9px;
        font-size: 12px;
        font-weight: 600;
    }}

    /* ── Sidebar ── */
    QFrame[cssClass="sidebar"] {{
        background: {surface};
        border-right: 1px solid {border};
    }}

    /* ── Nav button ── */
    QPushButton[cssClass="nav"] {{
        text-align: left;
        padding: 10px 12px 10px 16px;
        border: 0;
        border-radius: 9px;
        background: transparent;
        color: {text};
    }}
    QPushButton[cssClass="nav"]:hover {{
        background: {hover_bg};
    }}
    QPushButton[cssClass="nav"]:checked {{
        background: {primary_bg};
        color: {primary};
        font-weight: 600;
        border-left: 3px solid {primary};
        padding-left: 13px;
    }}

    /* ── QToolTip ── */
    QToolTip {{
        background: {surface};
        color: {text};
        border: 1px solid {border};
        border-radius: 6px;
        padding: 6px 10px;
    }}

    /* ── Stage list item (model services left nav) ── */
    QPushButton[cssClass="stageListItem"] {{
        text-align: left;
        padding: 8px 10px;
        border: 0;
        border-radius: 8px;
        background: transparent;
        color: {text};
        font-size: 13px;
    }}
    QPushButton[cssClass="stageListItem"]:hover {{
        background: {hover_bg};
    }}
    QPushButton[cssClass="stageListItem"]:checked {{
        background: {primary_bg};
        color: {primary};
        font-weight: 600;
    }}

    /* ── Provider item row ── */
    QFrame[cssClass="providerItem"] {{
        background: {bg};
        border: 1px solid {border};
        border-radius: 8px;
    }}
    QFrame[cssClass="providerItem"]:hover {{
        background: {hover_overlay};
        border-color: {primary};
    }}

    /* ── Kind badge ── */
    QLabel[cssClass="kindBadge"] {{
        color: {primary};
        font-size: 10px;
        font-weight: 600;
        padding: 2px 8px;
        border: 1px solid {primary};
        border-radius: 10px;
        background: {primary_bg};
    }}

    /* ── Scheme list panel (left sidebar) ── */
    QFrame[cssClass="schemeListPanel"] {{
        background: {surface};
        border: 1px solid {border};
        border-radius: 12px;
    }}

    /* ── Scheme list item ── */
    QPushButton[cssClass="schemeListItem"] {{
        text-align: left;
        padding: 10px 12px;
        border: 0;
        border-radius: 8px;
        background: transparent;
        color: {text};
        font-size: 13px;
    }}
    QPushButton[cssClass="schemeListItem"]:hover {{
        background: {hover_bg};
    }}
    QPushButton[cssClass="schemeListItem"]:checked {{
        background: {primary_bg};
        color: {primary};
        font-weight: 600;
        border-left: 3px solid {primary};
        padding-left: 9px;
    }}

    /* ── Link button ── */
    QPushButton[cssClass="linkButton"] {{
        border: 0;
        background: transparent;
        color: {primary};
        font-size: 12px;
        padding: 0;
    }}
    QPushButton[cssClass="linkButton"]:hover {{
        text-decoration: underline;
    }}

    /* ── Dependency row ── */
    QFrame[cssClass="depRow"] {{
        background: {surface};
        border: 1px solid {border};
        border-radius: 6px;
    }}
    QFrame[cssClass="depRow"]:hover {{
        border-color: {primary};
    }}

    /* ── Dependency group ── */
    QFrame[cssClass="depGroup"] {{
        background: transparent;
        border: 1px solid {border};
        border-radius: 8px;
    }}

    /* ── Sub text ── */
    QLabel[cssClass="subText"] {{
        color: {text_sec};
        font-size: 11px;
    }}

    /* ── Status text colors ── */
    QLabel[cssClass="statusSuccess"] {{
        color: {success};
    }}
    QLabel[cssClass="statusDanger"] {{
        color: {danger};
    }}
    QLabel[cssClass="statusWarning"] {{
        color: {warning};
    }}

    /* ── Stage panel ── */
    QFrame[cssClass="stagePanel"] {{
        background: {surface};
        border: 1px solid {border};
        border-radius: 12px;
    }}

    /* ── QMenu ── */
    QMenu {{
        background: {surface};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 24px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background: {primary_bg};
        color: {primary};
    }}
    QMenu::separator {{
        height: 1px;
        background: {border};
        margin: 4px 8px;
    }}

    /* ── QSpinBox ── */
    QSpinBox {{
        padding: 6px 10px;
        border: 1px solid {border};
        border-radius: 8px;
        background: {surface};
    }}
    QSpinBox:focus {{
        border: 2px solid {focus_ring};
    }}

    /* ── QSlider ── */
    QSlider::groove:horizontal {{
        height: 4px;
        background: {border};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {primary};
        width: 16px;
        height: 16px;
        margin: -6px 0;
        border-radius: 8px;
    }}

    /* ── QTextEdit (read-only) ── */
    QTextEdit[readOnly="true"] {{
        background: {bg};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 8px;
    }}
    """


# ── Theme application ──────────────────────────────────────────────────────

def apply_app_theme(app: QApplication, mode: str = "light") -> None:
    """Apply theme to the whole application.

    ``mode`` may be ``"light"``, ``"dark"``, or ``"system"``.
    """
    global _active_theme
    resolved = resolve_theme_mode(mode)
    changed = _active_theme != resolved
    _active_theme = resolved

    # Apply Fusion style for consistent cross-platform look
    app.setStyle("Fusion")

    # Set Qt palette for proper dark/light system colours
    palette = _dark_palette() if resolved == "dark" else _light_palette()
    app.setPalette(palette)

    # Build and apply application-level stylesheet
    if resolved == "dark":
        stylesheet = _build_stylesheet(
            bg=DARK_BG, surface=DARK_SURFACE,
            primary=DARK_PRIMARY, danger=DARK_DANGER,
            success=DARK_SUCCESS, warning=DARK_WARNING,
            text=DARK_TEXT_PRIMARY, text_sec=DARK_TEXT_SECONDARY,
            border=DARK_BORDER, disabled_primary="#4A4A6A",
            hover_bg="#3A3A3C", primary_bg="#1A2F4A",
            hover_overlay=DARK_HOVER_OVERLAY,
            pressed_overlay=DARK_PRESSED_OVERLAY,
            shadow_color=DARK_SHADOW_COLOR,
            focus_ring=DARK_FOCUS_RING,
            primary_hover=DARK_PRIMARY_HOVER,
            primary_pressed=DARK_PRIMARY_PRESSED,
            danger_hover=DARK_DANGER_HOVER,
        )
    else:
        stylesheet = _build_stylesheet(
            bg=LIGHT_BG, surface=LIGHT_SURFACE,
            primary=LIGHT_PRIMARY, danger=LIGHT_DANGER,
            success=LIGHT_SUCCESS, warning=LIGHT_WARNING,
            text=LIGHT_TEXT_PRIMARY, text_sec=LIGHT_TEXT_SECONDARY,
            border=LIGHT_BORDER, disabled_primary="#A7C7F7",
            hover_bg="#EFEFF4", primary_bg="#E5F0FF",
            hover_overlay=LIGHT_HOVER_OVERLAY,
            pressed_overlay=LIGHT_PRESSED_OVERLAY,
            shadow_color=LIGHT_SHADOW_COLOR,
            focus_ring=LIGHT_FOCUS_RING,
            primary_hover=LIGHT_PRIMARY_HOVER,
            primary_pressed=LIGHT_PRIMARY_PRESSED,
            danger_hover=LIGHT_DANGER_HOVER,
        )
    app.setStyleSheet(stylesheet)

    if changed:
        _notify_theme_changed(resolved)
