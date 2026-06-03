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
        self.separation_profile_path_edit = QLineEdit()
        self.separation_profile_browse_button = QPushButton("浏览人声分离 profile")
        self.separation_vars_edit = QLineEdit()
        self.asr_profile_path_edit = QLineEdit()
        self.asr_profile_browse_button = QPushButton("浏览 ASR profile")
        self.asr_vars_edit = QLineEdit()
        self.diarization_profile_path_edit = QLineEdit()
        self.diarization_profile_browse_button = QPushButton("浏览说话人分离 profile")
        self.diarization_vars_edit = QLineEdit()
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
        self.optional_response_keys_edit = QLineEdit()
        self.file_upload_fields_edit = QLineEdit()
        self.adapter_list = QListWidget()

        self.local_command_profiles_browse_button.clicked.connect(
            self.browse_local_command_profiles
        )
        self.separation_profile_browse_button.clicked.connect(self.browse_separation_profile)
        self.asr_profile_browse_button.clicked.connect(self.browse_asr_profile)
        self.diarization_profile_browse_button.clicked.connect(self.browse_diarization_profile)
        self.translation_profile_browse_button.clicked.connect(self.browse_translation_profile)
        self.tts_profile_browse_button.clicked.connect(self.browse_tts_profile)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("本地模型路径"))
        layout.addWidget(self.local_model_path_edit)
        layout.addWidget(QLabel("本地命令 profiles JSON"))
        layout.addWidget(self.local_command_profiles_path_edit)
        layout.addWidget(self.local_command_profiles_browse_button)
        layout.addWidget(QLabel("人声分离 HTTP profile JSON"))
        layout.addWidget(self.separation_profile_path_edit)
        layout.addWidget(self.separation_profile_browse_button)
        layout.addWidget(QLabel("人声分离变量 KEY=VALUE"))
        layout.addWidget(self.separation_vars_edit)
        layout.addWidget(QLabel("ASR HTTP profile JSON"))
        layout.addWidget(self.asr_profile_path_edit)
        layout.addWidget(self.asr_profile_browse_button)
        layout.addWidget(QLabel("ASR 变量 KEY=VALUE"))
        layout.addWidget(self.asr_vars_edit)
        layout.addWidget(QLabel("说话人分离 HTTP profile JSON"))
        layout.addWidget(self.diarization_profile_path_edit)
        layout.addWidget(self.diarization_profile_browse_button)
        layout.addWidget(QLabel("说话人分离变量 KEY=VALUE"))
        layout.addWidget(self.diarization_vars_edit)
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
        layout.addWidget(QLabel("\u53ef\u9009\u54cd\u5e94\u5b57\u6bb5\uff08\u9017\u53f7\u5206\u9694\uff09"))
        layout.addWidget(self.optional_response_keys_edit)
        layout.addWidget(QLabel("File upload fields"))
        layout.addWidget(self.file_upload_fields_edit)
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
                optional_response_keys=self._parse_optional_response_keys(),
                file_upload_fields=self._parse_file_upload_fields(),
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

    def browse_separation_profile(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "选择人声分离 HTTP profile JSON",
            "",
            "JSON files (*.json);;All files (*)",
        )
        if path:
            self.separation_profile_path_edit.setText(path)

    def browse_asr_profile(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "选择 ASR HTTP profile JSON",
            "",
            "JSON files (*.json);;All files (*)",
        )
        if path:
            self.asr_profile_path_edit.setText(path)

    def browse_diarization_profile(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "选择说话人分离 HTTP profile JSON",
            "",
            "JSON files (*.json);;All files (*)",
        )
        if path:
            self.diarization_profile_path_edit.setText(path)

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

    def _parse_optional_response_keys(self) -> list[str]:
        return [
            item.strip()
            for item in self.optional_response_keys_edit.text().replace("\n", ",").split(",")
            if item.strip()
        ]

    def _parse_file_upload_fields(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        raw_items = [
            item.strip()
            for item in self.file_upload_fields_edit.text().replace("\n", ",").split(",")
            if item.strip()
        ]
        for item in raw_items:
            key, separator, value = item.partition("=")
            if not separator:
                raise ValueError(f"File upload field needs KEY=VALUE format: {item}")
            mapping[key] = value
        return mapping
