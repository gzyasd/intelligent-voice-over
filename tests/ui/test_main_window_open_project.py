from __future__ import annotations


def test_main_window_opens_existing_project_from_directory(monkeypatch, qtbot, tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.ui.main_window import MainWindow

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    project = DubbingProject.create(
        tmp_path / "Episode 01.ivoproj",
        name="Episode 01",
        source_language="en",
        target_language="zh",
        source_media=source,
    )
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
    monkeypatch.setattr(
        "ivo.ui.main_window.QFileDialog.getExistingDirectory",
        lambda *args, **kwargs: str(project.path),
    )

    window = MainWindow()
    qtbot.addWidget(window)

    loaded = window.open_existing_project()

    assert loaded is not None
    assert loaded.path == project.path
    assert window.current_project.path == project.path
    assert window.source_media_path == source
    assert window.timeline_editor.table.rowCount() == 1
    assert window.progress_label.text() == "项目已打开。下一步：点击“开始生成配音（完整流程）”。"


def test_main_window_warns_when_open_project_fails(monkeypatch, qtbot, tmp_path) -> None:
    from ivo.ui.main_window import MainWindow

    missing_project = tmp_path / "missing.ivoproj"
    warnings: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "ivo.ui.main_window.QFileDialog.getExistingDirectory",
        lambda *args, **kwargs: str(missing_project),
    )
    monkeypatch.setattr(
        "ivo.ui.main_window.QMessageBox.warning",
        lambda parent, title, message: warnings.append((title, message)),
    )

    window = MainWindow()
    qtbot.addWidget(window)

    loaded = window.open_existing_project()

    assert loaded is None
    assert warnings
    assert warnings[0][0] == "打开项目失败"
    assert str(missing_project) in warnings[0][1]
