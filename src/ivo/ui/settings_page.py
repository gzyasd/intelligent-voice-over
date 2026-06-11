from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ivo.core.user_settings import PYPI_MIRRORS, UserSettings, UserSettingsStore
from ivo.ui.theme import mark_card, mark_heading3, mark_primary_button, mark_secondary_button
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
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["light", "dark", "system"])
        self.theme_combo.setCurrentText(settings.theme)
        self.pip_mirror_combo = QComboBox()
        for key, (label, _) in PYPI_MIRRORS.items():
            self.pip_mirror_combo.addItem(label, key)
        # Select the current mirror setting
        for i in range(self.pip_mirror_combo.count()):
            if self.pip_mirror_combo.itemData(i) == settings.pip_mirror:
                self.pip_mirror_combo.setCurrentIndex(i)
                break
        self.browse_models_button = QPushButton("选择模型目录")
        self.browse_projects_button = QPushButton("选择项目目录")
        self.save_button = QPushButton("保存设置")
        self.status_label = QLabel("")

        self.browse_models_button.setStyleSheet("")
        mark_secondary_button(self.browse_models_button)
        self.browse_projects_button.setStyleSheet("")
        mark_secondary_button(self.browse_projects_button)
        self.save_button.setStyleSheet("")
        mark_primary_button(self.save_button)
        self.browse_models_button.clicked.connect(lambda: self.browse_directory(self.models_dir_edit))
        self.browse_projects_button.clicked.connect(lambda: self.browse_directory(self.projects_dir_edit))
        self.save_button.clicked.connect(self.save_settings)

        # ── 卡片 1: 目录设置 ──
        dir_card = QFrame()
        dir_card.setStyleSheet("")
        mark_card(dir_card)
        dir_layout = QVBoxLayout()
        dir_layout.setContentsMargins(18, 18, 18, 18)
        dir_layout.setSpacing(10)
        dir_title = QLabel("目录设置")
        mark_heading3(dir_title)
        dir_layout.addWidget(dir_title)

        dir_form = QFormLayout()
        dir_form.setSpacing(8)
        models_row = QHBoxLayout()
        models_row.addWidget(self.models_dir_edit, 1)
        models_row.addWidget(self.browse_models_button)
        dir_form.addRow("默认模型目录", models_row)

        projects_row = QHBoxLayout()
        projects_row.addWidget(self.projects_dir_edit, 1)
        projects_row.addWidget(self.browse_projects_button)
        dir_form.addRow("默认项目目录", projects_row)
        dir_layout.addLayout(dir_form)
        dir_card.setLayout(dir_layout)

        # ── 卡片 2: 服务与性能 ──
        svc_card = QFrame()
        svc_card.setStyleSheet("")
        mark_card(svc_card)
        svc_layout = QVBoxLayout()
        svc_layout.setContentsMargins(18, 18, 18, 18)
        svc_layout.setSpacing(10)
        svc_title = QLabel("服务与性能")
        mark_heading3(svc_title)
        svc_layout.addWidget(svc_title)

        svc_form = QFormLayout()
        svc_form.setSpacing(8)
        svc_form.addRow("LM Studio 地址", self.lm_studio_url_edit)
        svc_form.addRow("硬件偏好", self.prefer_gpu_checkbox)
        svc_form.addRow("主题", self.theme_combo)
        svc_form.addRow("PyPI 镜像源", self.pip_mirror_combo)
        svc_layout.addLayout(svc_form)
        svc_card.setLayout(svc_layout)

        # ── 页面布局 ──
        layout = QVBoxLayout()
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)
        title = QLabel("设置")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        layout.addWidget(dir_card)
        layout.addWidget(svc_card)
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
                "theme": self.theme_combo.currentText(),
                "pip_mirror": self.pip_mirror_combo.currentData(),
            }
        )
        saved = self.store.save(settings)
        self.status_label.setText("设置已保存")
        self.saved.emit(saved)
        return saved
