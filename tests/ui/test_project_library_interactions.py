from __future__ import annotations

from pathlib import Path


def test_project_library_page_emits_card_actions(qtbot, tmp_path: Path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.project_library import scan_project_library
    from ivo.ui.project_library_page import ProjectLibraryPage

    project = DubbingProject.create(
        tmp_path / "runs" / "Episode 01.ivoproj",
        name="Episode 01",
        source_language="ja",
        target_language="zh",
    )
    opened: list[Path] = []
    folders: list[Path] = []
    page = ProjectLibraryPage()
    qtbot.addWidget(page)
    page.open_project_requested.connect(opened.append)
    page.open_folder_requested.connect(folders.append)
    page.set_projects(scan_project_library(tmp_path / "runs", recent_projects=[]))

    page.open_project_buttons[0].click()
    page.open_folder_buttons[0].click()

    assert opened == [project.path]
    assert folders == [project.path]


def test_project_library_page_emits_empty_state_actions(qtbot) -> None:
    from ivo.ui.project_library_page import ProjectLibraryPage

    created: list[bool] = []
    open_existing: list[bool] = []
    page = ProjectLibraryPage()
    qtbot.addWidget(page)
    page.create_project_requested.connect(lambda: created.append(True))
    page.open_existing_requested.connect(lambda: open_existing.append(True))
    page.set_projects([])

    page.empty_state.action_button.click()
    page.open_existing_project_button.click()

    assert created == [True]
    assert open_existing == [True]
