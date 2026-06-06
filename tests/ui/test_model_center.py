from __future__ import annotations


def test_model_center_shows_user_friendly_presets_without_json_terms(qtbot) -> None:
    from ivo.ui.model_center import ModelCenter

    center = ModelCenter()
    qtbot.addWidget(center)

    text = center.visible_summary_text()

    assert "本机高质量" in text
    assert "本机快速预览" in text
    assert "选择模型目录" in text
    assert "一键检查模型" in text
    assert "JSON" not in text
    assert "profile" not in text.lower()
    assert "adapter" not in text.lower()
    assert "KEY=VALUE" not in text


def test_model_center_exposes_advanced_settings_only_when_requested(qtbot) -> None:
    from ivo.ui.model_center import ModelCenter

    center = ModelCenter()
    qtbot.addWidget(center)

    assert center.advanced_settings_visible() is False

    center.toggle_advanced_button.click()

    assert center.advanced_settings_visible() is True
