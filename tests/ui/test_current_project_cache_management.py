from __future__ import annotations

from pathlib import Path


def test_current_project_refreshes_from_disk_when_entering_page(qtbot, tmp_path: Path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.ui.main_window import MainWindow

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    project = DubbingProject.create(
        tmp_path / "Episode.ivoproj",
        name="Episode",
        source_language="ja",
        target_language="zh",
        source_media=source,
    )

    window = MainWindow()
    qtbot.addWidget(window)
    window.open_project_path(project.path)

    assert window.project_overview.status_label.text() == "未开始"

    output = project.path / "renders" / "local-preview.mp4"
    output.write_bytes(b"video")
    project.jobs.mark_completed("export")
    project.mark_generation_completed(elapsed_seconds=12)

    window._reload_current_project()
    window._refresh_current_project_view()

    assert window.project_overview.status_label.text() == "已完成"
    assert window.project_overview.open_output_button.isEnabled() is True


def test_generation_started_refreshes_current_project_overview(qtbot, tmp_path: Path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.ui.main_window import MainWindow

    project = DubbingProject.create(
        tmp_path / "Running.ivoproj",
        name="Running",
        source_language="en",
        target_language="zh",
    )
    window = MainWindow()
    qtbot.addWidget(window)
    window.open_project_path(project.path)

    window._mark_generation_started()

    assert window.project_overview.status_label.text() == "生成中"
    assert window.project_overview.primary_action_button.text() == "查看进度"
