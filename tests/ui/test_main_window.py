from __future__ import annotations


def test_main_window_shows_project_controls(qtbot) -> None:
    from ivo.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == "智能视频配音"
    assert window.app_shell.navigation_labels() == [
        "首页",
        "项目库",
        "当前项目",
        "模型中心",
        "设置",
    ]
    assert window.app_shell.current_page_id() == "home"
    assert window.project_library_page.project_count() >= 0
    assert window.create_project_button.text() == "新建项目"
    assert window.open_project_button.text() == "打开项目"
    assert window.local_preview_button.text() == "开始生成配音（完整流程）"
    assert window.evaluation_report_button.text() == "生成评估报告"
    assert window.progress_label.text() == "尚未开始"


def test_main_window_can_be_resized_shorter_than_default_height(qtbot) -> None:
    from ivo.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    assert window.minimumSizeHint().height() <= 720


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


def test_run_log_panel_filters_error_logs(qtbot) -> None:
    from ivo.ui.run_log import RunLogPanel

    panel = RunLogPanel()
    qtbot.addWidget(panel)

    panel.append_stage_message("配音生成", "开始生成")
    panel.append_stage_message("配音生成", "模型加载失败", level="error")
    panel.error_only_checkbox.setChecked(True)

    assert "模型加载失败" in panel.plain_text()
    assert "开始生成" not in panel.plain_text()


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
    settings.file_upload_fields_edit.setText("audio=audio_path")
    settings.http_adapter_path_edit.setText(str(store_path))
    settings.save_adapter_profile_button.click()

    reloaded = ModelSettings()
    qtbot.addWidget(reloaded)
    reloaded.http_adapter_path_edit.setText(str(store_path))
    reloaded.load_adapter_profiles_button.click()

    assert reloaded.adapter_list.count() == 1
    assert reloaded.adapter_list.item(0).text() == "translator translation"
    profile = AdapterProfileStore(store_path).load()[0]
    assert profile.optional_response_keys == ["style_prompt", "duration_ms"]
    assert profile.file_upload_fields == {"audio": "audio_path"}


def test_model_settings_guides_local_model_directory_in_chinese(qtbot) -> None:
    from ivo.ui.model_settings import ModelSettings

    settings = ModelSettings()
    qtbot.addWidget(settings)

    assert settings.local_model_path_edit.text() == "models"
    assert settings.model_root_hint_label.text().startswith("默认模型目录")
    assert "本地命令配置 JSON" in settings.local_command_help_label.text()
    assert "examples/local_command_profiles.real_gpu_fast_preview.json" in (
        settings.local_command_profiles_path_edit.placeholderText()
    )
    assert settings.check_local_readiness_button.text() == "检查本地模型是否就绪"
    assert settings.validate_http_profiles_button.text() == "校验在线 API 配置"
    assert settings.http_adapter_path_browse_button.text() == "选择 adapter 配置文件"
    assert settings.save_adapter_profile_button.text() == "保存 adapter 配置"
    assert settings.load_adapter_profiles_button.text() == "加载 adapter 列表"
    assert settings.readiness_results_table.horizontalHeaderItem(0).text() == "阶段"
    assert settings.readiness_results_table.horizontalHeaderItem(1).text() == "服务"
    assert settings.advanced_group.title() == "高级配置（本地命令 / 在线 API）"
    assert settings.advanced_group.isCheckable() is False
    assert settings.validate_http_profiles_button.isEnabled() is True
    assert settings.separation_profile_path_edit.placeholderText() == (
        "例如：examples/http_separation_profile.example.json"
    )
    assert settings.asr_profile_path_edit.placeholderText() == (
        "例如：examples/http_asr_profile.example.json"
    )
    assert settings.diarization_profile_path_edit.placeholderText() == (
        "例如：examples/http_diarization_profile.example.json"
    )
    assert settings.translation_profile_path_edit.placeholderText() == (
        "例如：examples/http_translation_lm_studio_qwen36_35b.example.json"
    )
    assert settings.tts_profile_path_edit.placeholderText() == (
        "例如：examples/http_tts_profile.example.json"
    )
    assert settings.translation_vars_edit.placeholderText() == (
        "例如：api_key=lm-studio,temperature=0.2"
    )
    assert settings.file_upload_fields_edit.placeholderText() == "例如：audio=audio_path"


def test_model_settings_warns_when_saving_adapter_without_path(qtbot) -> None:
    from ivo.ui.model_settings import ModelSettings

    settings = ModelSettings()
    qtbot.addWidget(settings)

    settings.save_adapter_profile_button.click()

    assert settings.model_diagnostics_list.item(0).text() == "adapter 保存失败：请先选择配置文件"


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


def test_model_settings_browse_http_adapter_store(monkeypatch, qtbot, tmp_path) -> None:
    from ivo.ui.model_settings import ModelSettings

    store_path = tmp_path / "http-adapters.json"
    monkeypatch.setattr(
        "ivo.ui.model_settings.QFileDialog.getSaveFileName",
        lambda *args, **kwargs: (str(store_path), "JSON files (*.json)"),
    )

    settings = ModelSettings()
    qtbot.addWidget(settings)

    settings.http_adapter_path_browse_button.click()

    assert settings.http_adapter_path_edit.text() == str(store_path)


def test_model_settings_loads_local_command_profile_summary(qtbot, tmp_path) -> None:
    import json

    from ivo.ui.model_settings import ModelSettings

    profiles_path = tmp_path / "profiles.json"
    profiles_path.write_text(
        json.dumps(
            {
                "separation": {
                    "id": "sep",
                    "stage": "separation",
                    "command": ["sep"],
                    "output_json_path": "sep.json",
                },
                "asr": {
                    "id": "asr",
                    "stage": "asr",
                    "command": ["asr"],
                    "output_json_path": "asr.json",
                },
                "diarization": {
                    "id": "dia",
                    "stage": "diarization",
                    "command": ["dia"],
                    "output_json_path": "dia.json",
                },
                "tts": {
                    "id": "tts",
                    "stage": "tts",
                    "command": ["tts"],
                    "output_json_path": "tts.json",
                },
            }
        ),
        encoding="utf-8",
    )
    settings = ModelSettings()
    qtbot.addWidget(settings)

    settings.load_local_command_profile_summary(profiles_path)

    assert settings.local_profile_summary_list.count() == 5
    assert settings.local_profile_summary_list.item(0).text() == "separation: local / sep"
    assert settings.local_profile_summary_list.item(2).text() == "diarization: local / dia"
    assert settings.local_profile_summary_list.item(3).text() == "translation: mock / target-text overrides"


def test_model_settings_profile_summary_shows_http_overrides(qtbot, tmp_path) -> None:
    import json

    from ivo.ui.model_settings import ModelSettings

    profiles_path = tmp_path / "profiles.json"
    profiles_path.write_text(
        json.dumps(
            {
                "separation": {
                    "id": "sep",
                    "stage": "separation",
                    "command": ["sep"],
                    "output_json_path": "sep.json",
                },
                "asr": {
                    "id": "asr",
                    "stage": "asr",
                    "command": ["asr"],
                    "output_json_path": "asr.json",
                },
                "tts": {
                    "id": "tts",
                    "stage": "tts",
                    "command": ["tts"],
                    "output_json_path": "tts.json",
                },
            }
        ),
        encoding="utf-8",
    )
    translation_profile = tmp_path / "translation.json"
    translation_profile.write_text(
        json.dumps(
            {
                "id": "translator",
                "stage": "translation",
                "method": "POST",
                "url": "https://api.example.test/translate",
                "headers": {},
                "request_template": {"prompt": "{{ prompt }}"},
                "response_mapping": {"target_text": "$.text"},
            }
        ),
        encoding="utf-8",
    )
    settings = ModelSettings()
    qtbot.addWidget(settings)
    settings.translation_profile_path_edit.setText(str(translation_profile))

    settings.load_local_command_profile_summary(profiles_path)

    texts = [
        settings.local_profile_summary_list.item(index).text()
        for index in range(settings.local_profile_summary_list.count())
    ]
    assert "translation: http / translator" in texts
    assert "tts: local / tts" in texts


def test_model_settings_validates_local_command_profiles(qtbot, tmp_path) -> None:
    import json

    from ivo.ui.model_settings import ModelSettings

    profiles_path = tmp_path / "profiles.json"
    profiles_path.write_text(
        json.dumps(
            {
                "separation": {
                    "id": "sep",
                    "stage": "separation",
                    "command": ["python", "sep.py", "--out", "{{ output_json_path }}"],
                    "output_json_path": "sep.json",
                },
                "asr": {
                    "id": "asr",
                    "stage": "asr",
                    "command": ["python", "asr.py", "--out", "{{ output_json_path }}"],
                    "output_json_path": "asr.json",
                },
                "tts": {
                    "id": "tts",
                    "stage": "tts",
                    "command": ["python", "tts.py", "--text", "{{ segment_text }}"],
                    "output_json_path": "tts.json",
                },
            }
        ),
        encoding="utf-8",
    )
    settings = ModelSettings()
    qtbot.addWidget(settings)
    settings.local_command_profiles_path_edit.setText(str(profiles_path))

    settings.validate_local_profiles_button.click()

    texts = [
        settings.local_profile_summary_list.item(index).text()
        for index in range(settings.local_profile_summary_list.count())
    ]
    assert "校验：失败" in texts
    assert "错误：tts command should include {{ output_json_path }}" in texts


def test_model_settings_loads_model_diagnostics(monkeypatch, qtbot, tmp_path) -> None:
    from ivo.ui.model_settings import ModelSettings

    monkeypatch.delenv("HF_TOKEN", raising=False)
    (tmp_path / "models" / "asr" / "faster-whisper-large-v3").mkdir(parents=True)
    settings = ModelSettings()
    qtbot.addWidget(settings)

    settings.load_model_diagnostics(tmp_path / "models")

    texts = [
        settings.model_diagnostics_list.item(index).text()
        for index in range(settings.model_diagnostics_list.count())
    ]
    assert any("asr / faster-whisper" in text and "模型目录：已找到" in text for text in texts)
    assert any("tts / CosyVoice" in text for text in texts)
    assert any("diarization / pyannote.audio" in text and "环境变量：未设置" in text for text in texts)


def test_model_settings_refresh_button_loads_model_diagnostics(qtbot, tmp_path) -> None:
    from ivo.ui.model_settings import ModelSettings

    models_dir = tmp_path / "models"
    (models_dir / "tts" / "Fun-CosyVoice3-0.5B").mkdir(parents=True)
    settings = ModelSettings()
    qtbot.addWidget(settings)
    settings.local_model_path_edit.setText(str(models_dir))

    settings.refresh_model_diagnostics_button.click()

    texts = [
        settings.model_diagnostics_list.item(index).text()
        for index in range(settings.model_diagnostics_list.count())
    ]
    assert any("tts / CosyVoice" in text and "模型目录：已找到" in text for text in texts)


def test_model_settings_checks_local_readiness_from_profiles(qtbot, tmp_path) -> None:
    from ivo.ui.model_settings import ModelSettings

    settings = ModelSettings()
    qtbot.addWidget(settings)
    settings.local_model_path_edit.setText(str(tmp_path / "models"))
    settings.local_command_profiles_path_edit.setText(
        str("examples/local_command_profiles.real_dry_run.json")
    )

    settings.check_local_readiness_button.click()

    texts = [
        settings.model_diagnostics_list.item(index).text()
        for index in range(settings.model_diagnostics_list.count())
    ]
    assert "就绪检查：通过" in texts
    assert any("跳过 dry-run：asr:faster-whisper-dry-run" in text for text in texts)


def test_model_settings_reports_local_readiness_gaps(qtbot, tmp_path) -> None:
    from ivo.ui.model_settings import ModelSettings

    settings = ModelSettings()
    qtbot.addWidget(settings)
    settings.local_model_path_edit.setText(str(tmp_path / "models"))
    settings.local_command_profiles_path_edit.setText(
        str("examples/local_command_profiles.real_tts_cosyvoice.json")
    )

    settings.check_local_readiness_button.click()

    texts = [
        settings.model_diagnostics_list.item(index).text()
        for index in range(settings.model_diagnostics_list.count())
    ]
    assert "就绪检查：失败" in texts
    assert any(text.startswith("缺失：tts/CosyVoice:") for text in texts)


def test_model_settings_writes_local_model_setup_script(qtbot, tmp_path) -> None:
    from ivo.ui.model_settings import ModelSettings

    models_dir = tmp_path / "models"
    output = tmp_path / "scripts" / "setup-local-models.ps1"
    settings = ModelSettings()
    qtbot.addWidget(settings)
    settings.local_model_path_edit.setText(str(models_dir))
    settings.setup_script_path_edit.setText(str(output))

    settings.write_model_setup_script_button.click()

    assert output.is_file()
    script = output.read_text(encoding="utf-8")
    assert "asr / faster-whisper" in script
    assert str(models_dir / "asr" / "faster-whisper-large-v3") in script
    texts = [
        settings.model_diagnostics_list.item(index).text()
        for index in range(settings.model_diagnostics_list.count())
    ]
    assert any(f"安装脚本已生成：{output}" in text for text in texts)
