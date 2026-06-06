from __future__ import annotations


def test_model_center_validation_panel_shows_stage_results(qtbot, tmp_path) -> None:
    from ivo.ui.model_center import ModelCenter

    center = ModelCenter(config_store_path=tmp_path / "model-configs.json")
    qtbot.addWidget(center)

    center.show_validation_results(
        [
            {
                "stage": "asr",
                "provider": "faster-whisper",
                "status": "ready",
                "message": "模型已就绪",
            },
            {
                "stage": "tts",
                "provider": "F5-TTS",
                "status": "missing",
                "message": "请放到 models/tts/F5-TTS",
            },
        ]
    )

    summary = center.validation_summary_text()

    assert "语音识别：可用 · faster-whisper · 模型已就绪" in summary
    assert "语音合成：缺少模型 · F5-TTS · 请放到 models/tts/F5-TTS" in summary
    assert center.validation_status_pill.text() == "需要处理"


def test_model_center_test_single_stage_updates_only_that_stage(qtbot, tmp_path) -> None:
    from ivo.ui.model_center import ModelCenter

    center = ModelCenter(config_store_path=tmp_path / "model-configs.json")
    qtbot.addWidget(center)

    center.show_stage_validation_result(
        "translation",
        provider="LM Studio",
        status="failed",
        message="无法连接 http://127.0.0.1:1995/v1",
    )

    summary = center.validation_summary_text()

    assert "翻译：不可用 · LM Studio · 无法连接" in summary
    assert center.validation_status_pill.text() == "需要处理"
