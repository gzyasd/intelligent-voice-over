from __future__ import annotations

import httpx


def test_build_translation_prompt_preserves_emotion_fillers_and_timing() -> None:
    from ivo.pipeline.transcribe import TranscriptionSegment
    from ivo.pipeline.translate import build_translation_prompt

    prompt = build_translation_prompt(
        TranscriptionSegment(
            id="seg-001",
            start_ms=0,
            end_ms=1_500,
            source_language="en",
            source_text="Well, I mean... hi.",
            speaker_id="speaker-1",
        ),
        target_language="zh",
    )

    assert "自然中文" in prompt
    assert "语气词" in prompt
    assert "情绪" in prompt
    assert "1500ms" in prompt
    assert "Well, I mean... hi." in prompt


def test_translate_segments_writes_needs_review_timeline_entries(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.pipeline.transcribe import TranscriptionSegment
    from ivo.pipeline.translate import MockTranslationAdapter, TranslationResult, translate_segments

    project = DubbingProject.create(
        tmp_path / "translate.ivoproj",
        name="Translate",
        source_language="ko",
        target_language="zh",
    )
    source_segments = [
        TranscriptionSegment(
            id="seg-001",
            start_ms=100,
            end_ms=1_200,
            source_language="ko",
            source_text="안녕.",
            speaker_id="speaker-1",
        )
    ]

    created = translate_segments(
        project,
        source_segments,
        MockTranslationAdapter(
            {
                "seg-001": TranslationResult(
                    segment_id="seg-001",
                    target_text="你好。",
                    emotion="warm",
                )
            }
        ),
    )

    assert created[0].status == "needs_review"
    assert created[0].target_text == "你好。"
    assert created[0].emotion == "warm"
    assert project.timeline.get_segment("seg-001") == created[0]


def test_http_translation_adapter_uses_profile_and_prompt(tmp_path) -> None:
    from ivo.adapters.http import ApiAdapterProfile
    from ivo.pipeline.transcribe import TranscriptionSegment
    from ivo.pipeline.translate import HttpTranslationAdapter

    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.read().decode("utf-8")
        return httpx.Response(200, json={"data": {"text": "嗯，你好。", "emotion": "warm"}})

    adapter = HttpTranslationAdapter(
        ApiAdapterProfile(
            id="online-translator",
            stage="translation",
            method="POST",
            url="https://api.example.test/translate",
            headers={},
            request_template={
                "prompt": "{{ prompt }}",
                "text": "{{ segment_text }}",
                "from": "{{ source_language }}",
                "to": "{{ target_language }}",
            },
            response_mapping={
                "target_text": "$.data.text",
                "emotion": "$.data.emotion",
            },
        ),
        project_path=tmp_path,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = adapter.translate(
        TranscriptionSegment(
            id="seg-001",
            start_ms=0,
            end_ms=1_000,
            source_language="en",
            source_text="Well, hi.",
            speaker_id="speaker-1",
        ),
        prompt="translate naturally",
    )

    assert result.segment_id == "seg-001"
    assert result.target_text == "嗯，你好。"
    assert result.emotion == "warm"
    assert "translate naturally" in captured["body"]


def test_http_translation_adapter_raises_clear_error_on_provider_failure(tmp_path) -> None:
    import pytest

    from ivo.adapters.http import ApiAdapterProfile
    from ivo.pipeline.transcribe import TranscriptionSegment
    from ivo.pipeline.translate import HttpTranslationAdapter, TranslationProviderError

    adapter = HttpTranslationAdapter(
        ApiAdapterProfile(
            id="broken-translator",
            stage="translation",
            method="POST",
            url="https://api.example.test/translate",
            headers={},
            request_template={"text": "{{ segment_text }}"},
            response_mapping={"target_text": "$.text"},
        ),
        project_path=tmp_path,
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(503, text="busy"))
        ),
    )

    with pytest.raises(TranslationProviderError, match="broken-translator"):
        adapter.translate(
            TranscriptionSegment(
                id="seg-001",
                start_ms=0,
                end_ms=1_000,
                source_language="en",
                source_text="Hello.",
            ),
            prompt="translate",
        )
