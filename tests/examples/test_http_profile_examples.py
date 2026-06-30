from __future__ import annotations

import json
from pathlib import Path

import pytest

from ivo.adapters.http import ApiAdapterProfile


def test_http_profile_examples_are_valid() -> None:
    for profile_path in [
        Path("examples/http_separation_profile.example.json"),
        Path("examples/http_translation_profile.example.json"),
        Path("examples/http_asr_profile.example.json"),
        Path("examples/http_diarization_profile.example.json"),
        Path("examples/http_tts_profile.example.json"),
        Path("examples/http_translation_openai_compatible.example.json"),
    ]:
        profile = ApiAdapterProfile.model_validate(
            json.loads(profile_path.read_text(encoding="utf-8"))
        )

        assert profile.id
        assert profile.method == "POST"
        assert "Authorization" in profile.headers


def test_http_asr_profile_maps_segments() -> None:
    profile = ApiAdapterProfile.model_validate(
        json.loads(Path("examples/http_asr_profile.example.json").read_text(encoding="utf-8"))
    )

    assert profile.stage == "asr"
    assert profile.request_template["audio_path"] == "{{ audio_path }}"
    assert profile.response_mapping["segments"] == "$.segments"


def test_http_separation_profile_maps_base64_outputs() -> None:
    profile = ApiAdapterProfile.model_validate(
        json.loads(Path("examples/http_separation_profile.example.json").read_text(encoding="utf-8"))
    )

    assert profile.stage == "separation"
    assert profile.request_template["audio_path"] == "{{ audio_path }}"
    assert profile.response_mapping["vocals_base64"] == "$.vocals_base64"
    assert profile.response_mapping["background_base64"] == "$.background_base64"
    assert profile.response_mapping["vocals_path"] == "$.vocals_path"
    assert profile.response_mapping["background_path"] == "$.background_path"
    assert "vocals_base64" in profile.optional_response_keys
    assert "background_base64" in profile.optional_response_keys
    assert "vocals_path" in profile.optional_response_keys
    assert "background_path" in profile.optional_response_keys


def test_http_diarization_profile_maps_segments() -> None:
    profile = ApiAdapterProfile.model_validate(
        json.loads(
            Path("examples/http_diarization_profile.example.json").read_text(encoding="utf-8")
        )
    )

    assert profile.stage == "diarization"
    assert profile.request_template["audio_path"] == "{{ audio_path }}"
    assert profile.response_mapping["segments"] == "$.segments"


def test_http_translation_profile_marks_style_prompt_optional() -> None:
    profile = ApiAdapterProfile.model_validate(
        json.loads(
            Path("examples/http_translation_profile.example.json").read_text(encoding="utf-8")
        )
    )

    assert profile.stage == "translation"
    assert profile.response_mapping["style_prompt"] == "$.style_prompt"
    assert "style_prompt" in profile.optional_response_keys


def test_http_translation_openai_compatible_profile_maps_content_json() -> None:
    profile = ApiAdapterProfile.model_validate(
        json.loads(
            Path("examples/http_translation_openai_compatible.example.json").read_text(
                encoding="utf-8"
            )
        )
    )

    assert profile.stage == "translation"
    assert profile.url == "{{ base_url }}/v1/chat/completions"
    assert profile.request_template["model"] == "{{ model }}"
    assert profile.response_mapping["content_json"] == "$.choices[0].message.content"
    user_message = profile.request_template["messages"][1]["content"]
    assert "{{ source_language }}" in user_message
    assert "{{ target_language }}" in user_message
    assert "{{ speaker_id }}" in user_message
    assert "{{ duration_ms }}" in user_message


def test_http_translation_lm_studio_qwen36_profile_is_pinned_to_local_model() -> None:
    profile = ApiAdapterProfile.model_validate(
        json.loads(
            Path("examples/http_translation_lm_studio_qwen36_35b.example.json").read_text(
                encoding="utf-8"
            )
        )
    )

    assert profile.stage == "translation"
    assert profile.url == "http://127.0.0.1:1995/v1/chat/completions"
    assert profile.headers == {}
    assert (
        profile.request_template["model"]
        == "qwen3.6-35b-a3b-uncensored-hauhaucs-aggressive-q4_k_p"
    )
    assert "response_format" not in profile.request_template
    assert "source_text:" in profile.request_template["messages"][1]["content"]
    assert profile.response_mapping["content_json"] == "$.choices[0].message.content"


def test_http_tts_profile_marks_duration_optional() -> None:
    profile = ApiAdapterProfile.model_validate(
        json.loads(Path("examples/http_tts_profile.example.json").read_text(encoding="utf-8"))
    )

    assert profile.stage == "tts"
    assert profile.response_mapping["audio_base64"] == "$.audio_base64"
    assert profile.response_mapping["audio_path"] == "$.audio_path"
    assert "audio_base64" in profile.optional_response_keys
    assert "audio_path" in profile.optional_response_keys
    assert profile.response_mapping["duration_ms"] == "$.duration_ms"
    assert "duration_ms" in profile.optional_response_keys


def test_http_api_profiles_doc_covers_required_modes() -> None:
    path = Path("docs/http-api-profiles.md")
    if not path.exists():
        pytest.skip("optional docs/http-api-profiles.md is not present in this checkout")
    text = path.read_text(encoding="utf-8")

    for phrase in (
        "JSON API",
        "multipart",
        "OpenAI-compatible",
        "LM Studio",
        "audio_base64",
        "audio_path",
        "--translation-var api_key",
    ):
        assert phrase in text
