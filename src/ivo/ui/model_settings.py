from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ivo.adapters.http import ApiAdapterProfile
from ivo.adapters.profiles import AdapterProfileStore


class ModelSettings(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.local_model_path_edit = QLineEdit()
        self.local_command_profiles_path_edit = QLineEdit()
        self.local_command_profiles_browse_button = QPushButton("浏览本地命令 profile")
        self.asr_profile_path_edit = QLineEdit()
        self.asr_profile_browse_button = QPushButton("浏览 ASR profile")
        self.asr_vars_edit = QLineEdit()
        self.translation_profile_path_edit = QLineEdit()
        self.translation_profile_browse_button = QPushButton("浏览翻译 profile")
        self.translation_vars_edit = QLineEdit()
        self.tts_profile_path_edit = QLineEdit()
        self.tts_profile_browse_button = QPushButton("浏览 TTS profile")
        self.tts_vars_edit = QLineEdit()
        self.http_adapter_path_edit = QLineEdit()
        self.profile_id_edit = QLineEdit()
        self.stage_edit = QLineEdit("translation")
        self.url_edit = QLineEdit()
        self.response_mapping_edit = QLineEdit("target_text=$.text")
        self.adapter_list = QListWidget()

        self.local_command_profiles_browse_button.clicked.connect(
            self.browse_local_command_profiles
        )
        self.asr_profile_browse_button.clicked.connect(self.browse_asr_profile)
        self.translation_profile_browse_button.clicked.connect(self.browse_translation_profile)
        self.tts_profile_browse_button.clicked.connect(self.browse_tts_profile)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("本地模型路径"))
        layout.addWidget(self.local_model_path_edit)
        layout.addWidget(QLabel("本地命令 profiles JSON"))
        layout.addWidget(self.local_command_profiles_path_edit)
        layout.addWidget(self.local_command_profiles_browse_button)
        layout.addWidget(QLabel("ASR HTTP profile JSON"))
        layout.addWidget(self.asr_profile_path_edit)
        layout.addWidget(self.asr_profile_browse_button)
        layout.addWidget(QLabel("ASR 变量 KEY=VALUE"))
        layout.addWidget(self.asr_vars_edit)
        layout.addWidget(QLabel("翻译 HTTP profile JSON"))
        layout.addWidget(self.translation_profile_path_edit)
        layout.addWidget(self.translation_profile_browse_button)
        layout.addWidget(QLabel("翻译变量 KEY=VALUE"))
        layout.addWidget(self.translation_vars_edit)
        layout.addWidget(QLabel("TTS HTTP profile JSON"))
        layout.addWidget(self.tts_profile_path_edit)
        layout.addWidget(self.tts_profile_browse_button)
        layout.addWidget(QLabel("TTS 变量 KEY=VALUE"))
        layout.addWidget(self.tts_vars_edit)
        layout.addWidget(QLabel("HTTP adapter 配置文件"))
        layout.addWidget(self.http_adapter_path_edit)
        layout.addWidget(QLabel("Profile ID"))
        layout.addWidget(self.profile_id_edit)
        layout.addWidget(QLabel("阶段"))
        layout.addWidget(self.stage_edit)
        layout.addWidget(QLabel("URL"))
        layout.addWidget(self.url_edit)
        layout.addWidget(QLabel("响应映射"))
        layout.addWidget(self.response_mapping_edit)
        layout.addWidget(QLabel("已配置 adapter"))
        layout.addWidget(self.adapter_list)
        self.setLayout(layout)

    def save_adapter_profile(self, store_path: Path) -> None:
        store = AdapterProfileStore(store_path)
        profiles = [profile for profile in store.load() if profile.id != self.profile_id_edit.text()]
        profiles.append(
            ApiAdapterProfile(
                id=self.profile_id_edit.text(),
                stage=self.stage_edit.text(),
                method="POST",
                url=self.url_edit.text(),
                headers={},
                request_template={
                    "prompt": "{{ prompt }}",
                    "text": "{{ segment_text }}",
                    "source_language": "{{ source_language }}",
                    "target_language": "{{ target_language }}",
                    "speaker_id": "{{ speaker_id }}",
                },
                response_mapping=self._parse_response_mapping(),
            )
        )
        store.save(profiles)
        self.load_adapter_profiles(store_path)

    def load_adapter_profiles(self, store_path: Path) -> None:
        self.adapter_list.clear()
        for profile in AdapterProfileStore(store_path).load():
            self.adapter_list.addItem(f"{profile.id} {profile.stage}")

    def browse_local_command_profiles(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "选择本地命令 profiles JSON",
            "",
            "JSON files (*.json);;All files (*)",
        )
        if path:
            self.local_command_profiles_path_edit.setText(path)

    def browse_asr_profile(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "选择 ASR HTTP profile JSON",
            "",
            "JSON files (*.json);;All files (*)",
        )
        if path:
            self.asr_profile_path_edit.setText(path)

    def browse_translation_profile(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "选择翻译 HTTP profile JSON",
            "",
            "JSON files (*.json);;All files (*)",
        )
        if path:
            self.translation_profile_path_edit.setText(path)

    def browse_tts_profile(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "选择 TTS HTTP profile JSON",
            "",
            "JSON files (*.json);;All files (*)",
        )
        if path:
            self.tts_profile_path_edit.setText(path)

    def _parse_response_mapping(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        raw_items = [
            item.strip()
            for item in self.response_mapping_edit.text().replace("\n", ",").split(",")
            if item.strip()
        ]
        for item in raw_items:
            key, separator, value = item.partition("=")
            if not separator:
                raise ValueError(f"响应映射需要 KEY=JSONPATH 格式：{item}")
            mapping[key] = value
        return mapping
