from __future__ import annotations


def test_main_window_shows_project_controls(qtbot) -> None:
    from ivo.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == "智能视频配音"
    assert window.create_project_button.text() == "新建项目"
    assert window.open_project_button.text() == "打开项目"
    assert window.local_preview_button.text() == "本地命令预览"
    assert window.progress_label.text() == "尚未开始"


def test_timeline_editor_renders_project_segments(qtbot, tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.ui.timeline_editor import TimelineEditor

    project = DubbingProject.create(
        tmp_path / "ui.ivoproj",
        name="UI",
        source_language="en",
        target_language="zh",
    )
    project.timeline.add_segment(
        DubbingSegment(
            id="seg-001",
            start_ms=0,
            end_ms=1_000,
            speaker_id="speaker-1",
            source_language="en",
            source_text="Hello.",
            target_language="zh",
            target_text="你好。",
            emotion="warm",
            status="needs_review",
        )
    )

    editor = TimelineEditor()
    qtbot.addWidget(editor)
    editor.set_project(project)

    assert editor.table.rowCount() == 1
    assert editor.table.item(0, 2).text() == "Hello."
    assert editor.table.item(0, 3).text() == "你好。"
    assert editor.table.cellWidget(0, editor.COLUMN_ACTION) is not None


def test_export_dialog_requires_confirmation_and_supports_watermark(qtbot) -> None:
    from ivo.ui.export_dialog import ExportDialog

    dialog = ExportDialog()
    qtbot.addWidget(dialog)

    assert dialog.can_export() is False

    dialog.confirmation_checkbox.setChecked(True)
    dialog.output_path_edit.setText("final.mp4")
    dialog.watermark_checkbox.setChecked(True)
    dialog.watermark_text.setText("AI 中文配音")

    assert dialog.can_export() is True
    assert dialog.watermark_options().enabled is True
    assert dialog.watermark_options().text == "AI 中文配音"


def test_project_wizard_validates_required_video_path(qtbot) -> None:
    from ivo.ui.project_wizard import ProjectWizard

    wizard = ProjectWizard()
    qtbot.addWidget(wizard)

    assert wizard.is_valid() is False
    wizard.video_path_edit.setText("episode.mp4")
    wizard.project_name_edit.setText("Episode")
    wizard.output_dir_edit.setText("renders")
    assert wizard.is_valid() is True


def test_background_worker_runs_task_without_ui_coupling() -> None:
    from ivo.ui.workers import PipelineWorker

    calls: list[str] = []
    worker = PipelineWorker(lambda: calls.append("ran"))

    worker.run()

    assert calls == ["ran"]


def test_background_worker_stores_task_result() -> None:
    from ivo.ui.workers import PipelineWorker

    worker = PipelineWorker(lambda: "done")

    worker.run()

    assert worker.result == "done"


def test_model_settings_saves_and_loads_http_adapter_profile(qtbot, tmp_path) -> None:
    from ivo.adapters.profiles import AdapterProfileStore
    from ivo.ui.model_settings import ModelSettings

    store_path = tmp_path / "adapters.json"
    settings = ModelSettings()
    qtbot.addWidget(settings)

    settings.profile_id_edit.setText("translator")
    settings.stage_edit.setText("translation")
    settings.url_edit.setText("https://api.example.test/translate")
    settings.response_mapping_edit.setText("target_text=$.text")
    settings.optional_response_keys_edit.setText("style_prompt,duration_ms")
    settings.save_adapter_profile(store_path)

    reloaded = ModelSettings()
    qtbot.addWidget(reloaded)
    reloaded.load_adapter_profiles(store_path)

    assert reloaded.adapter_list.count() == 1
    assert reloaded.adapter_list.item(0).text() == "translator translation"
    profile = AdapterProfileStore(store_path).load()[0]
    assert profile.optional_response_keys == ["style_prompt", "duration_ms"]


def test_model_settings_browse_buttons_fill_profile_paths(monkeypatch, qtbot, tmp_path) -> None:
    from ivo.ui.model_settings import ModelSettings

    local_profile = tmp_path / "local.json"
    separation_profile = tmp_path / "separation.json"
    asr_profile = tmp_path / "asr.json"
    diarization_profile = tmp_path / "diarization.json"
    translation_profile = tmp_path / "translation.json"
    tts_profile = tmp_path / "tts.json"
    local_profile.write_text("{}", encoding="utf-8")
    separation_profile.write_text("{}", encoding="utf-8")
    asr_profile.write_text("{}", encoding="utf-8")
    diarization_profile.write_text("{}", encoding="utf-8")
    translation_profile.write_text("{}", encoding="utf-8")
    tts_profile.write_text("{}", encoding="utf-8")
    selected_paths = [
        str(local_profile),
        str(separation_profile),
        str(asr_profile),
        str(diarization_profile),
        str(translation_profile),
        str(tts_profile),
    ]

    def fake_get_open_file_name(*args, **kwargs):
        return selected_paths.pop(0), "JSON files (*.json)"

    monkeypatch.setattr(
        "ivo.ui.model_settings.QFileDialog.getOpenFileName",
        fake_get_open_file_name,
    )

    settings = ModelSettings()
    qtbot.addWidget(settings)

    settings.browse_local_command_profiles()
    settings.browse_separation_profile()
    settings.browse_asr_profile()
    settings.browse_diarization_profile()
    settings.browse_translation_profile()
    settings.browse_tts_profile()

    assert settings.local_command_profiles_path_edit.text() == str(local_profile)
    assert settings.separation_profile_path_edit.text() == str(separation_profile)
    assert settings.asr_profile_path_edit.text() == str(asr_profile)
    assert settings.diarization_profile_path_edit.text() == str(diarization_profile)
    assert settings.translation_profile_path_edit.text() == str(translation_profile)
    assert settings.tts_profile_path_edit.text() == str(tts_profile)
