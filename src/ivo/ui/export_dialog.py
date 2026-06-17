from __future__ import annotations

from pathlib import Path
from typing import Literal

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ivo.compliance.confirmation import ExportConfirmation
from ivo.compliance.watermark import WatermarkOptions
from ivo.ui.theme import mark_dialog, mark_primary_button, mark_secondary_button


class ExportDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("导出配音")
        mark_dialog(self)
        self._content_type: Literal["video", "audio"] = "video"

        self.output_path_edit = QLineEdit()
        self.output_path_browse_button = QPushButton("选择导出路径")
        self.audio_format_combo = QComboBox()
        self.audio_format_combo.addItem("WAV (无损)", "wav")
        self.audio_format_combo.addItem("MP3 (192kbps)", "mp3")
        self.audio_format_label = QLabel("音频格式")
        self.confirmation_checkbox = QCheckBox(
            "我确认有权处理并导出该素材"
        )
        self.metadata_notice = QLabel(
            "导出文件将写入 AI 配音元数据。"
        )
        self.watermark_checkbox = QCheckBox("添加可见角标")
        self.watermark_text = QLineEdit("AI 配音")
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setStyleSheet("")
        mark_secondary_button(self.cancel_button)
        self.start_export_button = QPushButton("开始导出")
        self.start_export_button.setStyleSheet("")
        mark_primary_button(self.start_export_button)
        self.start_export_button.setEnabled(False)

        self.output_path_browse_button.clicked.connect(self.browse_output_path)
        self.output_path_edit.textChanged.connect(self.refresh_export_button)
        self.confirmation_checkbox.stateChanged.connect(self.refresh_export_button)
        self.audio_format_combo.currentIndexChanged.connect(self._on_format_changed)
        self.cancel_button.clicked.connect(self.reject)
        self.start_export_button.clicked.connect(self.accept)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("导出路径"))
        layout.addWidget(self.output_path_edit)
        layout.addWidget(self.output_path_browse_button)
        layout.addWidget(self.audio_format_label)
        layout.addWidget(self.audio_format_combo)
        layout.addWidget(self.confirmation_checkbox)
        layout.addWidget(self.metadata_notice)
        layout.addWidget(self.watermark_checkbox)
        layout.addWidget(self.watermark_text)
        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.start_export_button)
        layout.addLayout(actions)
        self.setLayout(layout)
        self._update_ui_for_content_type()

    def set_content_type(self, content_type: Literal["video", "audio"]) -> None:
        self._content_type = content_type
        self._update_ui_for_content_type()

    def _update_ui_for_content_type(self) -> None:
        is_audio = self._content_type == "audio"
        if is_audio:
            self.setWindowTitle("导出配音音频")
        else:
            self.setWindowTitle("导出配音视频")
        # Audio mode: show format selector, hide watermark
        self.audio_format_label.setVisible(is_audio)
        self.audio_format_combo.setVisible(is_audio)
        # Video mode: show watermark
        self.watermark_checkbox.setVisible(not is_audio)
        self.watermark_text.setVisible(not is_audio)

    def can_export(self) -> bool:
        return self.confirmation_checkbox.isChecked() and bool(self.output_path_edit.text().strip())

    def confirmation(self) -> ExportConfirmation:
        return ExportConfirmation(accepted=self.confirmation_checkbox.isChecked())

    def audio_format(self) -> Literal["wav", "mp3"]:
        return self.audio_format_combo.currentData() or "wav"

    def watermark_options(self) -> WatermarkOptions:
        return WatermarkOptions(
            enabled=self.watermark_checkbox.isChecked(),
            text=self.watermark_text.text(),
        )

    def output_path(self) -> Path:
        return Path(self.output_path_edit.text().strip())

    def default_suffix(self) -> str:
        if self._content_type == "audio":
            return "final." + (self.audio_format_combo.currentData() or "wav")
        return "final.mp4"

    def browse_output_path(self) -> None:
        if self._content_type == "audio":
            filter_text = "WAV 音频 (*.wav);;MP3 音频 (*.mp3);;所有文件 (*)"
            title = "选择导出音频路径"
        else:
            filter_text = "MP4 视频 (*.mp4);;所有文件 (*)"
            title = "选择导出视频路径"
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            title,
            "",
            filter_text,
        )
        if path:
            self.output_path_edit.setText(path)

    def refresh_export_button(self) -> None:
        self.start_export_button.setEnabled(self.can_export())

    def _on_format_changed(self) -> None:
        """Sync output path suffix when audio format changes."""
        if self._content_type != "audio":
            return
        current_text = self.output_path_edit.text().strip()
        if not current_text:
            return
        path = Path(current_text)
        new_suffix = f".{self.audio_format()}"
        if path.suffix.lower() != new_suffix:
            self.output_path_edit.setText(str(path.with_suffix(new_suffix)))