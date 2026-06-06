from __future__ import annotations

import httpx


def test_lm_studio_cleanup_unloads_loaded_model_instance() -> None:
    from ivo.adapters.http import ApiAdapterProfile
    from ivo.runtime_cleanup import unload_lm_studio_model_for_profile

    requests: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, str(request.url)))
        if request.url.path == "/api/v1/models":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "key": "qwen-local",
                            "loaded_instances": [{"id": "qwen-local"}],
                        }
                    ]
                },
            )
        if request.url.path == "/api/v1/models/unload":
            return httpx.Response(200, json={"instance_id": "qwen-local"})
        return httpx.Response(404)

    unloaded = unload_lm_studio_model_for_profile(
        ApiAdapterProfile(
            id="lm-studio-qwen",
            stage="translation",
            method="POST",
            url="http://127.0.0.1:1995/v1/chat/completions",
            request_template={"model": "qwen-local"},
            response_mapping={"content_json": "$.choices[0].message.content"},
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert unloaded == ["qwen-local"]
    assert requests == [
        ("GET", "http://127.0.0.1:1995/api/v1/models"),
        ("POST", "http://127.0.0.1:1995/api/v1/models/unload"),
    ]


def test_lm_studio_cleanup_ignores_non_lm_studio_profiles() -> None:
    from ivo.adapters.http import ApiAdapterProfile
    from ivo.runtime_cleanup import unload_lm_studio_model_for_profile

    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(500)

    unloaded = unload_lm_studio_model_for_profile(
        ApiAdapterProfile(
            id="remote-translator",
            stage="translation",
            method="POST",
            url="https://api.example.test/v1/chat/completions",
            request_template={"model": "remote-model"},
            response_mapping={"content_json": "$.choices[0].message.content"},
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert unloaded == []
    assert called is False


def test_lm_studio_cleanup_does_not_raise_when_unload_endpoint_fails() -> None:
    from ivo.adapters.http import ApiAdapterProfile
    from ivo.runtime_cleanup import unload_lm_studio_model_for_profile

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/models":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "key": "qwen-local",
                            "loaded_instances": [{"id": "qwen-local"}],
                        }
                    ]
                },
            )
        return httpx.Response(503, text="busy")

    unloaded = unload_lm_studio_model_for_profile(
        ApiAdapterProfile(
            id="lm-studio-qwen",
            stage="translation",
            method="POST",
            url="http://127.0.0.1:1995/v1/chat/completions",
            request_template={"model": "qwen-local"},
            response_mapping={"content_json": "$.choices[0].message.content"},
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert unloaded == []
