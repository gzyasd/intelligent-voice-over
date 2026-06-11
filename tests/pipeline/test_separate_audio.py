from __future__ import annotations


def test_mock_separation_creates_vocals_and_background(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.pipeline.separate_audio import MockSeparationAdapter, separate_audio

    project = DubbingProject.create(
        tmp_path / "separate.ivoproj",
        name="Separate",
        source_language="ko",
        target_language="zh",
    )
    audio = project.path / "assets" / "extracted_audio.wav"
    audio.write_bytes(b"fake-wav")

    result = separate_audio(project, audio, MockSeparationAdapter())

    assert result.vocals_path == project.path / "work" / "vocals.wav"
    assert result.background_path == project.path / "work" / "background.wav"
    assert result.vocals_path.read_bytes() == b"fake-wav"
    assert result.background_path.read_bytes() == b"fake-wav"


def test_local_command_separation_adapter_uses_json_contract(tmp_path) -> None:
    import json

    from ivo.adapters.local import LocalCommandProfile
    from ivo.core.project import DubbingProject
    from ivo.pipeline.separate_audio import LocalCommandSeparationAdapter, separate_audio

    project = DubbingProject.create(
        tmp_path / "local-separate.ivoproj",
        name="Local Separate",
        source_language="en",
        target_language="zh",
    )
    audio = project.path / "assets" / "extracted_audio.wav"
    audio.write_bytes(b"fake-wav")
    output_json = tmp_path / "separation.json"
    commands: list[list[str]] = []

    def runner(command: list[str]) -> None:
        commands.append(command)
        vocals_path = command[command.index("--vocals-out") + 1]
        background_path = command[command.index("--background-out") + 1]
        with open(vocals_path, "wb") as vocals:
            vocals.write(b"vocals")
        with open(background_path, "wb") as background:
            background.write(b"background")
        output_json.write_text(
            json.dumps({"vocals_path": vocals_path, "background_path": background_path}),
            encoding="utf-8",
        )

    result = separate_audio(
        project,
        audio,
        LocalCommandSeparationAdapter(
            LocalCommandProfile(
                id="demucs-command",
                stage="separation",
                command=[
                    "python",
                    "separate.py",
                    "--audio",
                    "{{ audio_path }}",
                    "--vocals-out",
                    "{{ vocals_path }}",
                    "--background-out",
                    "{{ background_path }}",
                    "--json-out",
                    "{{ output_json_path }}",
                ],
                output_json_path=str(output_json),
            ),
            runner=runner,
        ),
    )

    assert result.vocals_path.read_bytes() == b"vocals"
    assert result.background_path.read_bytes() == b"background"
    assert commands[0][commands[0].index("--audio") + 1] == str(audio)
