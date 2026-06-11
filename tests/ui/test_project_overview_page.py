from __future__ import annotations


def test_project_overview_page_shows_empty_state_and_start_action(qtbot) -> None:
    from ivo.ui.project_overview_page import ProjectOverviewPage

    page = ProjectOverviewPage()
    qtbot.addWidget(page)

    assert page.project_name_label.text() == "还没有打开项目"
    assert page.primary_action_button.text() == "新建配音项目"


def test_project_overview_page_shows_project_summary(qtbot, tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.ui.project_overview_page import ProjectOverviewPage

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    project = DubbingProject.create(
        tmp_path / "episode.ivoproj",
        name="Episode 01",
        source_language="ja",
        target_language="zh",
        source_video=source,
    )

    page = ProjectOverviewPage()
    qtbot.addWidget(page)
    page.set_project(project)

    assert page.project_name_label.text() == "Episode 01"
    assert page.source_video_label.text().endswith("episode.mp4")
    assert page.language_label.text() == "日语 -> 中文"
    assert page.status_label.text() == "未开始"
    assert page.primary_action_button.text() == "开始生成"


def test_project_overview_page_marks_failed_project(qtbot, tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.ui.project_overview_page import ProjectOverviewPage

    project = DubbingProject.create(
        tmp_path / "failed.ivoproj",
        name="Failed",
        source_language="en",
        target_language="zh",
    )
    project.jobs.mark_failed("tts", "voice model failed")

    page = ProjectOverviewPage()
    qtbot.addWidget(page)
    page.set_project(project)

    assert page.status_label.text() == "生成失败"
    assert page.primary_action_button.text() == "重试失败阶段"


def test_main_window_updates_project_overview_after_project_creation(
    monkeypatch,
    qtbot,
    tmp_path,
) -> None:
    from ivo.ui.main_window import MainWindow

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    started: list[bool] = []
    window = MainWindow()
    qtbot.addWidget(window)
    monkeypatch.setattr(window, "start_local_preview_background", lambda: started.append(True))

    window.create_project_from_inputs(
        project_name="Episode 01",
        source_video=source,
        output_dir=tmp_path,
        source_language="ko",
    )

    assert window.project_overview.project_name_label.text() == "Episode 01"
    assert window.project_overview.language_label.text() == "韩语 -> 中文"

    window.project_overview.primary_action_button.click()

    assert started == [True]


def test_main_window_project_overview_open_buttons_use_shell(
    monkeypatch,
    qtbot,
    tmp_path,
) -> None:
    from ivo.core.project import DubbingProject
    from ivo.ui.main_window import MainWindow

    project = DubbingProject.create(
        tmp_path / "complete.ivoproj",
        name="Complete",
        source_language="en",
        target_language="zh",
    )
    final_video = project.path / "renders" / "local-preview.mp4"
    final_video.write_bytes(b"video")
    project.jobs.mark_completed("export", "completed")
    opened = []
    window = MainWindow()
    qtbot.addWidget(window)
    monkeypatch.setattr(window, "open_path_in_shell", opened.append)

    window.open_project_path(project.path)
    window.project_overview.open_folder_button.click()
    window.project_overview.open_video_button.click()
    window.project_overview.primary_action_button.click()

    assert opened == [project.path, final_video, final_video]


def test_project_overview_running_primary_action_shows_progress(qtbot, tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.ui.main_window import MainWindow

    project = DubbingProject.create(
        tmp_path / "running.ivoproj",
        name="Running",
        source_language="en",
        target_language="zh",
    )
    project.jobs.mark_running("tts")
    window = MainWindow()
    qtbot.addWidget(window)
    window.open_project_path(project.path)

    window.project_overview.primary_action_button.click()

    assert window.project_workspace_tabs.currentWidget() is window.generation_progress
