from __future__ import annotations

import subprocess


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
