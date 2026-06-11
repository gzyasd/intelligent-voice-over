from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ivo.ui.theme import mark_heading2, mark_nav_button, mark_sidebar


class AppShell(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("AppRoot")
        self._page_ids: list[str] = []
        self._buttons_by_label: dict[str, QPushButton] = {}
        self._button_by_page_id: dict[str, QPushButton] = {}

        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(190)
        self.sidebar.setStyleSheet("")
        mark_sidebar(self.sidebar)
        self.nav_layout = QVBoxLayout()
        self.nav_layout.setContentsMargins(16, 18, 16, 18)
        self.nav_layout.setSpacing(8)
        title = QLabel("智能配音")
        mark_heading2(title)
        self.nav_layout.addWidget(title)
        subtitle = QLabel("本地优先工作台")
        subtitle.setObjectName("SecondaryText")
        self.nav_layout.addWidget(subtitle)
        self.nav_layout.addSpacing(14)
        self.nav_layout.addStretch()
        self.sidebar.setLayout(self.nav_layout)

        self.stack = QStackedWidget()

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack, 1)
        self.setLayout(layout)

    def add_page(self, page_id: str, label: str, widget: QWidget) -> None:
        if page_id in self._page_ids:
            raise ValueError(f"Duplicate page id: {page_id}")
        self._page_ids.append(page_id)
        self.stack.addWidget(widget)
        button = QPushButton(label)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setCheckable(True)
        button.setStyleSheet("")
        mark_nav_button(button)
        button.clicked.connect(lambda _checked=False, page_id=page_id: self.set_current_page(page_id))
        insert_index = max(self.nav_layout.count() - 1, 0)
        self.nav_layout.insertWidget(insert_index, button)
        self._buttons_by_label[label] = button
        self._button_by_page_id[page_id] = button
        if len(self._page_ids) == 1:
            self.set_current_page(page_id)

    def navigation_labels(self) -> list[str]:
        return list(self._buttons_by_label.keys())

    def navigation_button(self, label: str) -> QPushButton:
        return self._buttons_by_label[label]

    def current_page_id(self) -> str:
        index = self.stack.currentIndex()
        return self._page_ids[index]

    def set_current_page(self, page_id: str) -> None:
        if page_id not in self._page_ids:
            raise ValueError(f"Unknown page id: {page_id}")
        index = self._page_ids.index(page_id)
        self.stack.setCurrentIndex(index)
        for candidate_page_id, button in self._button_by_page_id.items():
            button.setChecked(candidate_page_id == page_id)
