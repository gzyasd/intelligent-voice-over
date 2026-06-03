from __future__ import annotations

import json
from pathlib import Path

from ivo.adapters.http import ApiAdapterProfile


def test_http_profile_examples_are_valid() -> None:
    for profile_path in [
        Path("examples/http_separation_profile.example.json"),
        Path("examples/http_translation_profile.example.json"),
        Path("examples/http_asr_profile.example.json"),
        Path("examples/http_diarization_profile.example.json"),
        Path("examples/http_tts_profile.example.json"),
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


def test_http_diarization_profile_maps_segments() -> None:
    profile = ApiAdapterProfile.model_validate(
        json.loads(
            Path("examples/http_diarization_profile.example.json").read_text(encoding="utf-8")
        )
    )

    assert profile.stage == "diarization"
    assert profile.request_template["audio_path"] == "{{ audio_path }}"
    assert profile.response_mapping["segments"] == "$.segments"
