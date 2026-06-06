from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ivo.core.user_settings import UserSettings, UserSettingsStore
from ivo.ui.theme import PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE
from ivo.workspace_paths import default_user_settings_path


class SettingsPage(QWidget):
    saved = Signal(object)

    def __init__(
        self,
        *,
        settings_path: Path | None = None,
        runtime_root: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        root = (runtime_root or Path.cwd()).resolve()
        self.store = UserSettingsStore(
            settings_path or default_user_settings_path(root=root),
            runtime_root=root,
        )
        settings = self.store.load()

        self.models_dir_edit = QLineEdit(str(settings.models_dir))
        self.projects_dir_edit = QLineEdit(str(settings.projects_dir))
        self.lm_studio_url_edit = QLineEdit(settings.lm_studio_base_url)
        self.prefer_gpu_checkbox = QCheckBox("优先使用 GPU")
        self.prefer_gpu_checkbox.setChecked(settings.prefer_gpu)
        self.browse_models_button = QPushButton("选择模型目录")
        self.browse_projects_button = QPushButton("选择项目目录")
        self.save_button = QPushButton("保存设置")
        self.status_label = QLabel("")

        self.browse_models_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.browse_projects_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.save_button.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.browse_models_button.clicked.connect(lambda: self.browse_directory(self.models_dir_edit))
        self.browse_projects_button.clicked.connect(lambda: self.browse_directory(self.projects_dir_edit))
        self.save_button.clicked.connect(self.save_settings)

        form = QFormLayout()
        form.addRow("默认模型目录", self.models_dir_edit)
        form.addRow("", self.browse_models_button)
        form.addRow("默认项目目录", self.projects_dir_edit)
        form.addRow("", self.browse_projects_button)
        form.addRow("LM Studio 地址", self.lm_studio_url_edit)
        form.addRow("", self.prefer_gpu_checkbox)

        layout = QVBoxLayout()
        layout.setContentsMargins(28, 28, 28, 28)
        title = QLabel("设置")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        layout.addLayout(form)
        layout.addWidget(self.save_button)
        layout.addWidget(self.status_label)
        layout.addStretch()
        self.setLayout(layout)

    def browse_directory(self, target_edit: QLineEdit) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "选择目录",
            target_edit.text().strip() or str(Path.cwd()),
        )
        if path:
            target_edit.setText(path)

    def save_settings(self) -> UserSettings:
        current = self.store.load()
        settings = current.model_copy(
            update={
                "models_dir": Path(self.models_dir_edit.text().strip() or "models"),
                "projects_dir": Path(self.projects_dir_edit.text().strip() or "runs"),
                "prefer_gpu": self.prefer_gpu_checkbox.isChecked(),
                "lm_studio_base_url": self.lm_studio_url_edit.text().strip()
                or "http://127.0.0.1:1995/v1",
            }
        )
        saved = self.store.save(settings)
        self.status_label.setText("设置已保存")
        self.saved.emit(saved)
        return saved
