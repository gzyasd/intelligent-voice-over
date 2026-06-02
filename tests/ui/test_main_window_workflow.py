from __future__ import annotations


def test_main_window_creates_project_from_inputs(qtbot, tmp_path) -> None:
    from ivo.ui.main_window import MainWindow

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    window = MainWindow()
    qtbot.addWidget(window)

    project = window.create_project_from_inputs(
        project_name="Episode 01",
        source_video=source,
        output_dir=tmp_path,
        source_language="en",
    )

    assert project.path == tmp_path / "Episode 01.ivoproj"
    assert window.current_project == project
    assert window.source_video_path == source
    assert window.progress_label.text() == "项目已创建"


def test_main_window_runs_mock_preview_and_refreshes_timeline(qtbot, tmp_path) -> None:
    from ivo.ui.main_window import MainWindow

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    window = MainWindow()
    qtbot.addWidget(window)
    window.create_project_from_inputs(
        project_name="Episode 01",
        source_video=source,
        output_dir=tmp_path,
        source_language="en",
    )

    result = window.run_mock_preview()

    assert result.final_video.is_file()
    assert window.progress_label.text() == "mock 预览已完成"
    assert window.timeline_editor.table.rowCount() == 1
    assert window.timeline_editor.table.item(0, 3).text() == "嗯，你好。"
