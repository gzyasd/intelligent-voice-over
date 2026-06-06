from __future__ import annotations


def test_project_wizard_browse_buttons_fill_video_and_output_paths(
    monkeypatch,
    qtbot,
    tmp_path,
) -> None:
    from ivo.ui.project_wizard import ProjectWizard

    source_video = tmp_path / "episode.mp4"
    output_dir = tmp_path / "renders"
    source_video.write_bytes(b"video")
    output_dir.mkdir()

    monkeypatch.setattr(
        "ivo.ui.project_wizard.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: (str(source_video), "Video files (*.mp4)"),
    )
    monkeypatch.setattr(
        "ivo.ui.project_wizard.QFileDialog.getExistingDirectory",
        lambda *args, **kwargs: str(output_dir),
    )

    wizard = ProjectWizard()
    qtbot.addWidget(wizard)

    wizard.browse_video_file()
    wizard.browse_output_dir()

    assert wizard.video_path_edit.text() == str(source_video)
    assert wizard.output_dir_edit.text() == str(output_dir)


def test_project_wizard_defaults_output_dir_to_workspace_runs(qtbot) -> None:
    from ivo.ui.project_wizard import ProjectWizard
    from ivo.workspace_paths import default_runs_dir

    wizard = ProjectWizard()
    qtbot.addWidget(wizard)

    assert wizard.output_dir_edit.text() == str(default_runs_dir())


def test_project_wizard_has_create_button_and_chinese_choices(qtbot, tmp_path) -> None:
    from ivo.ui.project_wizard import ProjectWizard

    wizard = ProjectWizard()
    qtbot.addWidget(wizard)

    assert wizard.create_project_button.text() == "创建项目"
    assert wizard.cancel_button.text() == "取消"
    assert wizard.create_project_button.isEnabled() is False
    assert wizard.source_language_combo.itemText(1) == "日语"
    assert wizard.processing_mode_combo.itemText(0) == "快速预览"
    assert wizard.series_type_combo.itemText(0) == "美剧"

    wizard.project_name_edit.setText("Episode 01")
    wizard.video_path_edit.setText(str(tmp_path / "episode.mp4"))
    wizard.output_dir_edit.setText(str(tmp_path))

    assert wizard.create_project_button.isEnabled() is True


def test_project_wizard_collects_translation_style_inputs(qtbot, tmp_path) -> None:
    from ivo.ui.project_wizard import ProjectWizard

    glossary_path = tmp_path / "glossary.json"
    glossary_path.write_text('{"先輩": "前辈"}', encoding="utf-8")

    wizard = ProjectWizard()
    qtbot.addWidget(wizard)
    wizard.project_name_edit.setText("Episode 01")
    wizard.video_path_edit.setText(str(tmp_path / "episode.mp4"))
    wizard.output_dir_edit.setText(str(tmp_path))
    wizard.set_source_language("ja")
    wizard.set_series_type("japanese_drama")
    wizard.translation_style_notes_edit.setPlainText("日剧口吻，自然，不要书面腔。")
    wizard.glossary_path_edit.setText(str(glossary_path))

    values = wizard.values()

    assert values.source_language == "ja"
    assert values.series_type == "japanese_drama"
    assert values.translation_style_notes == "日剧口吻，自然，不要书面腔。"
    assert values.glossary_path == glossary_path


def test_main_window_creates_project_from_wizard_inputs(qtbot, tmp_path) -> None:
    from ivo.ui.main_window import MainWindow
    from ivo.ui.project_wizard import ProjectWizard

    source_video = tmp_path / "episode.mp4"
    source_video.write_bytes(b"video")
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    wizard = ProjectWizard()
    qtbot.addWidget(wizard)
    wizard.project_name_edit.setText("Episode 01")
    wizard.video_path_edit.setText(str(source_video))
    wizard.output_dir_edit.setText(str(output_dir))
    wizard.set_source_language("ja")
    wizard.set_series_type("japanese_drama")
    wizard.translation_style_notes_edit.setPlainText("日剧口吻")

    window = MainWindow()
    qtbot.addWidget(window)

    project = window.create_project_from_wizard(wizard)

    assert project.path == output_dir / "Episode 01.ivoproj"
    assert project.source_language == "ja"
    assert project.settings.load().translation.series_type == "japanese_drama"
    assert project.settings.load().translation.translation_style_notes == "日剧口吻"
    assert window.source_video_path == source_video
    assert window.progress_label.text() == "项目已创建。下一步：点击“开始生成配音（完整流程）”。"


def test_project_wizard_uses_four_step_flow(qtbot) -> None:
    from ivo.ui.project_wizard import ProjectWizard

    wizard = ProjectWizard()
    qtbot.addWidget(wizard)

    assert wizard.step_titles() == ["选择视频", "内容与语言", "生成方案", "确认创建"]
    assert wizard.current_step_title() == "选择视频"

    wizard.next_step_button.click()

    assert wizard.current_step_title() == "内容与语言"

    wizard.back_step_button.click()

    assert wizard.current_step_title() == "选择视频"


def test_project_wizard_glossary_button_hides_json_word(qtbot) -> None:
    from ivo.ui.project_wizard import ProjectWizard

    wizard = ProjectWizard()
    qtbot.addWidget(wizard)

    assert wizard.glossary_browse_button.text() == "浏览术语表"
    assert "JSON" not in wizard.glossary_browse_button.text()


def test_project_wizard_can_request_start_immediately(qtbot, tmp_path) -> None:
    from ivo.ui.project_wizard import ProjectWizard

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    wizard = ProjectWizard()
    qtbot.addWidget(wizard)
    wizard.project_name_edit.setText("Episode 01")
    wizard.video_path_edit.setText(str(source))
    wizard.output_dir_edit.setText(str(output_dir))

    wizard.create_and_start_button.click()

    assert wizard.values().start_immediately is True
