from __future__ import annotations

import sys


def test_local_command_pipeline_connects_separation_asr_and_tts(tmp_path) -> None:
    from ivo.adapters.local import LocalCommandProfile
    from ivo.core.project import DubbingProject
    from ivo.pipeline.separate_audio import LocalCommandSeparationAdapter, separate_audio
    from ivo.pipeline.synthesize import LocalCommandTtsAdapter, synthesize_segment
    from ivo.pipeline.transcribe import LocalCommandAsrAdapter, transcribe_audio
    from ivo.pipeline.translate import MockTranslationAdapter, TranslationResult, translate_segments

    project = DubbingProject.create(
        tmp_path / "local-command.ivoproj",
        name="Local Command",
        source_language="en",
        target_language="zh",
    )
    audio = project.path / "assets" / "extracted_audio.wav"
    audio.write_bytes(b"fake-wav")

    separation = separate_audio(
        project,
        audio,
        LocalCommandSeparationAdapter(
            LocalCommandProfile(
                id="mock-separate",
                stage="separation",
                command=[
                    sys.executable,
                    "examples/local_commands/mock_separate.py",
                    "--audio",
                    "{{ audio_path }}",
                    "--vocals-out",
                    "{{ vocals_path }}",
                    "--background-out",
                    "{{ background_path }}",
                    "--json-out",
                    "{{ output_json_path }}",
                ],
                output_json_path=str(tmp_path / "separation.json"),
            )
        ),
    )
    source_segments = transcribe_audio(
        LocalCommandAsrAdapter(
            LocalCommandProfile(
                id="mock-asr",
                stage="asr",
                command=[
                    sys.executable,
                    "examples/local_commands/mock_asr.py",
                    "--audio",
                    "{{ audio_path }}",
                    "--language",
                    "{{ source_language }}",
                    "--out",
                    "{{ output_json_path }}",
                ],
                output_json_path=str(tmp_path / "asr.json"),
            )
        ),
        separation.vocals_path,
        source_language="en",
    )
    dubbed_segments = translate_segments(
        project,
        source_segments,
        MockTranslationAdapter(
            {
                "seg-001": TranslationResult(
                    segment_id="seg-001",
                    target_text="嗯，你好。",
                    emotion="warm",
                )
            }
        ),
    )
    project.timeline.update_segment("seg-001", status="approved")
    result = synthesize_segment(
        project,
        dubbed_segments[0],
        LocalCommandTtsAdapter(
            LocalCommandProfile(
                id="mock-tts",
                stage="tts",
                command=[
                    sys.executable,
                    "examples/local_commands/mock_tts.py",
                    "--text",
                    "{{ segment_text }}",
                    "--speaker",
                    "{{ speaker_id }}",
                    "--audio-out",
                    "{{ output_audio_path }}",
                    "--json-out",
                    "{{ output_json_path }}",
                ],
                output_json_path=str(tmp_path / "tts.json"),
            )
        ),
    )

    assert separation.vocals_path.is_file()
    assert source_segments[0].source_text == "Well, hi."
    assert result.audio_path.is_file()
    assert project.timeline.get_segment("seg-001").status == "rendered"
