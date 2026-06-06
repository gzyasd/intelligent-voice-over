from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from ivo.core.project_library import ProjectLibraryItem
from ivo.ui.empty_states import EmptyStatePanel
from ivo.ui.theme import CARD_STYLE, PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE


class ProjectLibraryPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.open_project_buttons: list[QPushButton] = []
        self.open_folder_buttons: list[QPushButton] = []
        self.empty_state: EmptyStatePanel | None = None
        self.open_existing_project_button = QPushButton("打开已有项目")
        self.open_existing_project_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self._summary_parts: list[str] = []

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(28, 28, 28, 28)
        self.content_layout.setSpacing(12)
        title = QLabel("项目库")
        title.setObjectName("PageTitle")
        self.content_layout.addWidget(title)
        self.setLayout(self.content_layout)

    def set_projects(self, projects: list[ProjectLibraryItem]) -> None:
        self._clear_project_widgets()
        self.open_project_buttons = []
        self.open_folder_buttons = []
        self.empty_state = None
        self._summary_parts = []
        if not projects:
            self.empty_state = EmptyStatePanel(
                title="还没有项目",
                description="新建一个配音项目，或打开之前保存的 .ivoproj 项目文件夹。",
                action_text="新建配音项目",
            )
            self.open_existing_project_button = QPushButton("打开已有项目")
            self.open_existing_project_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
            self.content_layout.addWidget(self.empty_state)
            self.content_layout.addWidget(self.open_existing_project_button)
            self._summary_parts.extend(
                [
                    self.empty_state.title_label.text(),
                    self.empty_state.description_label.text(),
                    self.empty_state.action_button.text(),
                    self.open_existing_project_button.text(),
                ]
            )
            self.content_layout.addStretch()
            return
        for item in projects:
            self._add_project_card(item)
        self.content_layout.addStretch()

    def project_count(self) -> int:
        return len(self.open_project_buttons)

    def summary_text(self) -> str:
        return "\n".join(self._summary_parts)

    def _add_project_card(self, item: ProjectLibraryItem) -> None:
        card = QFrame()
        card.setStyleSheet(CARD_STYLE)
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        name = QLabel(item.name)
        name.setStyleSheet("font-size: 16px; font-weight: 700;")
        status = QLabel(f"{item.status}  {item.status_detail}".strip())
        status.setObjectName("SecondaryText")
        path_label = QLabel(str(item.path))
        path_label.setObjectName("SecondaryText")
        open_project = QPushButton("打开项目")
        open_project.setStyleSheet(PRIMARY_BUTTON_STYLE)
        open_folder = QPushButton("打开文件夹")
        open_folder.setStyleSheet(SECONDARY_BUTTON_STYLE)
        layout.addWidget(name)
        layout.addWidget(status)
        layout.addWidget(path_label)
        layout.addWidget(open_project)
        layout.addWidget(open_folder)
        card.setLayout(layout)
        self.content_layout.addWidget(card)
        self.open_project_buttons.append(open_project)
        self.open_folder_buttons.append(open_folder)
        self._summary_parts.extend([item.name, item.status, item.status_detail])

    def _clear_project_widgets(self) -> None:
        while self.content_layout.count() > 1:
            item = self.content_layout.takeAt(1)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
