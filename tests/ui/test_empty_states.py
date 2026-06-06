from __future__ import annotations


def test_empty_state_panel_explains_problem_and_next_step(qtbot) -> None:
    from ivo.ui.empty_states import EmptyStatePanel

    panel = EmptyStatePanel(
        title="没有找到 F5-TTS 模型",
        description="请把模型放到 models/tts/F5-TTS，或在模型中心选择已有目录。",
        action_text="打开模型中心",
    )
    qtbot.addWidget(panel)

    assert panel.title_label.text() == "没有找到 F5-TTS 模型"
    assert "models/tts/F5-TTS" in panel.description_label.text()
    assert panel.action_button.text() == "打开模型中心"


def test_model_center_can_show_missing_model_hint(qtbot) -> None:
    from ivo.ui.model_center import ModelCenter

    center = ModelCenter()
    qtbot.addWidget(center)

    center.show_missing_model_hint("tts", "F5-TTS", "models/tts/F5-TTS")

    assert "没有找到 F5-TTS 模型" in center.model_hint_panel.title_label.text()
    assert "models/tts/F5-TTS" in center.model_hint_panel.description_label.text()


def test_project_library_empty_state_has_new_and_open_actions(qtbot) -> None:
    from ivo.ui.project_library_page import ProjectLibraryPage

    page = ProjectLibraryPage()
    qtbot.addWidget(page)
    page.set_projects([])

    assert page.empty_state is not None
    assert page.empty_state.title_label.text() == "还没有项目"
    assert page.empty_state.action_button.text() == "新建配音项目"
    assert page.open_existing_project_button.text() == "打开已有项目"
