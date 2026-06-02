from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ivo.compliance.confirmation import ExportConfirmation
from ivo.adapters.http import ApiAdapterProfile
from ivo.compliance.metadata import build_ai_dubbing_metadata
from ivo.core.project import DubbingProject
from ivo.core.timeline import SourceLanguage
from ivo.pipeline.mix_export import ExportRequest, SegmentAudio, export_dubbed_video
from ivo.pipeline.local_command_preview import (
    LocalCommandPipelineProfiles,
    LocalCommandPreviewResult,
    run_local_command_preview,
)
from ivo.pipeline.mock_pipeline import MockPipelineResult, run_mock_dubbing_pipeline
from ivo.pipeline.synthesize import (
    HttpTtsAdapter,
    LocalCommandTtsAdapter,
    SynthesisResult,
    TtsAdapter,
    synthesize_segment,
)
from ivo.pipeline.translate import HttpTranslationAdapter
from ivo.ui.export_dialog import ExportDialog
from ivo.ui.model_settings import ModelSettings
from ivo.ui.project_wizard import ProjectWizard
from ivo.ui.timeline_editor import TimelineEditor
from ivo.ui.workers import PipelineWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("\u667a\u80fd\u89c6\u9891\u914d\u97f3")

        self.create_project_button = QPushButton("\u65b0\u5efa\u9879\u76ee")
        self.open_project_button = QPushButton("\u6253\u5f00\u9879\u76ee")
        self.local_preview_button = QPushButton("\u672c\u5730\u547d\u4ee4\u9884\u89c8")
        self.export_button = QPushButton("\u6700\u7ec8\u5bfc\u51fa")
        self.progress_label = QLabel("\u5c1a\u672a\u5f00\u59cb")
        self.timeline_editor = TimelineEditor()
        self.model_settings = ModelSettings()
        self.current_project: DubbingProject | None = None
        self.source_video_path: Path | None = None
        self.local_preview_worker: PipelineWorker | None = None
        self.segment_regeneration_worker: PipelineWorker | None = None
        self.regenerating_segment_id: str | None = None
        self.final_export_worker: PipelineWorker | None = None
        self.create_project_button.clicked.connect(self.open_project_wizard)
        self.open_project_button.clicked.connect(self.open_existing_project)
        self.local_preview_button.clicked.connect(lambda: self.start_local_preview_background())
        self.export_button.clicked.connect(self.open_export_dialog)
        self.timeline_editor.regenerate_requested.connect(self.start_segment_regeneration_background)

        tabs = QTabWidget()
        tabs.addTab(self.timeline_editor, "\u65f6\u95f4\u7ebf")
        tabs.addTab(self.model_settings, "\u6a21\u578b\u8bbe\u7f6e")

        root = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.create_project_button)
        layout.addWidget(self.open_project_button)
        layout.addWidget(self.local_preview_button)
        layout.addWidget(self.export_button)
        layout.addWidget(self.progress_label)
        layout.addWidget(tabs)
        root.setLayout(layout)
        self.setCentralWidget(root)
        self.resize(1120, 720)

    def create_project_from_inputs(
        self,
        *,
        project_name: str,
        source_video: Path,
        output_dir: Path,
        source_language: SourceLanguage,
    ) -> DubbingProject:
        project_path = output_dir / f"{project_name}.ivoproj"
        project = DubbingProject.create(
            project_path,
            name=project_name,
            source_language=source_language,
            target_language="zh",
            source_video=source_video,
        )
        self.current_project = project
        self.source_video_path = source_video
        self.progress_label.setText("\u9879\u76ee\u5df2\u521b\u5efa")
        self.timeline_editor.set_project(project)
        return project

    def create_project_from_wizard(self, wizard: ProjectWizard) -> DubbingProject:
        values = wizard.values()
        return self.create_project_from_inputs(
            project_name=values.project_name,
            source_video=values.source_video,
            output_dir=values.output_dir,
            source_language=values.source_language,
        )

    def open_project_wizard(self) -> DubbingProject | None:
        wizard = ProjectWizard(self)
        if wizard.exec() != ProjectWizard.DialogCode.Accepted:
            return None
        if not wizard.is_valid():
            QMessageBox.warning(
                self,
                "\u65b0\u5efa\u9879\u76ee\u5931\u8d25",
                "\u8bf7\u586b\u5199\u9879\u76ee\u540d\u79f0\u3001\u6e90\u89c6\u9891\u548c\u8f93\u51fa\u76ee\u5f55\u3002",
            )
            return None
        return self.create_project_from_wizard(wizard)

    def open_existing_project(self) -> DubbingProject | None:
        raw_path = QFileDialog.getExistingDirectory(
            self,
            "\u6253\u5f00 .ivoproj \u9879\u76ee\u76ee\u5f55",
            "",
        )
        if not raw_path:
            return None

        project_path = Path(raw_path)
        try:
            project = DubbingProject.load(project_path)
        except (OSError, ValueError, KeyError) as exc:
            QMessageBox.warning(
                self,
                "\u6253\u5f00\u9879\u76ee\u5931\u8d25",
                f"{project_path}: {exc}",
            )
            return None

        self.current_project = project
        self.source_video_path = project.source_video_path
        self.timeline_editor.set_project(project)
        self.progress_label.setText("\u9879\u76ee\u5df2\u6253\u5f00")
        return project

    def run_mock_preview(self) -> MockPipelineResult:
        if self.current_project is None:
            raise RuntimeError("\u8bf7\u5148\u521b\u5efa\u6216\u6253\u5f00\u9879\u76ee")
        if self.source_video_path is None:
            raise RuntimeError("\u8bf7\u5148\u9009\u62e9\u6e90\u89c6\u9891")

        self.progress_label.setText("\u6b63\u5728\u751f\u6210 mock \u9884\u89c8")
        result = run_mock_dubbing_pipeline(
            self.current_project,
            source_video=self.source_video_path,
        )
        self.timeline_editor.set_project(self.current_project)
        self.progress_label.setText("mock \u9884\u89c8\u5df2\u5b8c\u6210")
        return result

    def run_local_preview(self) -> LocalCommandPreviewResult:
        self.progress_label.setText("\u6b63\u5728\u751f\u6210\u672c\u5730\u547d\u4ee4\u9884\u89c8")
        result = self._execute_local_preview()
        self._refresh_after_local_preview()
        return result

    def create_local_preview_worker(self) -> PipelineWorker:
        self.progress_label.setText("\u6b63\u5728\u751f\u6210\u672c\u5730\u547d\u4ee4\u9884\u89c8")
        self.local_preview_button.setEnabled(False)
        worker = PipelineWorker(self._execute_local_preview)
        worker.succeeded.connect(self.handle_local_preview_succeeded)
        worker.failed.connect(self.handle_local_preview_failed)
        self.local_preview_worker = worker
        return worker

    def start_local_preview_background(self) -> PipelineWorker:
        worker = self.create_local_preview_worker()
        worker.start()
        return worker

    def handle_local_preview_succeeded(self) -> None:
        self._refresh_after_local_preview()
        self.local_preview_button.setEnabled(True)

    def handle_local_preview_failed(self, message: str) -> None:
        self.progress_label.setText(f"\u672c\u5730\u547d\u4ee4\u9884\u89c8\u5931\u8d25: {message}")
        self.local_preview_button.setEnabled(True)
        QMessageBox.warning(self, "\u672c\u5730\u547d\u4ee4\u9884\u89c8\u5931\u8d25", message)

    def run_final_export(self, dialog: ExportDialog) -> Path:
        request, confirmation = self._build_export_request(dialog)
        output = export_dubbed_video(request, confirmation)
        self.progress_label.setText("\u6700\u7ec8\u5bfc\u51fa\u5df2\u5b8c\u6210")
        return output

    def create_final_export_worker(self, dialog: ExportDialog) -> PipelineWorker:
        request, confirmation = self._build_export_request(dialog)
        self.progress_label.setText("\u6b63\u5728\u6700\u7ec8\u5bfc\u51fa")
        self.export_button.setEnabled(False)
        worker = PipelineWorker(lambda: export_dubbed_video(request, confirmation))
        worker.succeeded.connect(self.handle_final_export_succeeded)
        worker.failed.connect(self.handle_final_export_failed)
        self.final_export_worker = worker
        return worker

    def start_final_export_background(self, dialog: ExportDialog) -> PipelineWorker:
        worker = self.create_final_export_worker(dialog)
        worker.start()
        return worker

    def handle_final_export_succeeded(self) -> None:
        self.export_button.setEnabled(True)
        self.progress_label.setText("\u6700\u7ec8\u5bfc\u51fa\u5df2\u5b8c\u6210")

    def handle_final_export_failed(self, message: str) -> None:
        self.export_button.setEnabled(True)
        self.progress_label.setText(f"\u6700\u7ec8\u5bfc\u51fa\u5931\u8d25: {message}")
        QMessageBox.warning(self, "\u6700\u7ec8\u5bfc\u51fa\u5931\u8d25", message)

    def _build_export_request(self, dialog: ExportDialog) -> tuple[ExportRequest, ExportConfirmation]:
        if self.current_project is None:
            raise RuntimeError("\u8bf7\u5148\u521b\u5efa\u6216\u6253\u5f00\u9879\u76ee")
        if self.source_video_path is None:
            raise RuntimeError("\u8bf7\u5148\u9009\u62e9\u6e90\u89c6\u9891")
        if not dialog.output_path_edit.text().strip():
            raise ValueError("Export output path is required.")

        watermark_options = dialog.watermark_options()
        request = ExportRequest(
            source_video=self.source_video_path,
            background_audio=self.current_project.path / "work" / "background.wav",
            segment_audio=self._collect_rendered_segment_audio(),
            output_path=dialog.output_path(),
            metadata=build_ai_dubbing_metadata(
                source_language=self.current_project.source_language,
                target_language=self.current_project.target_language,
            ),
            watermark_text=watermark_options.text if watermark_options.enabled else None,
        )
        return request, dialog.confirmation()

    def open_export_dialog(self) -> PipelineWorker | None:
        dialog = ExportDialog(self)
        if dialog.exec() != ExportDialog.DialogCode.Accepted:
            return None
        if not dialog.can_export():
            QMessageBox.warning(
                self,
                "\u6700\u7ec8\u5bfc\u51fa\u5931\u8d25",
                "\u8bf7\u586b\u5199\u5bfc\u51fa\u8def\u5f84\u5e76\u786e\u8ba4\u7d20\u6750\u5904\u7406\u6743\u5229\u3002",
            )
            return None
        try:
            return self.start_final_export_background(dialog)
        except Exception as exc:
            self.progress_label.setText(f"\u6700\u7ec8\u5bfc\u51fa\u5931\u8d25: {exc}")
            QMessageBox.warning(self, "\u6700\u7ec8\u5bfc\u51fa\u5931\u8d25", str(exc))
            return None

    def regenerate_timeline_segment(self, segment_id: str) -> SynthesisResult | None:
        try:
            self._save_visible_segment_row(segment_id)
            result = self._execute_segment_regeneration(segment_id)
        except Exception as exc:
            self.progress_label.setText(f"\u7247\u6bb5\u91cd\u751f\u6210\u5931\u8d25: {exc}")
            QMessageBox.warning(self, "\u7247\u6bb5\u91cd\u751f\u6210\u5931\u8d25", str(exc))
            return None

        self._refresh_after_segment_regeneration(segment_id)
        return result

    def create_segment_regeneration_worker(self, segment_id: str) -> PipelineWorker:
        self._save_visible_segment_row(segment_id)
        self.regenerating_segment_id = segment_id
        self.progress_label.setText(f"\u6b63\u5728\u91cd\u751f\u6210\u7247\u6bb5: {segment_id}")
        self._set_timeline_regeneration_enabled(False)
        worker = PipelineWorker(lambda: self._execute_segment_regeneration(segment_id))
        worker.succeeded.connect(self.handle_segment_regeneration_succeeded)
        worker.failed.connect(self.handle_segment_regeneration_failed)
        self.segment_regeneration_worker = worker
        return worker

    def start_segment_regeneration_background(self, segment_id: str) -> PipelineWorker:
        worker = self.create_segment_regeneration_worker(segment_id)
        worker.start()
        return worker

    def handle_segment_regeneration_succeeded(self) -> None:
        segment_id = self.regenerating_segment_id or ""
        self._refresh_after_segment_regeneration(segment_id)
        self._set_timeline_regeneration_enabled(True)
        self.regenerating_segment_id = None

    def handle_segment_regeneration_failed(self, message: str) -> None:
        self.progress_label.setText(f"\u7247\u6bb5\u91cd\u751f\u6210\u5931\u8d25: {message}")
        self._set_timeline_regeneration_enabled(True)
        self.regenerating_segment_id = None
        QMessageBox.warning(self, "\u7247\u6bb5\u91cd\u751f\u6210\u5931\u8d25", message)

    def _collect_rendered_segment_audio(self) -> list[SegmentAudio]:
        if self.current_project is None:
            return []

        generated_dir = self.current_project.path / "work" / "generated_segments"
        segment_audio: list[SegmentAudio] = []
        for segment in self.current_project.timeline.list_segments():
            audio_path = generated_dir / f"{segment.id}.wav"
            if segment.status == "rendered" and audio_path.is_file():
                segment_audio.append(SegmentAudio(path=audio_path, start_ms=segment.start_ms))
        return segment_audio

    def _execute_local_preview(self) -> LocalCommandPreviewResult:
        if self.current_project is None:
            raise RuntimeError("\u8bf7\u5148\u521b\u5efa\u6216\u6253\u5f00\u9879\u76ee")
        if self.source_video_path is None:
            raise RuntimeError("\u8bf7\u5148\u9009\u62e9\u6e90\u89c6\u9891")

        return run_local_command_preview(
            self.current_project,
            source_video=self.source_video_path,
            profiles=self._load_local_command_profiles(),
            translation_adapter=self._build_translation_adapter(),
            tts_adapter=self._build_http_tts_adapter(),
        )

    def _refresh_after_local_preview(self) -> None:
        if self.current_project is not None:
            self.timeline_editor.set_project(self.current_project)
        self.progress_label.setText("\u672c\u5730\u547d\u4ee4\u9884\u89c8\u5df2\u5b8c\u6210")

    def _execute_segment_regeneration(self, segment_id: str) -> SynthesisResult:
        if self.current_project is None:
            raise RuntimeError("\u8bf7\u5148\u521b\u5efa\u6216\u6253\u5f00\u9879\u76ee")

        segment = self.current_project.timeline.get_segment(segment_id)
        adapter = self._build_regeneration_tts_adapter()
        return synthesize_segment(self.current_project, segment, adapter)

    def _refresh_after_segment_regeneration(self, segment_id: str) -> None:
        if self.current_project is not None:
            self.timeline_editor.set_project(self.current_project)
        self.progress_label.setText(f"\u7247\u6bb5\u5df2\u91cd\u751f\u6210: {segment_id}")

    def _save_visible_segment_row(self, segment_id: str) -> None:
        for row in range(self.timeline_editor.table.rowCount()):
            item = self.timeline_editor.table.item(row, self.timeline_editor.COLUMN_ID)
            if item is not None and item.text().strip() == segment_id:
                self.timeline_editor.save_row(row)
                return

    def _set_timeline_regeneration_enabled(self, enabled: bool) -> None:
        for button in self.timeline_editor.regenerate_buttons:
            button.setEnabled(enabled)

    def _load_local_command_profiles(self) -> LocalCommandPipelineProfiles:
        raw_path = self.model_settings.local_command_profiles_path_edit.text().strip()
        if not raw_path:
            raise ValueError("\u8bf7\u5148\u9009\u62e9\u672c\u5730\u547d\u4ee4 profiles JSON")

        profiles_path = Path(raw_path)
        if not profiles_path.is_file():
            raise FileNotFoundError(profiles_path)

        return LocalCommandPipelineProfiles.model_validate(
            json.loads(profiles_path.read_text(encoding="utf-8"))
        )

    def _build_translation_adapter(self) -> HttpTranslationAdapter | None:
        if self.current_project is None:
            return None

        raw_path = self.model_settings.translation_profile_path_edit.text().strip()
        if not raw_path:
            return None

        profile_path = Path(raw_path)
        if not profile_path.is_file():
            raise FileNotFoundError(profile_path)

        return HttpTranslationAdapter(
            ApiAdapterProfile.model_validate(json.loads(profile_path.read_text(encoding="utf-8"))),
            project_path=self.current_project.path,
            target_language=self.current_project.target_language,
            extra=_parse_key_value_text(self.model_settings.translation_vars_edit.text()),
        )

    def _build_regeneration_tts_adapter(self) -> TtsAdapter:
        http_adapter = self._build_http_tts_adapter()
        if http_adapter is not None:
            return http_adapter
        return LocalCommandTtsAdapter(self._load_local_command_profiles().tts)

    def _build_http_tts_adapter(self) -> HttpTtsAdapter | None:
        if self.current_project is None:
            return None

        raw_path = self.model_settings.tts_profile_path_edit.text().strip()
        if not raw_path:
            return None

        profile_path = Path(raw_path)
        if not profile_path.is_file():
            raise FileNotFoundError(profile_path)

        return HttpTtsAdapter(
            ApiAdapterProfile.model_validate(json.loads(profile_path.read_text(encoding="utf-8"))),
            project_path=self.current_project.path,
            extra=_parse_key_value_text(self.model_settings.tts_vars_edit.text()),
        )


def _parse_key_value_text(raw_text: str) -> dict[str, object]:
    parsed: dict[str, object] = {}
    raw_items = [
        item.strip()
        for item in raw_text.replace("\n", ",").split(",")
        if item.strip()
    ]
    for item in raw_items:
        key, separator, value = item.partition("=")
        if not separator or not key or not value:
            raise ValueError(f"Expected KEY=VALUE, got: {item}")
        parsed[key] = value
    return parsed
