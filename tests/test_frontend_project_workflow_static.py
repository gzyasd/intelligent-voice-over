from __future__ import annotations

from pathlib import Path
import re


def test_sidebar_does_not_add_project_workflow_menu_items() -> None:
    source = Path("src/components/layout/AppLayout.vue").read_text(encoding="utf-8")

    assert "projectEntries" not in source
    assert "hasCurrentProject" not in source
    assert "requiresProject" not in source
    assert "['/pipeline', '/timeline', '/export']" not in source


def test_current_project_embeds_generation_workflow_and_starts_directly() -> None:
    source = Path("src/pages/ProjectOverview.vue").read_text(encoding="utf-8")

    assert "usePipelineStore" in source
    assert "pipelineStore.start()" in source
    assert "pipeline-card" in source
    assert "overview-header" in source
    assert "goTimeline" in source
    assert "goExport" in source
    assert "goPipeline" not in source


def test_current_project_page_has_no_question_mark_placeholder_copy() -> None:
    source = Path("src/pages/ProjectOverview.vue").read_text(encoding="utf-8")

    placeholder_patterns = [
        r"'[?]{2,}'",
        r'"[?]{2,}"',
        r">[?]{2,}<",
        r'label="[?]{2,}"',
        r"description=\"[?]{2,}",
    ]

    for pattern in placeholder_patterns:
        assert not re.search(pattern, source), pattern

    for expected_copy in [
        "开始生成",
        "查看进度",
        "继续/重试生成",
        "查看成品",
        "项目信息",
        "总进度",
        "运行日志",
    ]:
        assert expected_copy in source


def test_current_project_uses_runtime_sync_instead_of_unconditional_history_reset() -> None:
    overview = Path("src/pages/ProjectOverview.vue").read_text(encoding="utf-8")
    pipeline_page = Path("src/pages/PipelineRun.vue").read_text(encoding="utf-8")

    assert "synchronizeWithBackend" in overview
    assert "pipelineStore.restoreFromBackend" not in overview
    assert "onUnmounted(() => {" not in pipeline_page
    assert "store.reset()" not in pipeline_page


def test_current_project_layout_is_compact_and_logs_scroll_independently() -> None:
    source = Path("src/pages/ProjectOverview.vue").read_text(encoding="utf-8")

    assert 'size="small"' in source
    assert "description-label-style" in source
    assert "white-space: nowrap" in source
    assert ".overview-page {" in source
    assert "height: 100%" in source
    assert "overflow: hidden" in source
    assert ".pipeline-grid {" in source
    assert "min-height: 0" in source
    assert ".pipeline-logs {" in source


def test_project_library_cards_keep_equal_height_with_fixed_actions() -> None:
    source = Path("src/pages/ProjectLibrary.vue").read_text(encoding="utf-8")

    assert 'class="project-grid"' in source
    assert 'class="project-grid-item"' in source
    assert ".project-card {" in source
    assert "height: 100%" in source
    assert "display: flex" in source
    assert "flex-direction: column" in source
    assert ":deep(.project-card > .n-card__content)" in source
    assert ":deep(.project-card > .n-card__action)" in source
    assert ".project-grid {" in source
    assert "align-items: stretch" in source


def test_project_overview_shows_total_and_current_stage_elapsed_time() -> None:
    """ProjectOverview 应同时显示总耗时和当前阶段耗时。"""
    source = Path("src/pages/ProjectOverview.vue").read_text(encoding="utf-8")

    assert "总进度" in source
    assert "当前阶段耗时" in source
    assert "currentStageElapsedSeconds" in source
    assert "stage.elapsedSeconds" in source
    assert "stage-elapsed" in source
    assert "formatElapsed" in source


def test_project_library_displays_generation_elapsed_time() -> None:
    """ProjectLibrary 卡片应显示生成耗时字段。"""
    source = Path("src/pages/ProjectLibrary.vue").read_text(encoding="utf-8")

    assert "elapsed_seconds" in source or "elapsedSeconds" in source
