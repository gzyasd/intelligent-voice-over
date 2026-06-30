from __future__ import annotations

from pathlib import Path


def test_project_status_snapshot_marks_completed_video(tmp_path: Path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.project_status import read_project_status_snapshot

    project = DubbingProject.create(
        tmp_path / "Video.ivoproj",
        name="Video",
        source_language="ja",
        target_language="zh",
        source_media=tmp_path / "source.mp4",
    )
    output = project.path / "renders" / "local-preview.mp4"
    output.write_bytes(b"video")
    project.jobs.mark_completed("export")
    project.mark_generation_completed(now=120.0, elapsed_seconds=65)

    snapshot = read_project_status_snapshot(project.path, active_project_paths=set())

    assert snapshot.project_path == project.path
    assert snapshot.name == "Video"
    assert snapshot.lifecycle == "completed"
    assert snapshot.status_label == "已完成"
    assert snapshot.primary_action == "open_output"
    assert snapshot.final_output_path == output
    assert snapshot.elapsed_seconds == 65


def test_project_status_snapshot_marks_stale_running_when_not_active(tmp_path: Path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.project_status import read_project_status_snapshot

    project = DubbingProject.create(
        tmp_path / "Interrupted.ivoproj",
        name="Interrupted",
        source_language="en",
        target_language="zh",
    )
    project.mark_generation_started(now=100.0)
    project.jobs.mark_running("separation")

    snapshot = read_project_status_snapshot(project.path, active_project_paths=set())

    assert snapshot.lifecycle == "interrupted"
    assert snapshot.status_label == "上次中断"
    assert snapshot.primary_action == "resume"
    assert "separation" in snapshot.status_detail


def test_project_status_snapshot_marks_active_running(tmp_path: Path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.project_status import read_project_status_snapshot

    project = DubbingProject.create(
        tmp_path / "Running.ivoproj",
        name="Running",
        source_language="ko",
        target_language="zh",
    )
    project.mark_generation_started(now=100.0)
    project.jobs.mark_running("tts")

    snapshot = read_project_status_snapshot(
        project.path,
        active_project_paths={project.path.resolve()},
    )

    assert snapshot.lifecycle == "running"
    assert snapshot.status_label == "生成中"
    assert snapshot.primary_action == "progress"


def test_project_status_snapshot_finds_audio_output(tmp_path: Path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.project_status import read_project_status_snapshot

    project = DubbingProject.create(
        tmp_path / "Audio.ivoproj",
        name="Audio",
        source_language="ja",
        target_language="zh",
        content_type="audio",
        source_media=tmp_path / "source.mp3",
    )
    output = project.path / "renders" / "local-preview.wav"
    output.write_bytes(b"audio")
    project.jobs.mark_completed("export")

    snapshot = read_project_status_snapshot(project.path, active_project_paths=set())

    assert snapshot.content_type == "audio"
    assert snapshot.final_output_path == output
    assert snapshot.open_output_enabled is True


def test_job_store_records_stage_elapsed_seconds(tmp_path: Path) -> None:
    from ivo.core.jobs import JobStore

    store = JobStore(tmp_path / "jobs.sqlite")
    store.mark_running("tts", "running", now=100.0)
    store.mark_completed("tts", "completed", now=145.4)

    record = store.get("tts")

    assert record is not None
    assert record.stage == "tts"
    assert record.status == "completed"
    assert record.started_at == 100.0
    assert record.completed_at == 145.4
    assert record.elapsed_seconds == 45


def test_project_status_snapshot_exposes_running_elapsed_seconds(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import ivo.core.project_status as project_status
    from ivo.core.project import DubbingProject

    project = DubbingProject.create(
        tmp_path / "RunningTimed.ivoproj",
        name="RunningTimed",
        source_language="ja",
        target_language="zh",
    )
    project.mark_generation_started(now=100.0)
    project.jobs.mark_running("tts", now=110.0)
    monkeypatch.setattr(project_status.time, "time", lambda: 145.0)

    snapshot = project_status.read_project_status_snapshot(
        project.path,
        active_project_paths={project.path.resolve()},
    )

    assert snapshot.elapsed_seconds == 45
    assert snapshot.generation_started_at == 100.0
    assert snapshot.generation_elapsed_seconds == 45
