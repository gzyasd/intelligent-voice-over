from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
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


class ExportDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("\u5bfc\u51fa\u914d\u97f3\u89c6\u9891")

        self.output_path_edit = QLineEdit()
        self.output_path_browse_button = QPushButton("\u9009\u62e9\u5bfc\u51fa\u8def\u5f84")
        self.confirmation_checkbox = QCheckBox(
            "\u6211\u786e\u8ba4\u6709\u6743\u5904\u7406\u5e76\u5bfc\u51fa\u8be5\u7d20\u6750"
        )
        self.metadata_notice = QLabel(
            "\u5bfc\u51fa\u6587\u4ef6\u5c06\u5199\u5165 AI \u914d\u97f3\u5143\u6570\u636e\u3002"
        )
        self.watermark_checkbox = QCheckBox("\u6dfb\u52a0\u53ef\u89c1\u89d2\u6807")
        self.watermark_text = QLineEdit("AI 配音")
        self.cancel_button = QPushButton("取消")
        self.start_export_button = QPushButton("开始导出")
        self.start_export_button.setEnabled(False)

        self.output_path_browse_button.clicked.connect(self.browse_output_path)
        self.output_path_edit.textChanged.connect(self.refresh_export_button)
        self.confirmation_checkbox.stateChanged.connect(self.refresh_export_button)
        self.cancel_button.clicked.connect(self.reject)
        self.start_export_button.clicked.connect(self.accept)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("\u5bfc\u51fa\u8def\u5f84"))
        layout.addWidget(self.output_path_edit)
        layout.addWidget(self.output_path_browse_button)
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

    def can_export(self) -> bool:
        return self.confirmation_checkbox.isChecked() and bool(self.output_path_edit.text().strip())

    def confirmation(self) -> ExportConfirmation:
        return ExportConfirmation(accepted=self.confirmation_checkbox.isChecked())

    def watermark_options(self) -> WatermarkOptions:
        return WatermarkOptions(
            enabled=self.watermark_checkbox.isChecked(),
            text=self.watermark_text.text(),
        )

    def output_path(self) -> Path:
        return Path(self.output_path_edit.text().strip())

    def browse_output_path(self) -> None:
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "\u9009\u62e9\u5bfc\u51fa\u89c6\u9891\u8def\u5f84",
            "",
            "MP4 视频 (*.mp4);;所有文件 (*)",
        )
        if path:
            self.output_path_edit.setText(path)

    def refresh_export_button(self) -> None:
        self.start_export_button.setEnabled(self.can_export())
