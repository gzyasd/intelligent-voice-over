from __future__ import annotations

import json


def test_main_window_runs_local_preview_from_model_settings(monkeypatch, qtbot, tmp_path) -> None:
    from ivo.pipeline.local_command_preview import LocalCommandPreviewResult
    from ivo.ui.main_window import MainWindow

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    profiles_path = _write_local_profiles(tmp_path)
    translation_profile_path = _write_translation_profile(tmp_path)
    captured: dict[str, object] = {}

    def fake_run_local_command_preview(project, **kwargs):
        captured["profiles"] = kwargs["profiles"]
        captured["translation_adapter"] = kwargs["translation_adapter"]
        _add_rendered_segment(project)
        final_video = project.path / "renders" / "local-preview.mp4"
        final_video.write_bytes(b"preview")
        return LocalCommandPreviewResult(
            final_video=final_video,
            metadata={"ai_dubbing": "true"},
            generated_segments=[],
        )

    monkeypatch.setattr("ivo.ui.main_window.run_local_command_preview", fake_run_local_command_preview)

    window = MainWindow()
    qtbot.addWidget(window)
    window.create_project_from_inputs(
        project_name="Episode 01",
        source_video=source,
        output_dir=tmp_path,
        source_language="en",
    )
    window.model_settings.local_command_profiles_path_edit.setText(str(profiles_path))
    window.model_settings.translation_profile_path_edit.setText(str(translation_profile_path))
    window.model_settings.translation_vars_edit.setText("api_key=test-token")

    result = window.run_local_preview()

    adapter = captured["translation_adapter"]
    assert result.final_video.is_file()
    assert captured["profiles"].tts.id == "tts"
    assert adapter.profile.id == "translator"
    assert adapter.extra == {"api_key": "test-token"}
    assert window.timeline_editor.table.rowCount() == 1
    assert window.progress_label.text() == "本地命令预览已完成"


def test_model_settings_panel_shows_structured_readiness_results(qtbot) -> None:
    from ivo.ui.model_settings import ModelSettingsPanel

    panel = ModelSettingsPanel()
    qtbot.addWidget(panel)

    panel.show_readiness_results(
        [
            {
                "stage": "tts",
                "provider": "CosyVoice",
                "status": "missing",
                "message": "cosyvoice package is missing",
            }
        ]
    )

    summary = panel.readiness_summary_text()
    assert "CosyVoice" in summary
    assert "缺失" in summary
    assert "cosyvoice package is missing" in summary


def test_main_window_saves_selected_profile_paths_to_project_settings(
    monkeypatch,
    qtbot,
    tmp_path,
) -> None:
    from ivo.pipeline.local_command_preview import LocalCommandPreviewResult
    from ivo.ui.main_window import MainWindow

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    profiles_path = _write_local_profiles(tmp_path)
    translation_profile_path = _write_translation_profile(tmp_path)

    def fake_run_local_command_preview(project, **kwargs):
        final_video = project.path / "renders" / "local-preview.mp4"
        final_video.write_bytes(b"preview")
        return LocalCommandPreviewResult(
            final_video=final_video,
            metadata={"ai_dubbing": "true"},
            generated_segments=[],
        )

    monkeypatch.setattr("ivo.ui.main_window.run_local_command_preview", fake_run_local_command_preview)

    window = MainWindow()
    qtbot.addWidget(window)
    project = window.create_project_from_inputs(
        project_name="Episode 01",
        source_video=source,
        output_dir=tmp_path,
        source_language="en",
    )
    window.model_settings.local_command_profiles_path_edit.setText(str(profiles_path))
    window.model_settings.translation_profile_path_edit.setText(str(translation_profile_path))

    window.run_local_preview()

    saved = project.settings.load().profiles
    assert saved.local_command_profiles_path == str(profiles_path)
    assert saved.translation_profile_path == str(translation_profile_path)


def test_main_window_builds_background_worker_for_local_preview(monkeypatch, qtbot, tmp_path) -> None:
    from ivo.pipeline.local_command_preview import LocalCommandPreviewResult
    from ivo.ui.main_window import MainWindow

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    profiles_path = _write_local_profiles(tmp_path)

    def fake_run_local_command_preview(project, **kwargs):
        _add_rendered_segment(project)
        final_video = project.path / "renders" / "local-preview.mp4"
        final_video.write_bytes(b"preview")
        return LocalCommandPreviewResult(
            final_video=final_video,
            metadata={"ai_dubbing": "true"},
            generated_segments=[],
        )

    monkeypatch.setattr("ivo.ui.main_window.run_local_command_preview", fake_run_local_command_preview)

    window = MainWindow()
    qtbot.addWidget(window)
    window.create_project_from_inputs(
        project_name="Episode 01",
        source_video=source,
        output_dir=tmp_path,
        source_language="en",
    )
    window.model_settings.local_command_profiles_path_edit.setText(str(profiles_path))

    worker = window.create_local_preview_worker()
    assert window.local_preview_button.isEnabled() is False

    worker.run()
    window.handle_local_preview_succeeded()

    assert worker.result.final_video.is_file()
    assert window.local_preview_button.isEnabled() is True
    assert window.timeline_editor.table.rowCount() == 1
    assert window.progress_label.text() == "本地命令预览已完成"


def test_main_window_local_preview_button_starts_background_worker(monkeypatch, qtbot) -> None:
    from ivo.ui.main_window import MainWindow

    started: list[bool] = []

    window = MainWindow()
    qtbot.addWidget(window)

    def fake_start_local_preview_background():
        started.append(True)

    monkeypatch.setattr(window, "start_local_preview_background", fake_start_local_preview_background)

    window.local_preview_button.click()

    assert started == [True]


def test_main_window_runs_local_preview_with_http_tts_profile(monkeypatch, qtbot, tmp_path) -> None:
    from ivo.pipeline.local_command_preview import LocalCommandPreviewResult
    from ivo.ui.main_window import MainWindow

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    profiles_path = _write_local_profiles(tmp_path)
    tts_profile_path = _write_tts_profile(tmp_path)
    captured: dict[str, object] = {}

    def fake_run_local_command_preview(project, **kwargs):
        captured["tts_adapter"] = kwargs["tts_adapter"]
        _add_rendered_segment(project)
        final_video = project.path / "renders" / "local-preview.mp4"
        final_video.write_bytes(b"preview")
        return LocalCommandPreviewResult(
            final_video=final_video,
            metadata={"ai_dubbing": "true"},
            generated_segments=[],
        )

    monkeypatch.setattr("ivo.ui.main_window.run_local_command_preview", fake_run_local_command_preview)

    window = MainWindow()
    qtbot.addWidget(window)
    window.create_project_from_inputs(
        project_name="Episode 01",
        source_video=source,
        output_dir=tmp_path,
        source_language="en",
    )
    window.model_settings.local_command_profiles_path_edit.setText(str(profiles_path))
    window.model_settings.tts_profile_path_edit.setText(str(tts_profile_path))
    window.model_settings.tts_vars_edit.setText("api_key=test-token")

    result = window.run_local_preview()

    adapter = captured["tts_adapter"]
    assert result.final_video.is_file()
    assert adapter.__class__.__name__ == "HttpTtsAdapter"
    assert adapter.profile.id == "online-tts"
    assert adapter.extra == {"api_key": "test-token"}


def test_main_window_runs_local_preview_with_http_asr_profile(monkeypatch, qtbot, tmp_path) -> None:
    from ivo.pipeline.local_command_preview import LocalCommandPreviewResult
    from ivo.ui.main_window import MainWindow

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    profiles_path = _write_local_profiles(tmp_path)
    asr_profile_path = _write_asr_profile(tmp_path)
    captured: dict[str, object] = {}

    def fake_run_local_command_preview(project, **kwargs):
        captured["asr_adapter"] = kwargs["asr_adapter"]
        _add_rendered_segment(project)
        final_video = project.path / "renders" / "local-preview.mp4"
        final_video.write_bytes(b"preview")
        return LocalCommandPreviewResult(
            final_video=final_video,
            metadata={"ai_dubbing": "true"},
            generated_segments=[],
        )

    monkeypatch.setattr("ivo.ui.main_window.run_local_command_preview", fake_run_local_command_preview)

    window = MainWindow()
    qtbot.addWidget(window)
    window.create_project_from_inputs(
        project_name="Episode 01",
        source_video=source,
        output_dir=tmp_path,
        source_language="en",
    )
    window.model_settings.local_command_profiles_path_edit.setText(str(profiles_path))
    window.model_settings.asr_profile_path_edit.setText(str(asr_profile_path))
    window.model_settings.asr_vars_edit.setText("api_key=test-token")

    result = window.run_local_preview()

    adapter = captured["asr_adapter"]
    assert result.final_video.is_file()
    assert adapter.__class__.__name__ == "HttpAsrAdapter"
    assert adapter.profile.id == "online-asr"
    assert adapter.extra == {"api_key": "test-token"}


def test_main_window_runs_local_preview_with_http_separation_profile(
    monkeypatch,
    qtbot,
    tmp_path,
) -> None:
    from ivo.pipeline.local_command_preview import LocalCommandPreviewResult
    from ivo.ui.main_window import MainWindow

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    profiles_path = _write_local_profiles(tmp_path)
    separation_profile_path = _write_separation_profile(tmp_path)
    captured: dict[str, object] = {}

    def fake_run_local_command_preview(project, **kwargs):
        captured["separation_adapter"] = kwargs["separation_adapter"]
        _add_rendered_segment(project)
        final_video = project.path / "renders" / "local-preview.mp4"
        final_video.write_bytes(b"preview")
        return LocalCommandPreviewResult(
            final_video=final_video,
            metadata={"ai_dubbing": "true"},
            generated_segments=[],
        )

    monkeypatch.setattr("ivo.ui.main_window.run_local_command_preview", fake_run_local_command_preview)

    window = MainWindow()
    qtbot.addWidget(window)
    window.create_project_from_inputs(
        project_name="Episode 01",
        source_video=source,
        output_dir=tmp_path,
        source_language="en",
    )
    window.model_settings.local_command_profiles_path_edit.setText(str(profiles_path))
    window.model_settings.separation_profile_path_edit.setText(str(separation_profile_path))
    window.model_settings.separation_vars_edit.setText("api_key=test-token")

    result = window.run_local_preview()

    adapter = captured["separation_adapter"]
    assert result.final_video.is_file()
    assert adapter.__class__.__name__ == "HttpSeparationAdapter"
    assert adapter.profile.id == "online-separation"
    assert adapter.extra == {"api_key": "test-token"}


def test_main_window_runs_local_preview_with_http_diarization_profile(
    monkeypatch,
    qtbot,
    tmp_path,
) -> None:
    from ivo.pipeline.local_command_preview import LocalCommandPreviewResult
    from ivo.ui.main_window import MainWindow

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    profiles_path = _write_local_profiles(tmp_path)
    diarization_profile_path = _write_diarization_profile(tmp_path)
    captured: dict[str, object] = {}

    def fake_run_local_command_preview(project, **kwargs):
        captured["diarization_adapter"] = kwargs["diarization_adapter"]
        _add_rendered_segment(project)
        final_video = project.path / "renders" / "local-preview.mp4"
        final_video.write_bytes(b"preview")
        return LocalCommandPreviewResult(
            final_video=final_video,
            metadata={"ai_dubbing": "true"},
            generated_segments=[],
        )

    monkeypatch.setattr("ivo.ui.main_window.run_local_command_preview", fake_run_local_command_preview)

    window = MainWindow()
    qtbot.addWidget(window)
    window.create_project_from_inputs(
        project_name="Episode 01",
        source_video=source,
        output_dir=tmp_path,
        source_language="en",
    )
    window.model_settings.local_command_profiles_path_edit.setText(str(profiles_path))
    window.model_settings.diarization_profile_path_edit.setText(str(diarization_profile_path))
    window.model_settings.diarization_vars_edit.setText("api_key=test-token")

    result = window.run_local_preview()

    adapter = captured["diarization_adapter"]
    assert result.final_video.is_file()
    assert adapter.__class__.__name__ == "HttpDiarizationAdapter"
    assert adapter.profile.id == "online-diarization"
    assert adapter.extra == {"api_key": "test-token"}


def _write_local_profiles(tmp_path):
    profiles_path = tmp_path / "local-profiles.json"
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
    return profiles_path


def _write_translation_profile(tmp_path):
    translation_profile_path = tmp_path / "translation.json"
    translation_profile_path.write_text(
        json.dumps(
            {
                "id": "translator",
                "stage": "translation",
                "method": "POST",
                "url": "https://api.example.test/translate",
                "headers": {"Authorization": "Bearer {{ api_key }}"},
                "request_template": {"prompt": "{{ prompt }}"},
                "response_mapping": {"target_text": "$.text"},
            }
        ),
        encoding="utf-8",
    )
    return translation_profile_path


def _write_asr_profile(tmp_path):
    asr_profile_path = tmp_path / "asr-http.json"
    asr_profile_path.write_text(
        json.dumps(
            {
                "id": "online-asr",
                "stage": "asr",
                "method": "POST",
                "url": "https://api.example.test/asr",
                "headers": {"Authorization": "Bearer {{ api_key }}"},
                "request_template": {"audio_path": "{{ audio_path }}"},
                "response_mapping": {"segments": "$.segments"},
            }
        ),
        encoding="utf-8",
    )
    return asr_profile_path


def _write_separation_profile(tmp_path):
    separation_profile_path = tmp_path / "separation-http.json"
    separation_profile_path.write_text(
        json.dumps(
            {
                "id": "online-separation",
                "stage": "separation",
                "method": "POST",
                "url": "https://api.example.test/separate",
                "headers": {"Authorization": "Bearer {{ api_key }}"},
                "request_template": {"audio_path": "{{ audio_path }}"},
                "response_mapping": {
                    "vocals_base64": "$.vocals_base64",
                    "background_base64": "$.background_base64",
                },
            }
        ),
        encoding="utf-8",
    )
    return separation_profile_path


def _write_diarization_profile(tmp_path):
    diarization_profile_path = tmp_path / "diarization-http.json"
    diarization_profile_path.write_text(
        json.dumps(
            {
                "id": "online-diarization",
                "stage": "diarization",
                "method": "POST",
                "url": "https://api.example.test/diarize",
                "headers": {"Authorization": "Bearer {{ api_key }}"},
                "request_template": {"audio_path": "{{ audio_path }}"},
                "response_mapping": {"segments": "$.segments"},
            }
        ),
        encoding="utf-8",
    )
    return diarization_profile_path


def _write_tts_profile(tmp_path):
    tts_profile_path = tmp_path / "tts-http.json"
    tts_profile_path.write_text(
        json.dumps(
            {
                "id": "online-tts",
                "stage": "tts",
                "method": "POST",
                "url": "https://api.example.test/tts",
                "headers": {"Authorization": "Bearer {{ api_key }}"},
                "request_template": {"text": "{{ segment_text }}"},
                "response_mapping": {
                    "audio_base64": "$.audio_base64",
                    "duration_ms": "$.duration_ms",
                },
            }
        ),
        encoding="utf-8",
    )
    return tts_profile_path


def _add_rendered_segment(project) -> None:
    from ivo.core.timeline import DubbingSegment

    project.timeline.add_segment(
        DubbingSegment(
            id="seg-001",
            start_ms=0,
            end_ms=1_000,
            speaker_id="speaker-1",
            source_language="en",
            source_text="Well, hi.",
            target_language="zh",
            target_text="你好。",
            emotion="warm",
            status="rendered",
        )
    )
