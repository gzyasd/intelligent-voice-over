from __future__ import annotations

import httpx


def test_http_adapter_renders_template_and_extracts_jsonpath(tmp_path) -> None:
    from ivo.adapters.base import AdapterContext
    from ivo.adapters.http import ApiAdapterProfile, HttpStageAdapter

    captured_request: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["url"] = str(request.url)
        captured_request["auth"] = request.headers["authorization"]
        captured_request["json"] = request.read().decode("utf-8")
        return httpx.Response(
            200,
            json={
                "result": {
                    "translation": "嗯，你好。",
                    "emotion": "warm",
                }
            },
        )

    adapter = HttpStageAdapter(
        ApiAdapterProfile(
            id="translate-http",
            stage="translation",
            method="POST",
            url="https://api.example.test/{{ source_language }}-to-{{ target_language }}",
            headers={"Authorization": "Bearer {{ api_key }}"},
            request_template={
                "text": "{{ segment_text }}",
                "speaker": "{{ speaker_id }}",
                "project": "{{ project_path }}",
            },
            response_mapping={
                "text": "$.result.translation",
                "emotion": "$.result.emotion",
            },
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = adapter.run(
        AdapterContext(
            project_path=tmp_path,
            segment_text="Well, hi.",
            source_language="en",
            target_language="zh",
            speaker_id="speaker-1",
            extra={"api_key": "secret"},
        )
    )

    assert result.ok is True
    assert result.payload == {"text": "嗯，你好。", "emotion": "warm"}
    assert captured_request["url"] == "https://api.example.test/en-to-zh"
    assert captured_request["auth"] == "Bearer secret"
    assert '"text":"Well, hi."' in str(captured_request["json"])


def test_http_adapter_returns_provider_error_for_non_success_status(tmp_path) -> None:
    from ivo.adapters.base import AdapterContext
    from ivo.adapters.http import ApiAdapterProfile, HttpStageAdapter

    adapter = HttpStageAdapter(
        ApiAdapterProfile(
            id="broken-provider",
            stage="translation",
            method="POST",
            url="https://api.example.test/translate",
            headers={},
            request_template={"text": "{{ segment_text }}"},
            response_mapping={"text": "$.text"},
        ),
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(503, text="busy"))
        ),
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

    assert result.ok is False
    assert result.error is not None
    assert result.error.provider == "broken-provider"
    assert result.error.http_status == 503
    assert result.error.retryable is True
    assert "busy" in result.error.message


def test_http_adapter_returns_timeout_error(tmp_path) -> None:
    from ivo.adapters.base import AdapterContext
    from ivo.adapters.http import ApiAdapterProfile, HttpStageAdapter

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("too slow", request=request)

    adapter = HttpStageAdapter(
        ApiAdapterProfile(
            id="slow-provider",
            stage="translation",
            method="POST",
            url="https://api.example.test/translate",
            headers={},
            request_template={"text": "{{ segment_text }}"},
            response_mapping={"text": "$.text"},
            timeout_seconds=1,
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
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

    assert result.ok is False
    assert result.error is not None
    assert result.error.provider == "slow-provider"
    assert result.error.retryable is True
    assert "timed out" in result.error.message


def test_http_adapter_skips_missing_optional_response_mapping(tmp_path) -> None:
    from ivo.adapters.base import AdapterContext
    from ivo.adapters.http import ApiAdapterProfile, HttpStageAdapter

    adapter = HttpStageAdapter(
        ApiAdapterProfile(
            id="style-provider",
            stage="translation",
            method="POST",
            url="https://api.example.test/translate",
            headers={},
            request_template={"text": "{{ segment_text }}"},
            response_mapping={
                "target_text": "$.text",
                "style_prompt": "$.style_prompt",
            },
            optional_response_keys={"style_prompt"},
        ),
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"text": "Hello there."})
            )
        ),
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
    assert result.payload == {"target_text": "Hello there."}


def test_http_adapter_returns_clear_error_for_missing_file_upload_variable(tmp_path) -> None:
    from ivo.adapters.base import AdapterContext
    from ivo.adapters.http import ApiAdapterProfile, HttpStageAdapter

    adapter = HttpStageAdapter(
        ApiAdapterProfile(
            id="upload-provider",
            stage="asr",
            method="POST",
            url="https://api.example.test/asr",
            headers={},
            request_template={},
            response_mapping={"segments": "$.segments"},
            file_upload_fields={"audio": "audio_path"},
        ),
        client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200))),
    )

    result = adapter.run(
        AdapterContext(
            project_path=tmp_path,
            segment_text="",
            source_language="en",
            target_language="zh",
            speaker_id="speaker-1",
        )
    )

    assert result.ok is False
    assert result.error is not None
    assert "file upload variable not found: audio_path" in result.error.message


def test_http_adapter_returns_clear_error_for_missing_file_upload_path(tmp_path) -> None:
    from ivo.adapters.base import AdapterContext
    from ivo.adapters.http import ApiAdapterProfile, HttpStageAdapter

    missing_audio = tmp_path / "missing.wav"
    adapter = HttpStageAdapter(
        ApiAdapterProfile(
            id="upload-provider",
            stage="asr",
            method="POST",
            url="https://api.example.test/asr",
            headers={},
            request_template={},
            response_mapping={"segments": "$.segments"},
            file_upload_fields={"audio": "audio_path"},
        ),
        client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200))),
    )

    result = adapter.run(
        AdapterContext(
            project_path=tmp_path,
            segment_text="",
            source_language="en",
            target_language="zh",
            speaker_id="speaker-1",
            extra={"audio_path": str(missing_audio)},
        )
    )

    assert result.ok is False
    assert result.error is not None
    assert "file upload path not found" in result.error.message
