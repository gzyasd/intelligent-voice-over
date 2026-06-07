from __future__ import annotations


def test_scan_model_candidates_groups_recommended_and_extra_directories(tmp_path) -> None:
    from ivo.core.model_inventory import group_candidates_by_stage, scan_model_candidates

    models_dir = tmp_path / "models"
    (models_dir / "asr" / "faster-whisper-large-v3").mkdir(parents=True)
    (models_dir / "tts" / "F5-TTS").mkdir(parents=True)
    (models_dir / "llm" / "Qwen3.6-35B-A3B").mkdir(parents=True)

    grouped = group_candidates_by_stage(scan_model_candidates(models_dir))

    assert "faster-whisper-large-v3" in [candidate.name for candidate in grouped["asr"]]
    assert "F5-TTS" in [candidate.name for candidate in grouped["tts"]]
    assert "Qwen3.6-35B-A3B" in [candidate.name for candidate in grouped["translation"]]
    assert grouped["asr"][0].path.is_absolute()


def test_fetch_lm_studio_models_reads_openai_compatible_model_list(monkeypatch) -> None:
    from ivo.core.model_inventory import fetch_lm_studio_models

    requested_urls: list[str] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, list[dict[str, str]]]:
            return {
                "data": [
                    {"id": "Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-Q4_K_P"},
                    {"id": "Qwen3-8B"},
                ]
            }

    class FakeClient:
        def __init__(self, *, timeout: float) -> None:
            self.timeout = timeout

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def get(self, url: str) -> FakeResponse:
            requested_urls.append(url)
            return FakeResponse()

    monkeypatch.setattr("ivo.core.model_inventory.httpx.Client", FakeClient)

    models = fetch_lm_studio_models("http://127.0.0.1:1995/v1")

    assert requested_urls == ["http://127.0.0.1:1995/v1/models"]
    assert models == [
        "Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-Q4_K_P",
        "Qwen3-8B",
    ]


def test_validate_stage_config_reports_missing_local_model(tmp_path) -> None:
    from ivo.core.model_inventory import validate_stage_config
    from ivo.core.visual_model_config import VisualStageConfig

    result = validate_stage_config(
        VisualStageConfig(
            stage="tts",
            label="语音合成",
            service_type="local",
            provider_name="F5-TTS",
            model_path="tts/F5-TTS",
        ),
        tmp_path / "models",
    )

    assert result.stage == "tts"
    assert result.status == "missing"
    assert "没有找到模型目录" in result.message


def test_validate_stage_config_accepts_lm_studio_model_name(tmp_path) -> None:
    from ivo.core.model_inventory import validate_stage_config
    from ivo.core.visual_model_config import VisualStageConfig

    result = validate_stage_config(
        VisualStageConfig(
            stage="translation",
            label="翻译",
            service_type="http",
            provider_name="LM Studio",
            api_base_url="http://127.0.0.1:1995/v1",
            api_model="Qwen3.6-35B-A3B",
        ),
        tmp_path / "models",
        lm_studio_models=["Qwen3.6-35B-A3B", "Qwen3-8B"],
    )

    assert result.status == "ready"
    assert "LM Studio 已找到该模型" in result.message
