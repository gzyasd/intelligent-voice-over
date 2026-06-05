from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ivo.adapters.http import ApiAdapterProfile
from ivo.adapters.profiles import AdapterProfileStore
from ivo.environment import collect_optional_model_dependencies
from ivo.local_readiness import build_local_readiness_report
from ivo.model_setup import build_model_setup_script
from ivo.pipeline.local_command_preview import LocalCommandPipelineProfiles
from ivo.profile_defaults import default_local_command_profiles_path
from ivo.profile_validation import validate_http_profile, validate_local_command_profiles


class ModelSettings(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.local_model_path_edit = QLineEdit()
        self.setup_script_path_edit = QLineEdit("scripts/setup-local-models.ps1")
        self.write_model_setup_script_button = QPushButton("生成本地模型安装脚本")
        self.refresh_model_diagnostics_button = QPushButton("刷新本地模型诊断")
        default_profiles_path = default_local_command_profiles_path()
        self.local_command_profiles_path_edit = QLineEdit(
            str(default_profiles_path) if default_profiles_path is not None else ""
        )
        self.local_command_profiles_browse_button = QPushButton("浏览本地命令 profile")
        self.validate_local_profiles_button = QPushButton("校验本地命令 profile")
        self.check_local_readiness_button = QPushButton("Check local model readiness")
        self.validate_http_profiles_button = QPushButton("Validate HTTP profiles")
        self.local_profile_summary_list = QListWidget()
        self.model_diagnostics_list = QListWidget()
        self.readiness_results_table = QTableWidget(0, 4)
        self.readiness_results_table.setHorizontalHeaderLabels(
            ["stage", "provider", "status", "message"]
        )
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
        self.validate_local_profiles_button.clicked.connect(self.validate_local_command_profiles)
        self.check_local_readiness_button.clicked.connect(self.check_local_readiness)
        self.validate_http_profiles_button.clicked.connect(self.validate_http_profiles)
        self.separation_profile_browse_button.clicked.connect(self.browse_separation_profile)
        self.asr_profile_browse_button.clicked.connect(self.browse_asr_profile)
        self.diarization_profile_browse_button.clicked.connect(self.browse_diarization_profile)
        self.translation_profile_browse_button.clicked.connect(self.browse_translation_profile)
        self.tts_profile_browse_button.clicked.connect(self.browse_tts_profile)
        self.refresh_model_diagnostics_button.clicked.connect(self.refresh_model_diagnostics)
        self.write_model_setup_script_button.clicked.connect(self.write_model_setup_script)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("本地模型路径"))
        layout.addWidget(self.local_model_path_edit)
        layout.addWidget(self.refresh_model_diagnostics_button)
        layout.addWidget(QLabel("本地模型安装脚本输出"))
        layout.addWidget(self.setup_script_path_edit)
        layout.addWidget(self.write_model_setup_script_button)
        layout.addWidget(QLabel("本地命令 profiles JSON"))
        layout.addWidget(self.local_command_profiles_path_edit)
        layout.addWidget(self.local_command_profiles_browse_button)
        layout.addWidget(self.validate_local_profiles_button)
        layout.addWidget(self.check_local_readiness_button)
        layout.addWidget(self.validate_http_profiles_button)
        layout.addWidget(QLabel("本地命令 profile 阶段摘要"))
        layout.addWidget(self.local_profile_summary_list)
        layout.addWidget(QLabel("本地模型环境诊断"))
        layout.addWidget(self.model_diagnostics_list)
        layout.addWidget(QLabel("Readiness results"))
        layout.addWidget(self.readiness_results_table)
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

    def load_local_command_profile_summary(self, profiles_path: Path) -> None:
        self.local_profile_summary_list.clear()
        try:
            profiles = LocalCommandPipelineProfiles.model_validate(
                json.loads(profiles_path.read_text(encoding="utf-8"))
            )
        except (OSError, ValueError) as exc:
            self.local_profile_summary_list.addItem(f"profile 读取失败: {exc}")
            return

        self.local_profile_summary_list.addItem(
            self._stage_summary("separation", profiles.separation.id, self.separation_profile_path_edit)
        )
        self.local_profile_summary_list.addItem(
            self._stage_summary("asr", profiles.asr.id, self.asr_profile_path_edit)
        )
        if profiles.diarization is not None:
            self.local_profile_summary_list.addItem(
                self._stage_summary(
                    "diarization",
                    profiles.diarization.id,
                    self.diarization_profile_path_edit,
                )
            )
        self.local_profile_summary_list.addItem(
            self._stage_summary("translation", "target-text overrides", self.translation_profile_path_edit)
        )
        self.local_profile_summary_list.addItem(
            self._stage_summary("tts", profiles.tts.id, self.tts_profile_path_edit)
        )

    def load_model_diagnostics(self, model_root: Path) -> None:
        self.model_diagnostics_list.clear()
        for dependency in collect_optional_model_dependencies(model_root):
            package_status = "installed" if dependency.installed else "missing"
            model_status = "found" if dependency.model_dir_exists else "missing"
            env_status = ""
            if dependency.required_env_var is not None:
                env_value = "set" if dependency.env_var_set else "missing"
                env_status = f"; env: {env_value}"
            self.model_diagnostics_list.addItem(
                f"{dependency.stage} / {dependency.name}: package: {package_status}; "
                f"model dir: {model_status}{env_status}"
            )

    def refresh_model_diagnostics(self) -> None:
        raw_path = self.local_model_path_edit.text().strip()
        self.load_model_diagnostics(Path(raw_path) if raw_path else Path("models"))

    def write_model_setup_script(self) -> Path:
        raw_model_root = self.local_model_path_edit.text().strip()
        raw_output = self.setup_script_path_edit.text().strip()
        model_root = Path(raw_model_root) if raw_model_root else Path("models")
        output_path = Path(raw_output) if raw_output else Path("scripts") / "setup-local-models.ps1"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(build_model_setup_script(model_root), encoding="utf-8")
        self.model_diagnostics_list.addItem(f"setup script written: {output_path}")
        return output_path

    def validate_local_command_profiles(self) -> None:
        raw_path = self.local_command_profiles_path_edit.text().strip()
        self.local_profile_summary_list.clear()
        if not raw_path:
            self.local_profile_summary_list.addItem("validation: failed")
            self.local_profile_summary_list.addItem("error: local command profiles path is empty")
            return
        try:
            profiles = LocalCommandPipelineProfiles.model_validate(
                json.loads(Path(raw_path).read_text(encoding="utf-8"))
            )
        except (OSError, ValueError) as exc:
            self.local_profile_summary_list.addItem("validation: failed")
            self.local_profile_summary_list.addItem(f"error: {exc}")
            return
        report = validate_local_command_profiles(profiles)
        self.local_profile_summary_list.addItem("validation: ok" if report.ok else "validation: failed")
        for error in report.errors:
            self.local_profile_summary_list.addItem(f"error: {error}")

    def check_local_readiness(self) -> None:
        raw_profiles_path = self.local_command_profiles_path_edit.text().strip()
        raw_model_root = self.local_model_path_edit.text().strip()
        model_root = Path(raw_model_root) if raw_model_root else Path("models")
        self.model_diagnostics_list.clear()
        if not raw_profiles_path:
            self.model_diagnostics_list.addItem("readiness: failed")
            self.model_diagnostics_list.addItem("missing: local command profiles path is empty")
            return
        try:
            profiles = LocalCommandPipelineProfiles.model_validate(
                json.loads(Path(raw_profiles_path).read_text(encoding="utf-8"))
            )
        except (OSError, ValueError) as exc:
            self.model_diagnostics_list.addItem("readiness: failed")
            self.model_diagnostics_list.addItem(f"missing: {exc}")
            return
        report = build_local_readiness_report(
            profiles,
            dependencies=collect_optional_model_dependencies(model_root),
        )
        self.model_diagnostics_list.addItem("readiness: ok" if report.ok else "readiness: failed")
        for profile in report.checked_profiles:
            self.model_diagnostics_list.addItem(f"checked: {profile}")
        for profile in report.skipped_dry_run_profiles:
            self.model_diagnostics_list.addItem(f"skipped dry-run: {profile}")
        for missing in report.missing:
            self.model_diagnostics_list.addItem(f"missing: {missing}")
        self.show_readiness_results([result.model_dump() for result in report.ui_results])

    def show_readiness_results(self, results: list[dict[str, object]]) -> None:
        self.readiness_results_table.setRowCount(len(results))
        for row, result in enumerate(results):
            for column, key in enumerate(("stage", "provider", "status", "message")):
                self.readiness_results_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(str(result.get(key, ""))),
                )

    def readiness_summary_text(self) -> str:
        lines: list[str] = []
        for row in range(self.readiness_results_table.rowCount()):
            values: list[str] = []
            for column in range(self.readiness_results_table.columnCount()):
                item = self.readiness_results_table.item(row, column)
                values.append(item.text() if item is not None else "")
            lines.append(" | ".join(values))
        return "\n".join(lines)

    def validate_http_profiles(self) -> None:
        self.model_diagnostics_list.clear()
        found_profile = False
        for stage, path_edit in (
            ("separation", self.separation_profile_path_edit),
            ("asr", self.asr_profile_path_edit),
            ("diarization", self.diarization_profile_path_edit),
            ("translation", self.translation_profile_path_edit),
            ("tts", self.tts_profile_path_edit),
        ):
            raw_path = path_edit.text().strip()
            if not raw_path:
                continue
            found_profile = True
            try:
                profile = ApiAdapterProfile.model_validate(
                    json.loads(Path(raw_path).read_text(encoding="utf-8"))
                )
                report = validate_http_profile(profile)
            except (OSError, ValueError) as exc:
                self.model_diagnostics_list.addItem(f"http validation: {stage}: failed")
                self.model_diagnostics_list.addItem(f"error: {exc}")
                continue
            self.model_diagnostics_list.addItem(
                f"http validation: {stage}: {'ok' if report.ok else 'failed'}"
            )
            for error in report.errors:
                self.model_diagnostics_list.addItem(f"error: {error}")
        if not found_profile:
            self.model_diagnostics_list.addItem("http validation: skipped")

    def _stage_summary(self, stage: str, local_id: str, http_path_edit: QLineEdit) -> str:
        raw_http_path = http_path_edit.text().strip()
        if raw_http_path:
            return f"{stage}: http / {self._http_profile_label(Path(raw_http_path))}"
        if stage == "translation":
            return f"{stage}: mock / {local_id}"
        return f"{stage}: local / {local_id}"

    def _http_profile_label(self, profile_path: Path) -> str:
        try:
            profile = ApiAdapterProfile.model_validate(
                json.loads(profile_path.read_text(encoding="utf-8"))
            )
        except (OSError, ValueError):
            return profile_path.name
        return profile.id

    def browse_local_command_profiles(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "选择本地命令 profiles JSON",
            "",
            "JSON files (*.json);;All files (*)",
        )
        if path:
            self.local_command_profiles_path_edit.setText(path)
            self.load_local_command_profile_summary(Path(path))

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


ModelSettingsPanel = ModelSettings
