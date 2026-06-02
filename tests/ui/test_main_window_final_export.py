from __future__ import annotations


def test_export_dialog_browses_output_path(monkeypatch, qtbot, tmp_path) -> None:
    from ivo.ui.export_dialog import ExportDialog

    output = tmp_path / "final.mp4"
    monkeypatch.setattr(
        "ivo.ui.export_dialog.QFileDialog.getSaveFileName",
        lambda *args, **kwargs: (str(output), "MP4 video (*.mp4)"),
    )

    dialog = ExportDialog()
    qtbot.addWidget(dialog)
    dialog.browse_output_path()

    assert dialog.output_path() == output


def test_main_window_runs_final_export_from_dialog(monkeypatch, qtbot, tmp_path) -> None:
    from ivo.ui.export_dialog import ExportDialog
    from ivo.ui.main_window import MainWindow

    source_video, project, background, generated_audio = _create_exportable_project(tmp_path)
    captured: dict[str, object] = {}

    def fake_export_dubbed_video(request, confirmation):
        captured["request"] = request
        captured["confirmation"] = confirmation
        request.output_path.write_bytes(b"final")
        return request.output_path

    monkeypatch.setattr("ivo.ui.main_window.export_dubbed_video", fake_export_dubbed_video)

    window = MainWindow()
    qtbot.addWidget(window)
    window.current_project = project
    window.source_video_path = source_video
    dialog = ExportDialog()
    qtbot.addWidget(dialog)
    dialog.confirmation_checkbox.setChecked(True)
    dialog.watermark_checkbox.setChecked(True)
    dialog.watermark_text.setText("AI Dubbed")
    dialog.output_path_edit.setText(str(tmp_path / "final.mp4"))

    output = window.run_final_export(dialog)

    request = captured["request"]
    confirmation = captured["confirmation"]
    assert output.read_bytes() == b"final"
    assert confirmation.accepted is True
    assert request.source_video == source_video
    assert request.background_audio == background
    assert request.segment_audio[0].path == generated_audio
    assert request.segment_audio[0].start_ms == 250
    assert request.metadata["ai_dubbing"] == "true"
    assert request.watermark_text == "AI Dubbed"
    assert window.progress_label.text() == "\u6700\u7ec8\u5bfc\u51fa\u5df2\u5b8c\u6210"


def test_main_window_builds_background_worker_for_final_export(monkeypatch, qtbot, tmp_path) -> None:
    from ivo.ui.export_dialog import ExportDialog
    from ivo.ui.main_window import MainWindow

    source_video, project, _background, generated_audio = _create_exportable_project(tmp_path)
    captured: dict[str, object] = {}

    def fake_export_dubbed_video(request, confirmation):
        captured["request"] = request
        captured["confirmation"] = confirmation
        request.output_path.write_bytes(b"final")
        return request.output_path

    monkeypatch.setattr("ivo.ui.main_window.export_dubbed_video", fake_export_dubbed_video)

    window = MainWindow()
    qtbot.addWidget(window)
    window.current_project = project
    window.source_video_path = source_video
    dialog = ExportDialog()
    qtbot.addWidget(dialog)
    dialog.confirmation_checkbox.setChecked(True)
    dialog.output_path_edit.setText(str(tmp_path / "final.mp4"))

    worker = window.create_final_export_worker(dialog)

    assert window.export_button.isEnabled() is False
    assert window.progress_label.text() == "\u6b63\u5728\u6700\u7ec8\u5bfc\u51fa"

    worker.run()
    window.handle_final_export_succeeded()

    request = captured["request"]
    confirmation = captured["confirmation"]
    assert confirmation.accepted is True
    assert request.segment_audio[0].path == generated_audio
    assert worker.result.read_bytes() == b"final"
    assert window.export_button.isEnabled() is True
    assert window.progress_label.text() == "\u6700\u7ec8\u5bfc\u51fa\u5df2\u5b8c\u6210"


def _create_exportable_project(tmp_path):
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment

    source_video = tmp_path / "episode.mp4"
    source_video.write_bytes(b"video")
    project = DubbingProject.create(
        tmp_path / "Episode 01.ivoproj",
        name="Episode 01",
        source_language="en",
        target_language="zh",
        source_video=source_video,
    )
    background = project.path / "work" / "background.wav"
    background.write_bytes(b"background")
    generated_dir = project.path / "work" / "generated_segments"
    generated_dir.mkdir(parents=True, exist_ok=True)
    generated_audio = generated_dir / "seg-001.wav"
    generated_audio.write_bytes(b"speech")
    project.timeline.add_segment(
        DubbingSegment(
            id="seg-001",
            start_ms=250,
            end_ms=1_250,
            speaker_id="speaker-1",
            source_language="en",
            source_text="Well, hi.",
            target_language="zh",
            target_text="\u4f60\u597d\u3002",
            emotion="warm",
            status="rendered",
        )
    )
    return source_video, project, background, generated_audio
