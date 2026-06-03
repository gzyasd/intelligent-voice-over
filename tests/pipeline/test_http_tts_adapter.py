from __future__ import annotations

import base64

import httpx


def test_http_tts_adapter_writes_base64_audio_from_online_api(tmp_path) -> None:
    from ivo.adapters.http import ApiAdapterProfile
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.pipeline.synthesize import HttpTtsAdapter, synthesize_segment

    captured: dict[str, str] = {}
    audio_bytes = b"fake-wav-bytes"

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.read().decode("utf-8")
        return httpx.Response(
            200,
            json={
                "result": {
                    "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
                    "duration_ms": 1000,
                }
            },
        )

    project = DubbingProject.create(
        tmp_path / "http-tts.ivoproj",
        name="HTTP TTS",
        source_language="en",
        target_language="zh",
    )
    segment = DubbingSegment(
        id="seg-001",
        start_ms=0,
        end_ms=1_000,
        speaker_id="speaker-1",
        source_language="en",
        source_text="Hello.",
        target_language="zh",
        target_text="\u4f60\u597d\u3002",
        style_prompt="warm and natural",
        status="approved",
    )
    project.timeline.add_segment(segment)
    adapter = HttpTtsAdapter(
        ApiAdapterProfile(
            id="online-voice-clone",
            stage="tts",
            method="POST",
            url="https://api.example.test/tts",
            headers={"Authorization": "Bearer {{ api_key }}"},
            request_template={
                "text": "{{ segment_text }}",
                "speaker": "{{ speaker_id }}",
                "style": "{{ style_prompt }}",
                "duration": "{{ target_duration_ms }}",
            },
            response_mapping={
                "audio_base64": "$.result.audio_base64",
                "duration_ms": "$.result.duration_ms",
            },
        ),
        project_path=project.path,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        extra={"api_key": "secret"},
    )

    result = synthesize_segment(project, segment, adapter)

    assert result.generated_duration_ms == 1000
    assert result.audio_path.read_bytes() == audio_bytes
    assert project.timeline.get_segment("seg-001").quality_flags == ["duration_ok"]
    assert '"text":"\u4f60\u597d\u3002"' in captured["body"]
    assert "warm and natural" in captured["body"]


def test_http_tts_adapter_uses_target_duration_when_optional_duration_missing(tmp_path) -> None:
    from ivo.adapters.http import ApiAdapterProfile
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.pipeline.synthesize import HttpTtsAdapter, synthesize_segment

    audio_bytes = b"fake-wav-bytes"
    project = DubbingProject.create(
        tmp_path / "http-tts-default-duration.ivoproj",
        name="HTTP TTS Default Duration",
        source_language="en",
        target_language="zh",
    )
    segment = DubbingSegment(
        id="seg-001",
        start_ms=0,
        end_ms=1_000,
        speaker_id="speaker-1",
        source_language="en",
        source_text="Hello.",
        target_language="zh",
        target_text="Hello.",
        status="approved",
    )
    project.timeline.add_segment(segment)
    adapter = HttpTtsAdapter(
        ApiAdapterProfile(
            id="online-voice-clone",
            stage="tts",
            method="POST",
            url="https://api.example.test/tts",
            headers={},
            request_template={"text": "{{ segment_text }}"},
            response_mapping={
                "audio_base64": "$.audio_base64",
                "duration_ms": "$.duration_ms",
            },
            optional_response_keys=["duration_ms"],
        ),
        project_path=project.path,
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={"audio_base64": base64.b64encode(audio_bytes).decode("ascii")},
                )
            )
        ),
    )

    result = synthesize_segment(project, segment, adapter)

    assert result.generated_duration_ms == 1000
    assert result.audio_path.read_bytes() == audio_bytes


def test_http_tts_adapter_copies_audio_path_from_online_api(tmp_path) -> None:
    from ivo.adapters.http import ApiAdapterProfile
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.pipeline.synthesize import HttpTtsAdapter, synthesize_segment

    project = DubbingProject.create(
        tmp_path / "http-tts-path.ivoproj",
        name="HTTP TTS Path",
        source_language="en",
        target_language="zh",
    )
    provided_audio = tmp_path / "provider-audio.wav"
    provided_audio.write_bytes(b"provider-wav")
    segment = DubbingSegment(
        id="seg-001",
        start_ms=0,
        end_ms=1_000,
        speaker_id="speaker-1",
        source_language="en",
        source_text="Hello.",
        target_language="zh",
        target_text="Hello.",
        status="approved",
    )
    project.timeline.add_segment(segment)
    adapter = HttpTtsAdapter(
        ApiAdapterProfile(
            id="online-voice-clone",
            stage="tts",
            method="POST",
            url="https://api.example.test/tts",
            headers={},
            request_template={"text": "{{ segment_text }}"},
            response_mapping={
                "audio_base64": "$.audio_base64",
                "audio_path": "$.audio_path",
                "duration_ms": "$.duration_ms",
            },
            optional_response_keys=["audio_base64", "audio_path", "duration_ms"],
        ),
        project_path=project.path,
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"audio_path": str(provided_audio)})
            )
        ),
    )

    result = synthesize_segment(project, segment, adapter)

    assert result.generated_duration_ms == 1000
    assert result.audio_path.read_bytes() == b"provider-wav"
