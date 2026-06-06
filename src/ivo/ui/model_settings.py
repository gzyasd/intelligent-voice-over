from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
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
from ivo.environment import collect_optional_model_dependencies, resolve_local_python
from ivo.local_readiness import check_profiles_readiness
from ivo.model_setup import build_model_setup_script
from ivo.pipeline.local_command_preview import LocalCommandPipelineProfiles
from ivo.profile_runtime import infer_local_runtime_root, resolve_local_model_root
from ivo.profile_defaults import default_local_command_profiles_path
from ivo.profile_validation import validate_http_profile, validate_local_command_profiles


class ModelSettings(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.local_model_path_edit = QLineEdit("models")
        self.model_root_hint_label = QLabel(
            "默认模型目录：程序目录下的 models。也可以选择其他磁盘上的模型目录。"
        )
        self.model_root_browse_button = QPushButton("选择模型目录")
        self.setup_script_path_edit = QLineEdit("scripts/setup-local-models.ps1")
        self.write_model_setup_script_button = QPushButton("生成本地模型安装脚本")
        self.refresh_model_diagnostics_button = QPushButton("刷新模型目录检查")
        default_profiles_path = default_local_command_profiles_path()
        self.local_command_profiles_path_edit = QLineEdit(
            str(default_profiles_path) if default_profiles_path is not None else ""
        )
        self.local_command_profiles_path_edit.setPlaceholderText(
            "例如：examples/local_command_profiles.real_gpu_fast_preview.json"
        )
        self.local_command_help_label = QLabel(
            "本地命令配置 JSON 用来告诉程序每个阶段调用哪个本地脚本或模型服务，"
            "例如人声分离、语音识别、说话人识别、翻译、语音合成。"
            "一般保持默认示例即可；只有你换成本机其他模型、脚本路径或参数时才需要修改。"
        )
        self.local_command_help_label.setWordWrap(True)
        self.local_command_profiles_browse_button = QPushButton("选择本地命令配置")
        self.validate_local_profiles_button = QPushButton("校验本地命令配置")
        self.check_local_readiness_button = QPushButton("检查本地模型是否就绪")
        self.validate_http_profiles_button = QPushButton("校验在线 API 配置")
        self.local_profile_summary_list = QListWidget()
        self.model_diagnostics_list = QListWidget()
        self.readiness_results_table = QTableWidget(0, 4)
        self.readiness_results_table.setHorizontalHeaderLabels(
            ["阶段", "服务", "状态", "说明"]
        )
        self.separation_profile_path_edit = QLineEdit()
        self.separation_profile_path_edit.setPlaceholderText(
            "例如：examples/http_separation_profile.example.json"
        )
        self.separation_profile_browse_button = QPushButton("选择人声分离 API 配置")
        self.separation_vars_edit = QLineEdit()
        self.separation_vars_edit.setPlaceholderText("例如：api_key=your-token,model=uvr")
        self.asr_profile_path_edit = QLineEdit()
        self.asr_profile_path_edit.setPlaceholderText("例如：examples/http_asr_profile.example.json")
        self.asr_profile_browse_button = QPushButton("选择语音识别 API 配置")
        self.asr_vars_edit = QLineEdit()
        self.asr_vars_edit.setPlaceholderText("例如：api_key=your-token,language=ja")
        self.diarization_profile_path_edit = QLineEdit()
        self.diarization_profile_path_edit.setPlaceholderText(
            "例如：examples/http_diarization_profile.example.json"
        )
        self.diarization_profile_browse_button = QPushButton("选择说话人识别 API 配置")
        self.diarization_vars_edit = QLineEdit()
        self.diarization_vars_edit.setPlaceholderText("例如：api_key=your-token,min_speakers=1")
        self.translation_profile_path_edit = QLineEdit()
        self.translation_profile_path_edit.setPlaceholderText(
            "例如：examples/http_translation_lm_studio_qwen36_35b.example.json"
        )
        self.translation_profile_browse_button = QPushButton("选择翻译 API 配置")
        self.translation_vars_edit = QLineEdit()
        self.translation_vars_edit.setPlaceholderText("例如：api_key=lm-studio,temperature=0.2")
        self.tts_profile_path_edit = QLineEdit()
        self.tts_profile_path_edit.setPlaceholderText("例如：examples/http_tts_profile.example.json")
        self.tts_profile_browse_button = QPushButton("选择语音合成 API 配置")
        self.tts_vars_edit = QLineEdit()
        self.tts_vars_edit.setPlaceholderText("例如：api_key=your-token,voice=speaker_001")
        self.http_adapter_path_edit = QLineEdit()
        self.http_adapter_path_edit.setPlaceholderText("例如：examples/http_translation_profile.example.json")
        self.profile_id_edit = QLineEdit()
        self.profile_id_edit.setPlaceholderText("例如：lm-studio-qwen-translation")
        self.stage_edit = QLineEdit("translation")
        self.stage_edit.setPlaceholderText("例如：translation / asr / tts / separation / diarization")
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("例如：http://127.0.0.1:1995/v1/chat/completions")
        self.response_mapping_edit = QLineEdit("target_text=$.text")
        self.response_mapping_edit.setPlaceholderText("例如：target_text=$.choices[0].message.content")
        self.optional_response_keys_edit = QLineEdit()
        self.optional_response_keys_edit.setPlaceholderText("例如：style_prompt,duration_ms")
        self.file_upload_fields_edit = QLineEdit()
        self.file_upload_fields_edit.setPlaceholderText("例如：audio=audio_path")
        self.adapter_list = QListWidget()

        self.model_root_browse_button.clicked.connect(self.browse_model_root)
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

        model_form = QFormLayout()
        model_form.addRow("本地模型目录", self.local_model_path_edit)
        model_form.addRow("", self.model_root_browse_button)
        model_form.addRow("", self.model_root_hint_label)
        model_form.addRow("本地命令配置", self.local_command_profiles_path_edit)
        model_form.addRow("", self.local_command_profiles_browse_button)
        model_form.addRow("", self.local_command_help_label)
        model_form.addRow("安装脚本输出", self.setup_script_path_edit)

        layout = QVBoxLayout()
        layout.addLayout(model_form)
        layout.addWidget(self.refresh_model_diagnostics_button)
        layout.addWidget(self.check_local_readiness_button)
        layout.addWidget(self.validate_local_profiles_button)
        layout.addWidget(self.write_model_setup_script_button)
        layout.addWidget(QLabel("本地命令阶段摘要"))
        layout.addWidget(self.local_profile_summary_list)
        layout.addWidget(QLabel("模型目录与依赖检查"))
        layout.addWidget(self.model_diagnostics_list)
        layout.addWidget(QLabel("就绪检查结果"))
        layout.addWidget(self.readiness_results_table)

        self.advanced_group = QGroupBox("高级配置（本地命令 / 在线 API）")
        self.advanced_group.setCheckable(False)
        advanced_layout = QVBoxLayout()
        advanced_help_label = QLabel(
            "只有接入自定义在线 API，或需要覆盖某个本地阶段时才填写这里。"
            "JSON 配置填 profile 文件路径；变量按 KEY=VALUE 填写，多个变量用英文逗号分隔。"
        )
        advanced_help_label.setWordWrap(True)
        advanced_layout.addWidget(advanced_help_label)
        advanced_layout.addWidget(self.validate_http_profiles_button)
        advanced_layout.addWidget(QLabel("人声分离 API 配置 JSON"))
        advanced_layout.addWidget(self.separation_profile_path_edit)
        advanced_layout.addWidget(self.separation_profile_browse_button)
        advanced_layout.addWidget(QLabel("人声分离变量 KEY=VALUE"))
        advanced_layout.addWidget(self.separation_vars_edit)
        advanced_layout.addWidget(QLabel("语音识别 API 配置 JSON"))
        advanced_layout.addWidget(self.asr_profile_path_edit)
        advanced_layout.addWidget(self.asr_profile_browse_button)
        advanced_layout.addWidget(QLabel("语音识别变量 KEY=VALUE"))
        advanced_layout.addWidget(self.asr_vars_edit)
        advanced_layout.addWidget(QLabel("说话人识别 API 配置 JSON"))
        advanced_layout.addWidget(self.diarization_profile_path_edit)
        advanced_layout.addWidget(self.diarization_profile_browse_button)
        advanced_layout.addWidget(QLabel("说话人识别变量 KEY=VALUE"))
        advanced_layout.addWidget(self.diarization_vars_edit)
        advanced_layout.addWidget(QLabel("翻译 API 配置 JSON"))
        advanced_layout.addWidget(self.translation_profile_path_edit)
        advanced_layout.addWidget(self.translation_profile_browse_button)
        advanced_layout.addWidget(QLabel("翻译变量 KEY=VALUE"))
        advanced_layout.addWidget(self.translation_vars_edit)
        advanced_layout.addWidget(QLabel("语音合成 API 配置 JSON"))
        advanced_layout.addWidget(self.tts_profile_path_edit)
        advanced_layout.addWidget(self.tts_profile_browse_button)
        advanced_layout.addWidget(QLabel("语音合成变量 KEY=VALUE"))
        advanced_layout.addWidget(self.tts_vars_edit)
        advanced_layout.addWidget(QLabel("HTTP adapter 配置文件"))
        advanced_layout.addWidget(self.http_adapter_path_edit)
        advanced_layout.addWidget(QLabel("配置 ID"))
        advanced_layout.addWidget(self.profile_id_edit)
        advanced_layout.addWidget(QLabel("阶段"))
        advanced_layout.addWidget(self.stage_edit)
        advanced_layout.addWidget(QLabel("URL"))
        advanced_layout.addWidget(self.url_edit)
        advanced_layout.addWidget(QLabel("响应映射"))
        advanced_layout.addWidget(self.response_mapping_edit)
        advanced_layout.addWidget(QLabel("可选响应字段（逗号分隔）"))
        advanced_layout.addWidget(self.optional_response_keys_edit)
        advanced_layout.addWidget(QLabel("文件上传字段"))
        advanced_layout.addWidget(self.file_upload_fields_edit)
        advanced_layout.addWidget(QLabel("已配置 adapter"))
        advanced_layout.addWidget(self.adapter_list)
        self.advanced_group.setLayout(advanced_layout)
        layout.addWidget(self.advanced_group)
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

    def load_model_diagnostics(
        self,
        model_root: Path,
        *,
        python_executable: Path | None = None,
    ) -> None:
        self.model_diagnostics_list.clear()
        for dependency in collect_optional_model_dependencies(
            model_root,
            python_executable=python_executable,
        ):
            package_status = "已安装" if dependency.installed else "未安装"
            model_status = "已找到" if dependency.model_dir_exists else "未找到"
            env_status = ""
            if dependency.required_env_var is not None:
                env_value = "已设置" if dependency.env_var_set else "未设置"
                env_status = f"；环境变量：{env_value}"
            self.model_diagnostics_list.addItem(
                f"{dependency.stage} / {dependency.name}：依赖包：{package_status}；"
                f"模型目录：{model_status}{env_status}"
            )

    def refresh_model_diagnostics(self) -> None:
        raw_path = self.local_model_path_edit.text().strip()
        model_root = Path(raw_path) if raw_path else Path("models")
        runtime_root = self._infer_current_runtime_root(model_root)
        self.load_model_diagnostics(
            resolve_local_model_root(model_root, runtime_root),
            python_executable=resolve_local_python(runtime_root),
        )

    def browse_model_root(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "选择本地模型目录",
            self.local_model_path_edit.text().strip() or "models",
        )
        if path:
            self.local_model_path_edit.setText(path)

    def write_model_setup_script(self) -> Path:
        raw_model_root = self.local_model_path_edit.text().strip()
        raw_output = self.setup_script_path_edit.text().strip()
        model_root = Path(raw_model_root) if raw_model_root else Path("models")
        output_path = Path(raw_output) if raw_output else Path("scripts") / "setup-local-models.ps1"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(build_model_setup_script(model_root), encoding="utf-8")
        self.model_diagnostics_list.addItem(f"安装脚本已生成：{output_path}")
        return output_path

    def validate_local_command_profiles(self) -> None:
        raw_path = self.local_command_profiles_path_edit.text().strip()
        self.local_profile_summary_list.clear()
        if not raw_path:
            self.local_profile_summary_list.addItem("校验：失败")
            self.local_profile_summary_list.addItem("错误：本地命令配置路径为空")
            return
        try:
            profiles = LocalCommandPipelineProfiles.model_validate(
                json.loads(Path(raw_path).read_text(encoding="utf-8"))
            )
        except (OSError, ValueError) as exc:
            self.local_profile_summary_list.addItem("校验：失败")
            self.local_profile_summary_list.addItem(f"错误：{exc}")
            return
        report = validate_local_command_profiles(profiles)
        self.local_profile_summary_list.addItem("校验：通过" if report.ok else "校验：失败")
        for error in report.errors:
            self.local_profile_summary_list.addItem(f"错误：{error}")

    def check_local_readiness(self) -> None:
        raw_profiles_path = self.local_command_profiles_path_edit.text().strip()
        raw_model_root = self.local_model_path_edit.text().strip()
        model_root = Path(raw_model_root) if raw_model_root else Path("models")
        self.model_diagnostics_list.clear()
        if not raw_profiles_path:
            self.model_diagnostics_list.addItem("就绪检查：失败")
            self.model_diagnostics_list.addItem("缺失：本地命令配置路径为空")
            return
        try:
            report = check_profiles_readiness(Path(raw_profiles_path), models_dir=model_root)
        except (OSError, ValueError) as exc:
            self.model_diagnostics_list.addItem("就绪检查：失败")
            self.model_diagnostics_list.addItem(f"缺失：{exc}")
            return
        self.model_diagnostics_list.addItem("就绪检查：通过" if report.ok else "就绪检查：失败")
        for profile in report.checked_profiles:
            self.model_diagnostics_list.addItem(f"已检查：{profile}")
        for profile in report.skipped_dry_run_profiles:
            self.model_diagnostics_list.addItem(f"跳过 dry-run：{profile}")
        for missing in report.missing:
            self.model_diagnostics_list.addItem(f"缺失：{missing}")
        self.show_readiness_results([result.model_dump() for result in report.ui_results])

    def _infer_current_runtime_root(self, model_root: Path) -> Path:
        raw_profiles_path = self.local_command_profiles_path_edit.text().strip()
        profiles_path = Path(raw_profiles_path) if raw_profiles_path else default_local_command_profiles_path()
        if profiles_path is not None:
            return infer_local_runtime_root(profiles_path, models_dir=model_root)
        return Path.cwd()

    def show_readiness_results(self, results: list[dict[str, object]]) -> None:
        self.readiness_results_table.setRowCount(len(results))
        for row, result in enumerate(results):
            for column, key in enumerate(("stage", "provider", "status", "message")):
                self.readiness_results_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(_localize_readiness_value(key, result.get(key, ""))),
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
                self.model_diagnostics_list.addItem(f"在线 API 校验：{stage}：失败")
                self.model_diagnostics_list.addItem(f"错误：{exc}")
                continue
            self.model_diagnostics_list.addItem(
                f"在线 API 校验：{stage}：{'通过' if report.ok else '失败'}"
            )
            for error in report.errors:
                self.model_diagnostics_list.addItem(f"错误：{error}")
        if not found_profile:
            self.model_diagnostics_list.addItem("在线 API 校验：已跳过")

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
            "JSON 文件 (*.json);;所有文件 (*)",
        )
        if path:
            self.local_command_profiles_path_edit.setText(path)
            self.load_local_command_profile_summary(Path(path))

    def browse_separation_profile(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "选择人声分离 HTTP profile JSON",
            "",
            "JSON 文件 (*.json);;所有文件 (*)",
        )
        if path:
            self.separation_profile_path_edit.setText(path)

    def browse_asr_profile(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "选择 ASR HTTP profile JSON",
            "",
            "JSON 文件 (*.json);;所有文件 (*)",
        )
        if path:
            self.asr_profile_path_edit.setText(path)

    def browse_diarization_profile(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "选择说话人分离 HTTP profile JSON",
            "",
            "JSON 文件 (*.json);;所有文件 (*)",
        )
        if path:
            self.diarization_profile_path_edit.setText(path)

    def browse_translation_profile(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "选择翻译 HTTP profile JSON",
            "",
            "JSON 文件 (*.json);;所有文件 (*)",
        )
        if path:
            self.translation_profile_path_edit.setText(path)

    def browse_tts_profile(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "选择 TTS HTTP profile JSON",
            "",
            "JSON 文件 (*.json);;所有文件 (*)",
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
                raise ValueError(f"文件上传字段需要 KEY=VALUE 格式：{item}")
            mapping[key] = value
        return mapping


def _localize_readiness_value(key: str, value: object) -> str:
    raw = str(value)
    if key == "status":
        return {
            "ok": "通过",
            "missing": "缺失",
            "failed": "失败",
            "skipped": "已跳过",
        }.get(raw, raw)
    return raw


ModelSettingsPanel = ModelSettings
