from __future__ import annotations

from PySide6.QtWidgets import QApplication, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from ivo.adapters.base import AdapterError


class RunLogPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.copy_button = QPushButton("复制日志")
        self.copy_button.clicked.connect(self.copy_log)

        layout = QVBoxLayout()
        layout.addWidget(self.log_text)
        layout.addWidget(self.copy_button)
        self.setLayout(layout)

    def append_stage_message(self, stage: str, message: str) -> None:
        self.log_text.appendPlainText(f"[{stage}] {message}")

    def append_adapter_error(self, error: AdapterError) -> None:
        lines = [
            f"[{error.stage}] {error.message}",
            f"provider: {error.provider}",
        ]
        if error.exit_code is not None:
            lines.append(f"exit code: {error.exit_code}")
        if error.command:
            lines.append(f"command: {' '.join(error.command)}")
        if error.output_json_path:
            lines.append(f"output JSON: {error.output_json_path}")
        if error.stderr_summary:
            lines.append(f"stderr: {error.stderr_summary}")
        self.log_text.appendPlainText("\n".join(lines))

    def plain_text(self) -> str:
        return self.log_text.toPlainText()

    def copy_log(self) -> None:
        QApplication.clipboard().setText(self.plain_text())
