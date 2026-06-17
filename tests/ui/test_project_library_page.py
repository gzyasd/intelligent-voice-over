from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QPushButton


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
    project.mark_generation_completed(elapsed_seconds=30)
    final_output = project.path / "renders" / "local-preview.mp4"
    final_output.write_bytes(b"video")

    page = ProjectLibraryPage()
    qtbot.addWidget(page)
    page.set_projects(scan_project_library(tmp_path / "runs", recent_projects=[]))

    assert page.project_count() == 1
    assert "Episode 01" in page.summary_text()
    assert "已完成" in page.summary_text()
    assert page.open_project_buttons[0].text() == "打开项目"
    assert page.open_folder_buttons[0].text() == "文件夹"


def test_project_library_page_shows_status_and_elapsed_time(qtbot, tmp_path: Path) -> None:
    from ivo.core.project_library import ProjectLibraryItem
    from ivo.ui.project_library_page import ProjectLibraryPage

    page = ProjectLibraryPage()
    qtbot.addWidget(page)
    page.set_projects(
        [
            ProjectLibraryItem(
                name="Episode 02",
                path=tmp_path / "Episode 02.ivoproj",
                source_language="ja",
                target_language="zh",
                updated_at=1,
                status="生成中",
                status_detail="总耗时 12:03",
                elapsed_seconds=723,
            )
        ]
    )

    assert "Episode 02" in page.summary_text()
    assert "生成中" in page.summary_text()
    assert "总耗时 12:03" in page.summary_text()


def test_project_library_page_shows_empty_state(qtbot) -> None:
    from ivo.ui.project_library_page import ProjectLibraryPage

    page = ProjectLibraryPage()
    qtbot.addWidget(page)
    page.set_projects([])

    assert page.project_count() == 0
    assert "还没有项目" in page.summary_text()
    # Scroll area should be hidden when empty
    assert not page._scroll.isVisible()
    # Toolbar and stats should be hidden when no projects
    assert not page._toolbar_widget.isVisible()
    assert not page._stats_widget.isVisible()


def test_project_library_single_project_card_has_fixed_size(qtbot, tmp_path: Path) -> None:
    from ivo.core.project_library import ProjectLibraryItem
    from ivo.ui.project_library_page import ProjectLibraryPage

    page = ProjectLibraryPage()
    page.resize(800, 600)
    qtbot.addWidget(page)
    page.set_projects(
        [
            ProjectLibraryItem(
                name="Solo",
                path=tmp_path / "Solo.ivoproj",
                source_language="en",
                target_language="zh",
                updated_at=1,
                status="未开始",
            )
        ]
    )

    card = page._card_widgets[0]
    assert card.width() == page._CARD_WIDTH
    assert card.height() == page._CARD_HEIGHT


def test_project_library_status_badge_keeps_compact_height(qtbot, tmp_path: Path) -> None:
    from ivo.core.project_library import ProjectLibraryItem
    from ivo.ui.project_library_page import ProjectLibraryPage

    page = ProjectLibraryPage()
    qtbot.addWidget(page)
    page.set_projects(
        [
            ProjectLibraryItem(
                name="BadgeTest",
                path=tmp_path / "BadgeTest.ivoproj",
                source_language="ja",
                target_language="zh",
                updated_at=1,
                status="未开始",
            )
        ]
    )

    card = page._card_widgets[0]
    # Find the status badge (it's the second widget in the header layout)
    header_layout = card.layout().itemAt(0).layout()
    badge_widget = header_layout.itemAt(1).widget()
    assert badge_widget.height() <= 24


def test_project_library_filters_by_status(qtbot, tmp_path: Path) -> None:
    from ivo.core.project_library import ProjectLibraryItem
    from ivo.ui.project_library_page import ProjectLibraryPage

    page = ProjectLibraryPage()
    qtbot.addWidget(page)
    items = [
        ProjectLibraryItem(
            name="Done", path=tmp_path / "Done.ivoproj",
            source_language="ja", target_language="zh",
            updated_at=2, status="已完成",
        ),
        ProjectLibraryItem(
            name="Running", path=tmp_path / "Running.ivoproj",
            source_language="en", target_language="zh",
            updated_at=1, status="生成中",
        ),
    ]
    page.set_projects(items)
    assert page.project_count() == 2

    # Filter to only "生成中"
    page._status_filter.setCurrentText("生成中")
    assert page.project_count() == 1
    assert "Running" in page.summary_text()

    # Reset filter
    page._status_filter.setCurrentText("全部")
    assert page.project_count() == 2


def test_project_library_searches_by_name_and_path(qtbot, tmp_path: Path) -> None:
    from ivo.core.project_library import ProjectLibraryItem
    from ivo.ui.project_library_page import ProjectLibraryPage

    page = ProjectLibraryPage()
    qtbot.addWidget(page)
    items = [
        ProjectLibraryItem(
            name="Alpha", path=tmp_path / "Alpha.ivoproj",
            source_language="ja", target_language="zh",
            updated_at=2, status="已完成",
        ),
        ProjectLibraryItem(
            name="Beta", path=tmp_path / "Beta.ivoproj",
            source_language="en", target_language="zh",
            updated_at=1, status="未开始",
        ),
    ]
    page.set_projects(items)
    assert page.project_count() == 2

    # Search by name
    page._search_edit.setText("Alpha")
    assert page.project_count() == 1
    assert "Alpha" in page.summary_text()

    # Clear search
    page._search_edit.setText("")
    assert page.project_count() == 2


def test_project_library_shows_final_output_action_when_available(qtbot, tmp_path: Path) -> None:
    from ivo.core.project_library import ProjectLibraryItem
    from ivo.ui.project_library_page import ProjectLibraryPage

    page = ProjectLibraryPage()
    qtbot.addWidget(page)
    page.set_projects(
        [
            ProjectLibraryItem(
                name="WithOutput",
                path=tmp_path / "WithOutput.ivoproj",
                source_language="ja",
                target_language="zh",
                updated_at=1,
                status="已完成",
                final_output_path=tmp_path / "renders" / "final.mp4",
            )
        ]
    )

    assert len(page.open_output_buttons) == 1
    assert page.open_output_buttons[0].text() == "成品"


def test_project_library_audio_and_video_items_have_type_labels(qtbot, tmp_path: Path) -> None:
    from ivo.core.project_library import ProjectLibraryItem
    from ivo.ui.project_library_page import ProjectLibraryPage

    page = ProjectLibraryPage()
    qtbot.addWidget(page)
    items = [
        ProjectLibraryItem(
            name="VideoProject", path=tmp_path / "VideoProject.ivoproj",
            content_type="video", source_language="en", target_language="zh",
            updated_at=2, status="已完成",
        ),
        ProjectLibraryItem(
            name="AudioProject", path=tmp_path / "AudioProject.ivoproj",
            content_type="audio", source_language="ja", target_language="zh",
            updated_at=1, status="未开始",
        ),
    ]
    page.set_projects(items)

    # Check that cards contain the correct type+language info
    video_card = page._card_widgets[0]
    audio_card = page._card_widgets[1]

    # Info label is at layout index 1
    video_info = video_card.layout().itemAt(1).widget()
    audio_info = audio_card.layout().itemAt(1).widget()

    assert "视频" in video_info.text()
    assert "音频" in audio_info.text()


def test_project_library_cards_keep_fixed_size_in_grid(qtbot, tmp_path: Path) -> None:
    from ivo.core.project_library import ProjectLibraryItem
    from ivo.ui.project_library_page import ProjectLibraryPage

    page = ProjectLibraryPage()
    page.resize(1200, 800)
    qtbot.addWidget(page)
    items = [
        ProjectLibraryItem(
            name=f"Project{i}", path=tmp_path / f"Project{i}.ivoproj",
            source_language="en", target_language="zh",
            updated_at=float(i), status="已完成",
        )
        for i in range(5)
    ]
    page.set_projects(items)

    # All cards should have the fixed size
    for card in page._card_widgets:
        assert card.width() == page._CARD_WIDTH
        assert card.height() == page._CARD_HEIGHT


def test_project_library_shows_stats(qtbot, tmp_path: Path) -> None:
    from ivo.core.project_library import ProjectLibraryItem
    from ivo.ui.project_library_page import ProjectLibraryPage

    page = ProjectLibraryPage()
    qtbot.addWidget(page)
    items = [
        ProjectLibraryItem(
            name="Done", path=tmp_path / "Done.ivoproj",
            source_language="ja", target_language="zh",
            updated_at=3, status="已完成",
        ),
        ProjectLibraryItem(
            name="Running", path=tmp_path / "Running.ivoproj",
            source_language="en", target_language="zh",
            updated_at=2, status="生成中",
        ),
        ProjectLibraryItem(
            name="Failed", path=tmp_path / "Failed.ivoproj",
            source_language="ko", target_language="zh",
            updated_at=1, status="生成失败",
        ),
    ]
    page.set_projects(items)

    assert page._stat_labels["all"].text() == "全部项目 3"
    assert page._stat_labels["completed"].text() == "已完成 1"
    assert page._stat_labels["running"].text() == "生成中 1"
    assert page._stat_labels["failed"].text() == "生成失败 1"


def test_project_library_output_text_shows_filename(qtbot, tmp_path: Path) -> None:
    from ivo.core.project_library import ProjectLibraryItem
    from ivo.ui.project_library_page import ProjectLibraryPage

    page = ProjectLibraryPage()
    qtbot.addWidget(page)
    page.set_projects(
        [
            ProjectLibraryItem(
                name="WithFile",
                path=tmp_path / "WithFile.ivoproj",
                source_language="ja",
                target_language="zh",
                updated_at=1,
                status="已完成",
                final_output_path=tmp_path / "renders" / "final.wav",
            )
        ]
    )

    # The output label should show just the filename
    card = page._card_widgets[0]
    output_label = card.layout().itemAt(3).widget()
    assert output_label.text() == "final.wav"


def test_project_library_no_output_shows_placeholder(qtbot, tmp_path: Path) -> None:
    from ivo.core.project_library import ProjectLibraryItem
    from ivo.ui.project_library_page import ProjectLibraryPage

    page = ProjectLibraryPage()
    qtbot.addWidget(page)
    page.set_projects(
        [
            ProjectLibraryItem(
                name="NoOutput",
                path=tmp_path / "NoOutput.ivoproj",
                source_language="ja",
                target_language="zh",
                updated_at=1,
                status="未开始",
            )
        ]
    )

    card = page._card_widgets[0]
    output_label = card.layout().itemAt(3).widget()
    assert output_label.text() == "暂无输出"


# ── Task 1: Reflow timing ──────────────────────────────────────────────


def test_project_library_cards_reflow_after_first_show(qtbot, tmp_path: Path) -> None:
    from ivo.core.project_library import ProjectLibraryItem
    from ivo.ui.project_library_page import ProjectLibraryPage

    page = ProjectLibraryPage()
    page.resize(1280, 800)
    qtbot.addWidget(page)
    page.set_projects(
        [
            ProjectLibraryItem(
                name=f"Project{i}",
                path=tmp_path / f"Project{i}.ivoproj",
                source_language="ja",
                target_language="zh",
                updated_at=float(i),
                status="已完成",
            )
            for i in range(6)
        ]
    )

    page.show()
    qtbot.wait(100)

    # After show + event loop, cards should be reflowed correctly
    assert len(page._card_widgets) == 6
    # Verify cards exist and have fixed size
    for card in page._card_widgets:
        assert card.width() == page._CARD_WIDTH
        assert card.height() == page._CARD_HEIGHT
    # With 1280 width, at least 3 cards should fit in the first row
    y0 = page._card_widgets[0].y()
    first_row_count = sum(1 for card in page._card_widgets if card.y() == y0)
    assert first_row_count >= 3


# ── Task 2: No-match empty state ───────────────────────────────────────


def test_project_library_shows_no_match_state_for_empty_filter(qtbot, tmp_path: Path) -> None:
    from ivo.core.project_library import ProjectLibraryItem
    from ivo.ui.project_library_page import ProjectLibraryPage

    page = ProjectLibraryPage()
    qtbot.addWidget(page)
    page.set_projects(
        [
            ProjectLibraryItem(
                name="Episode 01",
                path=tmp_path / "Episode 01.ivoproj",
                source_language="ja",
                target_language="zh",
                updated_at=1,
                status="已完成",
            )
        ]
    )

    page._search_edit.setText("does-not-exist")

    assert page.project_count() == 0
    assert "没有匹配项目" in page.summary_text()
    assert "清空筛选" in page.summary_text()


def test_project_library_clear_filters_restores_cards(qtbot, tmp_path: Path) -> None:
    from ivo.core.project_library import ProjectLibraryItem
    from ivo.ui.project_library_page import ProjectLibraryPage

    page = ProjectLibraryPage()
    qtbot.addWidget(page)
    page.set_projects(
        [
            ProjectLibraryItem(
                name="Episode 01",
                path=tmp_path / "Episode 01.ivoproj",
                source_language="ja",
                target_language="zh",
                updated_at=1,
                status="已完成",
            )
        ]
    )

    # Apply a filter that yields no results
    page._search_edit.setText("does-not-exist")
    assert page.project_count() == 0

    # Clear filters
    page._clear_filters()
    assert page.project_count() == 1
    assert "Episode 01" in page.summary_text()


# ── Task 3: Empty state layout ─────────────────────────────────────────


def test_project_library_empty_state_uses_compact_actions(qtbot) -> None:
    from ivo.ui.project_library_page import ProjectLibraryPage

    page = ProjectLibraryPage()
    page.resize(900, 650)
    qtbot.addWidget(page)
    page.set_projects([])
    page.show()
    qtbot.wait(50)

    assert page.empty_state is not None
    assert page.empty_state.maximumWidth() <= 560
    assert page.open_existing_project_button.maximumWidth() <= 240
    # Toolbar and stats should be hidden when no projects
    assert not page._toolbar_widget.isVisible()
    assert not page._stats_widget.isVisible()


# ── Task 4: Extended search ────────────────────────────────────────────


def test_project_library_searches_target_language_type_status_and_output(
    qtbot, tmp_path: Path
) -> None:
    from ivo.core.project_library import ProjectLibraryItem
    from ivo.ui.project_library_page import ProjectLibraryPage

    page = ProjectLibraryPage()
    qtbot.addWidget(page)
    page.set_projects(
        [
            ProjectLibraryItem(
                name="VideoDone",
                path=tmp_path / "VideoDone.ivoproj",
                content_type="video",
                source_language="ja",
                target_language="zh",
                updated_at=2,
                status="已完成",
                status_detail="总耗时 00:02:10",
                final_output_path=tmp_path / "renders" / "final-video.mp4",
            ),
            ProjectLibraryItem(
                name="AudioRunning",
                path=tmp_path / "AudioRunning.ivoproj",
                content_type="audio",
                source_language="en",
                target_language="zh",
                updated_at=1,
                status="生成中",
                status_detail="正在生成配音 42%",
            ),
        ]
    )

    # Search by content type
    page._search_edit.setText("音频")
    assert page.project_count() == 1
    assert "AudioRunning" in page.summary_text()

    # Search by status
    page._search_edit.setText("生成中")
    assert page.project_count() == 1
    assert "AudioRunning" in page.summary_text()

    # Search by output filename
    page._search_edit.setText("final-video")
    assert page.project_count() == 1
    assert "VideoDone" in page.summary_text()


def test_project_library_card_emits_delete_signal(qtbot, tmp_path: Path) -> None:
    from ivo.core.project_library import ProjectLibraryItem
    from ivo.ui.project_library_page import ProjectLibraryPage

    project_path = tmp_path / "ToDelete.ivoproj"
    page = ProjectLibraryPage()
    qtbot.addWidget(page)
    page.set_projects(
        [
            ProjectLibraryItem(
                name="ToDelete",
                path=project_path,
                source_language="en",
                target_language="zh",
                updated_at=1,
                status="未开始",
            )
        ]
    )

    received: list[Path] = []
    page.delete_project_requested.connect(lambda p: received.append(p))

    # Find the delete button in the first card
    card = page._card_widgets[0]
    buttons = card.findChildren(QPushButton)
    delete_btn = next(btn for btn in buttons if btn.text() == "删除")
    delete_btn.click()

    assert received == [project_path]
