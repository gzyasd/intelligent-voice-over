from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QApplication, QCheckBox, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from ivo.adapters.base import AdapterError
from ivo.adapters.local import CommandExecutionLog


@dataclass(frozen=True)
class _LogEntry:
    level: str
    text: str
    full_text: str


class RunLogPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._entries: list[_LogEntry] = []
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.error_only_checkbox = QCheckBox("仅显示错误日志")
        self.error_only_checkbox.stateChanged.connect(self._render_entries)
        self.show_warning_checkbox = QCheckBox("显示警告日志")
        self.show_warning_checkbox.setChecked(True)
        self.show_warning_checkbox.stateChanged.connect(self._render_entries)
        self.copy_button = QPushButton("复制日志")
        self.copy_button.clicked.connect(self.copy_log)

        layout = QVBoxLayout()
        layout.addWidget(self.error_only_checkbox)
        layout.addWidget(self.show_warning_checkbox)
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
        from ivo.ui.log_classification import classify_command_log

        for entry in classify_command_log(log):
            self._append(entry.level, entry.text, full_text=entry.full_text)

    def plain_text(self) -> str:
        return self.log_text.toPlainText()

    def copy_log(self) -> None:
        QApplication.clipboard().setText("\n\n".join(entry.full_text for entry in self._entries))

    def _should_show_entry(self, entry: _LogEntry) -> bool:
        if self.error_only_checkbox.isChecked():
            return entry.level == "error"
        if not self.show_warning_checkbox.isChecked() and entry.level == "warning":
            return False
        return True

    def _append(self, level: str, text: str, *, full_text: str | None = None) -> None:
        entry = _LogEntry(level=level, text=text, full_text=full_text or text)
        self._entries.append(entry)
        if not self._should_show_entry(entry):
            return
        self.log_text.appendPlainText(text)

    def _render_entries(self) -> None:
        self.log_text.clear()
        for entry in self._entries:
            if not self._should_show_entry(entry):
                continue
            self.log_text.appendPlainText(entry.text)
