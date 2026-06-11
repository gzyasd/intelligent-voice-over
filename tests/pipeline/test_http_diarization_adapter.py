from __future__ import annotations

import httpx


def test_http_diarization_adapter_reads_segments_from_online_api(tmp_path) -> None:
    from ivo.adapters.http import ApiAdapterProfile
    from ivo.pipeline.transcribe import HttpDiarizationAdapter, diarize_audio

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
                            "start_ms": 0,
                            "end_ms": 1200,
                            "speaker_id": "speaker-a",
                        }
                    ]
                }
            },
        )

    adapter = HttpDiarizationAdapter(
        ApiAdapterProfile(
            id="online-diarization",
            stage="diarization",
            method="POST",
            url="https://api.example.test/diarize",
            headers={"Authorization": "Bearer {{ api_key }}"},
            request_template={"audio_path": "{{ audio_path }}"},
            response_mapping={"segments": "$.data.segments"},
        ),
        project_path=tmp_path,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        extra={"api_key": "secret"},
    )

    segments = diarize_audio(adapter, audio)

    assert segments[0].speaker_id == "speaker-a"
    assert '"audio_path":"' in captured["body"]
