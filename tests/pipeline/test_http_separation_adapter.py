from __future__ import annotations

import base64

import httpx


def test_http_separation_adapter_writes_base64_outputs_from_online_api(tmp_path) -> None:
    from ivo.adapters.http import ApiAdapterProfile
    from ivo.core.project import DubbingProject
    from ivo.pipeline.separate_audio import HttpSeparationAdapter, separate_audio

    project = DubbingProject.create(
        tmp_path / "http-separation.ivoproj",
        name="HTTP Separation",
        source_language="en",
        target_language="zh",
    )
    audio = project.path / "assets" / "extracted_audio.wav"
    audio.write_bytes(b"mixed")
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.read().decode("utf-8")
        return httpx.Response(
            200,
            json={
                "data": {
                    "vocals_base64": base64.b64encode(b"vocals").decode("ascii"),
                    "background_base64": base64.b64encode(b"background").decode("ascii"),
                }
            },
        )

    result = separate_audio(
        project,
        audio,
        HttpSeparationAdapter(
            ApiAdapterProfile(
                id="online-separation",
                stage="separation",
                method="POST",
                url="https://api.example.test/separate",
                headers={"Authorization": "Bearer {{ api_key }}"},
                request_template={"audio_path": "{{ audio_path }}"},
                response_mapping={
                    "vocals_base64": "$.data.vocals_base64",
                    "background_base64": "$.data.background_base64",
                },
            ),
            project_path=project.path,
            client=httpx.Client(transport=httpx.MockTransport(handler)),
            extra={"api_key": "secret"},
        ),
    )

    assert result.vocals_path.read_bytes() == b"vocals"
    assert result.background_path.read_bytes() == b"background"
    assert '"audio_path":"' in captured["body"]


def test_http_separation_adapter_copies_path_outputs_from_online_api(tmp_path) -> None:
    from ivo.adapters.http import ApiAdapterProfile
    from ivo.core.project import DubbingProject
    from ivo.pipeline.separate_audio import HttpSeparationAdapter, separate_audio

    project = DubbingProject.create(
        tmp_path / "http-separation-path.ivoproj",
        name="HTTP Separation Path",
        source_language="en",
        target_language="zh",
    )
    audio = project.path / "assets" / "extracted_audio.wav"
    audio.write_bytes(b"mixed")
    provider_vocals = tmp_path / "provider-vocals.wav"
    provider_background = tmp_path / "provider-background.wav"
    provider_vocals.write_bytes(b"vocals-from-path")
    provider_background.write_bytes(b"background-from-path")

    result = separate_audio(
        project,
        audio,
        HttpSeparationAdapter(
            ApiAdapterProfile(
                id="online-separation",
                stage="separation",
                method="POST",
                url="https://api.example.test/separate",
                headers={},
                request_template={"audio_path": "{{ audio_path }}"},
                response_mapping={
                    "vocals_base64": "$.vocals_base64",
                    "background_base64": "$.background_base64",
                    "vocals_path": "$.vocals_path",
                    "background_path": "$.background_path",
                },
                optional_response_keys=[
                    "vocals_base64",
                    "background_base64",
                    "vocals_path",
                    "background_path",
                ],
            ),
            project_path=project.path,
            client=httpx.Client(
                transport=httpx.MockTransport(
                    lambda request: httpx.Response(
                        200,
                        json={
                            "vocals_path": str(provider_vocals),
                            "background_path": str(provider_background),
                        },
                    )
                )
            ),
        ),
    )

    assert result.vocals_path.read_bytes() == b"vocals-from-path"
    assert result.background_path.read_bytes() == b"background-from-path"
