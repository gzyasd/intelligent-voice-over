from __future__ import annotations

from pathlib import Path


def test_main_window_opens_project_from_project_library_signal(qtbot, tmp_path: Path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.ui.main_window import MainWindow

    project = DubbingProject.create(
        tmp_path / "Episode 01.ivoproj",
        name="Episode 01",
        source_language="ja",
        target_language="zh",
    )
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_library_page.open_project_requested.emit(project.path)

    assert window.current_project is not None
    assert window.current_project.path == project.path
    assert window.project_overview.project_name_label.text() == "Episode 01"
    assert window.app_shell.current_page_id() == "current"


def test_main_window_project_library_opens_folder_via_shell(
    monkeypatch,
    qtbot,
    tmp_path: Path,
) -> None:
    from ivo.ui.main_window import MainWindow

    opened: list[Path] = []
    window = MainWindow()
    qtbot.addWidget(window)
    monkeypatch.setattr(window, "open_path_in_shell", opened.append)

    window.project_library_page.open_folder_requested.emit(tmp_path)

    assert opened == [tmp_path]


def test_main_window_project_library_empty_actions_call_existing_flows(
    monkeypatch,
    qtbot,
) -> None:
    from ivo.ui.main_window import MainWindow

    created: list[bool] = []
    opened: list[bool] = []
    window = MainWindow()
    qtbot.addWidget(window)
    monkeypatch.setattr(window, "open_project_wizard", lambda: created.append(True))
    monkeypatch.setattr(window, "open_existing_project", lambda: opened.append(True))

    window.project_library_page.create_project_requested.emit()
    window.project_library_page.open_existing_requested.emit()

    assert created == [True]
    assert opened == [True]
