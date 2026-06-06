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
    assert window.progress_label.text() == "项目已创建。下一步：点击“开始生成配音（完整流程）”。"


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


def test_main_window_writes_evaluation_report(qtbot, tmp_path) -> None:
    from ivo.core.timeline import DubbingSegment
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
            status="rendered",
            quality_flags=["duration_ok"],
        )
    )

    report_path = window.write_evaluation_report()

    assert report_path == project.path / "renders" / "evaluation-report.md"
    assert report_path.is_file()
    assert "| duration_ok | 1 |" in report_path.read_text(encoding="utf-8")
    assert window.progress_label.text() == f"评估报告已生成: {report_path}"
