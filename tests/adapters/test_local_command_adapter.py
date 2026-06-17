from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any


def test_local_command_adapter_renders_command_and_reads_json_output(tmp_path) -> None:
    from ivo.adapters.base import AdapterContext
    from ivo.adapters.local import LocalCommandAdapter, LocalCommandProfile

    output = tmp_path / "result.json"
    commands: list[list[str]] = []

    def runner(command: list[str]) -> None:
        commands.append(command)
        output.write_text('{"target_text": "你好", "emotion": "warm"}', encoding="utf-8")

    adapter = LocalCommandAdapter(
        LocalCommandProfile(
            id="local-translator",
            stage="translation",
            command=[
                "python",
                "translate.py",
                "--text",
                "{{ segment_text }}",
                "--out",
                "{{ output_json_path }}",
            ],
            output_json_path=str(output),
        ),
        runner=runner,
    )

    result = adapter.run(
        AdapterContext(
            project_path=tmp_path,
            segment_text="Hello",
            source_language="en",
            target_language="zh",
            speaker_id="speaker-1",
        )
    )

    assert result.ok is True
    assert result.payload == {"target_text": "你好", "emotion": "warm"}
    assert commands == [["python", "translate.py", "--text", "Hello", "--out", str(output)]]


def test_local_command_adapter_exposes_current_python_executable(tmp_path) -> None:
    from ivo.adapters.base import AdapterContext
    from ivo.adapters.local import LocalCommandAdapter, LocalCommandProfile

    output = tmp_path / "result.json"
    commands: list[list[str]] = []

    def runner(command: list[str]) -> None:
        commands.append(command)
        output.write_text("{}", encoding="utf-8")

    adapter = LocalCommandAdapter(
        LocalCommandProfile(
            id="local-asr",
            stage="asr",
            command=["{{ python_executable }}", "asr.py", "--out", "{{ output_json_path }}"],
            output_json_path=str(output),
        ),
        runner=runner,
    )

    result = adapter.run(
        AdapterContext(
            project_path=tmp_path,
            segment_text="",
            source_language="ja",
            target_language="zh",
            speaker_id="speaker-1",
        )
    )

    assert result.ok is True
    assert commands == [[sys.executable, "asr.py", "--out", str(output)]]


def test_local_command_adapter_honors_configured_python_and_working_dir(tmp_path) -> None:
    from ivo.adapters.base import AdapterContext
    from ivo.adapters.local import LocalCommandAdapter, LocalCommandProfile

    output = tmp_path / "result.json"
    working_dir = tmp_path / "runtime"
    working_dir.mkdir()
    commands: list[list[str]] = []
    cwd_values: list[str | None] = []

    def runner(command: list[str], cwd: str | None = None) -> None:
        commands.append(command)
        cwd_values.append(cwd)
        output.write_text("{}", encoding="utf-8")

    adapter = LocalCommandAdapter(
        LocalCommandProfile(
            id="local-asr",
            stage="asr",
            command=["{{ python_executable }}", "examples/local_commands/asr.py"],
            output_json_path=str(output),
            extra={
                "python_executable": "F:/runtime/.venv/Scripts/python.exe",
                "working_dir": str(working_dir),
            },
        ),
        runner=runner,
    )

    result = adapter.run(
        AdapterContext(
            project_path=tmp_path,
            segment_text="",
            source_language="ja",
            target_language="zh",
            speaker_id="speaker-1",
        )
    )

    assert result.ok is True
    assert commands == [["F:/runtime/.venv/Scripts/python.exe", "examples/local_commands/asr.py"]]
    assert cwd_values == [str(working_dir)]


def test_local_command_adapter_adds_bundled_ffmpeg_to_subprocess_path(
    tmp_path, monkeypatch
) -> None:
    from ivo.adapters.base import AdapterContext
    from ivo.adapters.local import LocalCommandAdapter, LocalCommandProfile

    runtime_root = tmp_path / "runtime"
    ffmpeg_bin = runtime_root / "_internal" / "ffmpeg" / "bin"
    ffmpeg_bin.mkdir(parents=True)
    (ffmpeg_bin / "ffmpeg.exe").write_text("", encoding="utf-8")
    output = tmp_path / "result.json"
    captured_env: dict[str, str] = {}

    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        del command
        captured_env.update(kwargs["env"])
        output.write_text("{}", encoding="utf-8")
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    adapter = LocalCommandAdapter(
        LocalCommandProfile(
            id="local-separation",
            stage="separation",
            command=["python", "sep.py", "--out", "{{ output_json_path }}"],
            output_json_path=str(output),
            extra={"working_dir": str(runtime_root)},
        )
    )

    result = adapter.run(
        AdapterContext(
            project_path=tmp_path,
            segment_text="",
            source_language="ja",
            target_language="zh",
            speaker_id="speaker-1",
        )
    )

    assert result.ok is True
    path_entries = captured_env["PATH"].split(";")
    assert str(Path(ffmpeg_bin)) in path_entries


def test_local_command_adapter_returns_error_when_output_missing(tmp_path) -> None:
    from ivo.adapters.base import AdapterContext
    from ivo.adapters.local import LocalCommandAdapter, LocalCommandProfile

    adapter = LocalCommandAdapter(
        LocalCommandProfile(
            id="broken-local",
            stage="tts",
            command=["missing-tool"],
            output_json_path=str(tmp_path / "missing.json"),
        ),
        runner=lambda command: None,
    )

    result = adapter.run(
        AdapterContext(
            project_path=tmp_path,
            segment_text="你好",
            source_language="en",
            target_language="zh",
            speaker_id="speaker-1",
        )
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error.provider == "broken-local"
    assert "output JSON not found" in result.error.message


def test_local_command_adapter_error_includes_command_context(tmp_path) -> None:
    from ivo.adapters.base import AdapterContext
    from ivo.adapters.local import LocalCommandAdapter, LocalCommandProfile

    output = tmp_path / "asr.json"

    def runner(command: list[str]) -> None:
        raise subprocess.CalledProcessError(
            returncode=7,
            cmd=command,
            stderr="model path not found\nfull traceback omitted",
        )

    adapter = LocalCommandAdapter(
        LocalCommandProfile(
            id="broken-asr",
            stage="asr",
            command=[
                "python",
                "asr.py",
                "--audio",
                "{{ segment_text }}",
                "--out",
                "{{ output_json_path }}",
            ],
            output_json_path=str(output),
        ),
        runner=runner,
    )

    result = adapter.run(
        AdapterContext(
            project_path=tmp_path,
            segment_text="voice.wav",
            source_language="en",
            target_language="zh",
            speaker_id="speaker-1",
        )
    )

    assert result.ok is False
    assert result.error is not None
    assert "stage: asr" in result.error.message
    assert "provider: broken-asr" in result.error.message
    assert "exit code: 7" in result.error.message
    assert "command: python asr.py --audio voice.wav" in result.error.message
    assert f"output JSON: {output}" in result.error.message
    assert "stderr: model path not found" in result.error.message
    assert result.error.command == [
        "python",
        "asr.py",
        "--audio",
        "voice.wav",
        "--out",
        str(output),
    ]
    assert result.error.exit_code == 7
    assert result.error.stderr_summary == "model path not found full traceback omitted"
    assert result.error.output_json_path == str(output)


def test_local_command_adapter_hides_windows_console_and_reports_command_output(
    monkeypatch,
    tmp_path,
) -> None:
    from ivo.adapters.base import AdapterContext
    from ivo.adapters.local import CommandExecutionLog, LocalCommandAdapter, LocalCommandProfile

    output = tmp_path / "result.json"
    calls: list[dict[str, object]] = []
    logs: list[CommandExecutionLog] = []

    def fake_run(command, **kwargs):
        calls.append(kwargs)
        output.write_text('{"ok": true}', encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="loaded model", stderr="warning")

    monkeypatch.setattr("ivo.adapters.local.subprocess.run", fake_run)

    adapter = LocalCommandAdapter(
        LocalCommandProfile(
            id="local-tts",
            stage="tts",
            command=["python", "tts.py", "--out", "{{ output_json_path }}"],
            output_json_path=str(output),
        ),
        command_output_callback=logs.append,
    )

    result = adapter.run(
        AdapterContext(
            project_path=tmp_path,
            segment_text="你好",
            source_language="ja",
            target_language="zh",
            speaker_id="speaker-1",
        )
    )

    assert result.ok is True
    assert calls[0]["capture_output"] is True
    assert calls[0]["text"] is True
    if sys.platform == "win32":
        assert calls[0]["creationflags"] & subprocess.CREATE_NO_WINDOW
        assert calls[0]["startupinfo"] is not None
    assert logs[0].stage == "tts"
    assert logs[0].stdout == "loaded model"
    assert logs[0].stderr == "warning"
