from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from ivo.ui.theme import PRIMARY_BUTTON_STYLE, TEXT_SECONDARY


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
        self.title_label.setStyleSheet("font-size: 17px; font-weight: 700;")
        self.description_label = QLabel(description)
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self.action_button = QPushButton(action_text)
        self.action_button.setStyleSheet(PRIMARY_BUTTON_STYLE)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.addWidget(self.title_label)
        layout.addWidget(self.description_label)
        layout.addWidget(self.action_button)
        self.setLayout(layout)
