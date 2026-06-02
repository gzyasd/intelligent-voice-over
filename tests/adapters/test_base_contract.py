from __future__ import annotations


def test_mock_adapter_returns_configured_payload(tmp_path) -> None:
    from ivo.adapters.base import AdapterContext, MockStageAdapter

    adapter = MockStageAdapter(stage="translation", payload={"text": "你好"})
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
    assert result.stage == "translation"
    assert result.payload == {"text": "你好"}
    assert result.error is None


def test_adapter_context_serializes_paths_as_strings(tmp_path) -> None:
    from ivo.adapters.base import AdapterContext

    context = AdapterContext(
        project_path=tmp_path,
        segment_text="Hello",
        source_language="en",
        target_language="zh",
        speaker_id="speaker-1",
        reference_audio_path=tmp_path / "voice.wav",
    )

    values = context.template_values()

    assert values["project_path"] == str(tmp_path)
    assert values["reference_audio_path"] == str(tmp_path / "voice.wav")
