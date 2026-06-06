from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QApplication, QCheckBox, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from ivo.adapters.base import AdapterError
from ivo.adapters.local import CommandExecutionLog


@dataclass(frozen=True)
class _LogEntry:
    level: str
    text: str


class RunLogPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._entries: list[_LogEntry] = []
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.error_only_checkbox = QCheckBox("仅显示错误日志")
        self.error_only_checkbox.stateChanged.connect(self._render_entries)
        self.copy_button = QPushButton("复制日志")
        self.copy_button.clicked.connect(self.copy_log)

        layout = QVBoxLayout()
        layout.addWidget(self.error_only_checkbox)
        layout.addWidget(self.log_text)
        layout.addWidget(self.copy_button)
        self.setLayout(layout)

    def append_stage_message(self, stage: str, message: str, *, level: str = "info") -> None:
        self._append(level, f"[{stage}] {message}")

    def append_adapter_error(self, error: AdapterError) -> None:
        lines = [
            f"[{error.stage}] {error.message}",
            f"服务：{error.provider}",
        ]
        if error.exit_code is not None:
            lines.append(f"退出码：{error.exit_code}")
        if error.command:
            lines.append(f"命令：{' '.join(error.command)}")
        if error.output_json_path:
            lines.append(f"输出 JSON：{error.output_json_path}")
        if error.stderr_summary:
            lines.append(f"错误输出：{error.stderr_summary}")
        self._append("error", "\n".join(lines))

    def append_command_output(self, log: CommandExecutionLog) -> None:
        command = " ".join(log.command)
        if log.stdout.strip():
            self._append(
                "info",
                f"[{log.stage}] 命令输出：{log.provider}\n命令：{command}\n{log.stdout.strip()}",
            )
        if log.stderr.strip():
            self._append(
                "error" if log.exit_code else "warning",
                f"[{log.stage}] 命令错误输出：{log.provider}\n命令：{command}\n{log.stderr.strip()}",
            )

    def plain_text(self) -> str:
        return self.log_text.toPlainText()

    def copy_log(self) -> None:
        QApplication.clipboard().setText(self.plain_text())

    def _append(self, level: str, text: str) -> None:
        self._entries.append(_LogEntry(level=level, text=text))
        if self.error_only_checkbox.isChecked() and level != "error":
            return
        self.log_text.appendPlainText(text)

    def _render_entries(self) -> None:
        self.log_text.clear()
        error_only = self.error_only_checkbox.isChecked()
        for entry in self._entries:
            if error_only and entry.level != "error":
                continue
            self.log_text.appendPlainText(entry.text)
