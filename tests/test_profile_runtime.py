from __future__ import annotations

from pathlib import Path


def test_prepare_local_command_profiles_resolves_relative_profile_runtime_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from ivo.adapters.local import LocalCommandProfile
    from ivo.pipeline.local_command_preview import LocalCommandPipelineProfiles
    from ivo.profile_runtime import prepare_local_command_profiles

    app_root = tmp_path / "dist" / "IntelligentVoiceOver"
    (app_root / "examples" / "local_commands").mkdir(parents=True)
    local_python = app_root / ".venv" / "Scripts" / "python.exe"
    pyannote_python = app_root / ".venv-pyannote" / "Scripts" / "python.exe"
    local_python.parent.mkdir(parents=True)
    pyannote_python.parent.mkdir(parents=True)
    local_python.write_text("", encoding="utf-8")
    pyannote_python.write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    profiles = prepare_local_command_profiles(
        LocalCommandPipelineProfiles(
            separation=LocalCommandProfile(
                id="sep",
                stage="separation",
                command=["{{ python_executable }}", "sep.py"],
                output_json_path="sep.json",
            ),
            asr=LocalCommandProfile(
                id="asr",
                stage="asr",
                command=["{{ python_executable }}", "asr.py"],
                output_json_path="asr.json",
            ),
            diarization=LocalCommandProfile(
                id="dia",
                stage="diarization",
                extra={"pyannote_python_executable": ".venv-pyannote/Scripts/python.exe"},
                command=["{{ pyannote_python_executable }}", "dia.py"],
                output_json_path="dia.json",
            ),
            tts=LocalCommandProfile(
                id="tts",
                stage="tts",
                command=["{{ python_executable }}", "tts.py"],
                output_json_path="tts.json",
            ),
        ),
        profiles_path=Path("dist/IntelligentVoiceOver/examples/profile.json"),
        models_dir=Path("models"),
    )

    assert profiles.separation.extra["working_dir"] == str(app_root)
    assert profiles.separation.extra["python_executable"] == str(local_python)
    assert profiles.diarization is not None
    assert profiles.diarization.extra["pyannote_python_executable"] == str(pyannote_python)


def test_prepare_local_command_profiles_prefers_configured_python_paths(
    tmp_path: Path,
) -> None:
    from ivo.adapters.local import LocalCommandProfile
    from ivo.pipeline.local_command_preview import LocalCommandPipelineProfiles
    from ivo.profile_runtime import prepare_local_command_profiles

    app_root = tmp_path / "resources"
    profiles_path = app_root / "examples" / "profile.json"
    (app_root / "examples" / "local_commands").mkdir(parents=True)
    configured_python = tmp_path / "runtime" / "python.exe"
    configured_pyannote = tmp_path / "pyannote" / "python.exe"
    configured_python.parent.mkdir(parents=True)
    configured_pyannote.parent.mkdir(parents=True)
    configured_python.write_bytes(b"python")
    configured_pyannote.write_bytes(b"python")

    profile = LocalCommandProfile(
        id="local",
        stage="separation",
        command=["{{ python_executable }}", "script.py"],
        output_json_path="output.json",
    )
    profiles = prepare_local_command_profiles(
        LocalCommandPipelineProfiles(
            separation=profile.model_copy(deep=True),
            asr=profile.model_copy(update={"stage": "asr"}, deep=True),
            diarization=profile.model_copy(
                update={
                    "stage": "diarization",
                    "command": ["{{ pyannote_python_executable }}", "script.py"],
                },
                deep=True,
            ),
            tts=profile.model_copy(update={"stage": "tts"}, deep=True),
        ),
        profiles_path=profiles_path,
        python_executable=configured_python,
        pyannote_python_executable=configured_pyannote,
    )

    assert profiles.separation.extra["python_executable"] == str(configured_python)
    assert profiles.asr.extra["python_executable"] == str(configured_python)
    assert profiles.tts.extra["python_executable"] == str(configured_python)
    assert profiles.diarization is not None
    assert profiles.diarization.extra["pyannote_python_executable"] == str(
        configured_pyannote
    )
