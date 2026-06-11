from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from ivo.ui.theme import mark_heading3, mark_primary_button


class EmptyStatePanel(QWidget):
    def __init__(
        self,
        *,
        title: str,
        description: str,
        action_text: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.title_label = QLabel(title)
        mark_heading3(self.title_label)
        self.description_label = QLabel(description)
        self.description_label.setWordWrap(True)
        self.description_label.setObjectName("SecondaryText")
        self.action_button = QPushButton(action_text)
        mark_primary_button(self.action_button)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.addWidget(self.title_label)
        layout.addWidget(self.description_label)
        layout.addWidget(self.action_button)
        self.setLayout(layout)
