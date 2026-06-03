from __future__ import annotations

import httpx


def test_http_asr_adapter_reads_segments_from_online_api(tmp_path) -> None:
    from ivo.adapters.http import ApiAdapterProfile
    from ivo.pipeline.transcribe import HttpAsrAdapter, transcribe_audio

    audio = tmp_path / "vocals.wav"
    audio.write_bytes(b"fake-wav")
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.read().decode("utf-8")
        return httpx.Response(
            200,
            json={
                "data": {
                    "segments": [
                        {
                            "id": "seg-001",
                            "start_ms": 0,
                            "end_ms": 1200,
                            "text": "Well, hi.",
                            "speaker_id": "speaker-1",
                        }
                    ]
                }
            },
        )

    adapter = HttpAsrAdapter(
        ApiAdapterProfile(
            id="online-asr",
            stage="asr",
            method="POST",
            url="https://api.example.test/asr",
            headers={"Authorization": "Bearer {{ api_key }}"},
            request_template={
                "audio_path": "{{ audio_path }}",
                "language": "{{ source_language }}",
            },
            response_mapping={"segments": "$.data.segments"},
        ),
        project_path=tmp_path,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        extra={"api_key": "secret"},
    )

    segments = transcribe_audio(adapter, audio, source_language="en")

    assert segments[0].id == "seg-001"
    assert segments[0].source_language == "en"
    assert segments[0].source_text == "Well, hi."
    assert segments[0].speaker_id == "speaker-1"
    assert '"audio_path":"' in captured["body"]
    assert '"language":"en"' in captured["body"]
