from __future__ import annotations

from pathlib import Path


def test_project_library_page_lists_project_cards(qtbot, tmp_path: Path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.project_library import scan_project_library
    from ivo.ui.project_library_page import ProjectLibraryPage

    project = DubbingProject.create(
        tmp_path / "runs" / "Episode 01.ivoproj",
        name="Episode 01",
        source_language="ja",
        target_language="zh",
    )
    project.jobs.mark_completed("export", "completed")

    page = ProjectLibraryPage()
    qtbot.addWidget(page)
    page.set_projects(scan_project_library(tmp_path / "runs", recent_projects=[]))

    assert page.project_count() == 1
    assert "Episode 01" in page.summary_text()
    assert "已完成" in page.summary_text()
    assert page.open_project_buttons[0].text() == "打开项目"
    assert page.open_folder_buttons[0].text() == "打开文件夹"


def test_project_library_page_shows_empty_state(qtbot) -> None:
    from ivo.ui.project_library_page import ProjectLibraryPage

    page = ProjectLibraryPage()
    qtbot.addWidget(page)
    page.set_projects([])

    assert page.project_count() == 0
    assert "还没有项目" in page.summary_text()
