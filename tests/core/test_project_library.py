from __future__ import annotations

from pathlib import Path


def test_scan_project_library_reads_project_status_and_final_video(tmp_path: Path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.project_library import scan_project_library

    runs_dir = tmp_path / "runs"
    completed = DubbingProject.create(
        runs_dir / "Episode 01.ivoproj",
        name="Episode 01",
        source_language="ja",
        target_language="zh",
        source_video=tmp_path / "episode01.mp4",
    )
    completed.jobs.mark_completed("export", "completed")
    final_video = completed.path / "renders" / "local-preview.mp4"
    final_video.write_bytes(b"video")
    failed = DubbingProject.create(
        runs_dir / "Episode 02.ivoproj",
        name="Episode 02",
        source_language="ko",
        target_language="zh",
    )
    failed.jobs.mark_failed("tts", "model missing")

    items = scan_project_library(runs_dir, recent_projects=[])

    assert [item.name for item in items] == ["Episode 02", "Episode 01"]
    by_name = {item.name: item for item in items}
    assert by_name["Episode 01"].status == "已完成"
    assert by_name["Episode 01"].final_video_path == final_video
    assert by_name["Episode 02"].status == "失败"
    assert by_name["Episode 02"].status_detail == "tts: model missing"


def test_scan_project_library_reads_generation_elapsed_seconds(tmp_path: Path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.project_library import scan_project_library

    runs_dir = tmp_path / "runs"
    project = DubbingProject.create(
        runs_dir / "Timed.ivoproj",
        name="Timed",
        source_language="en",
        target_language="zh",
    )
    project.mark_generation_started(now=100.0)
    project.mark_generation_completed(now=165.4)

    items = scan_project_library(runs_dir, recent_projects=[])

    assert items[0].name == "Timed"
    assert items[0].status == "已完成"
    assert items[0].elapsed_seconds == 65
    assert "总耗时 01:05" in items[0].status_detail


def test_scan_project_library_includes_recent_project_outside_runs(tmp_path: Path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.project_library import scan_project_library

    project = DubbingProject.create(
        tmp_path / "external" / "External.ivoproj",
        name="External",
        source_language="en",
        target_language="zh",
    )

    items = scan_project_library(tmp_path / "runs", recent_projects=[project.path])

    assert [item.name for item in items] == ["External"]
    assert items[0].path == project.path


def test_scan_project_library_keeps_unreadable_projects_visible(tmp_path: Path) -> None:
    from ivo.core.project_library import scan_project_library

    broken = tmp_path / "runs" / "Broken.ivoproj"
    broken.mkdir(parents=True)

    items = scan_project_library(tmp_path / "runs", recent_projects=[])

    assert len(items) == 1
    assert items[0].name == "Broken"
    assert items[0].status == "无法读取"
    assert items[0].status_detail
