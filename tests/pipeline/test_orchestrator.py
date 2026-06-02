from __future__ import annotations

import pytest


def test_job_store_persists_stage_status(tmp_path) -> None:
    from ivo.core.project import DubbingProject

    project = DubbingProject.create(
        tmp_path / "jobs.ivoproj",
        name="Jobs",
        source_language="en",
        target_language="zh",
    )

    project.jobs.mark_running("translate", "translating")
    project.jobs.mark_completed("translate", "done")

    reloaded = DubbingProject.load(project.path)
    record = reloaded.jobs.get("translate")

    assert record is not None
    assert record.stage == "translate"
    assert record.status == "completed"
    assert record.message == "done"


def test_orchestrator_skips_completed_stages_when_resuming(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.pipeline.orchestrator import PipelineOrchestrator, PipelineStage

    project = DubbingProject.create(
        tmp_path / "resume.ivoproj",
        name="Resume",
        source_language="en",
        target_language="zh",
    )
    project.jobs.mark_completed("import", "already done")
    calls: list[str] = []
    events: list[str] = []

    orchestrator = PipelineOrchestrator(
        project,
        stages=[
            PipelineStage("import", lambda current: calls.append("import")),
            PipelineStage("translate", lambda current: calls.append("translate")),
        ],
        on_progress=lambda event: events.append(f"{event.stage}:{event.message}"),
    )

    orchestrator.run()

    assert calls == ["translate"]
    assert project.jobs.get("translate").status == "completed"  # type: ignore[union-attr]
    assert events == ["import:skipped completed stage", "translate:running", "translate:completed"]


def test_orchestrator_persists_failure_and_can_resume(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.pipeline.orchestrator import PipelineOrchestrator, PipelineStage, PipelineStageError

    project = DubbingProject.create(
        tmp_path / "failure.ivoproj",
        name="Failure",
        source_language="en",
        target_language="zh",
    )

    def fail(current: DubbingProject) -> None:
        raise RuntimeError("provider offline")

    with pytest.raises(PipelineStageError, match="translate"):
        PipelineOrchestrator(project, [PipelineStage("translate", fail)]).run()

    failed = DubbingProject.load(project.path)
    assert failed.jobs.get("translate").status == "failed"  # type: ignore[union-attr]

    calls: list[str] = []
    PipelineOrchestrator(
        failed,
        [PipelineStage("translate", lambda current: calls.append("translate"))],
    ).run()

    assert calls == ["translate"]
    assert DubbingProject.load(project.path).jobs.get("translate").status == "completed"  # type: ignore[union-attr]


def test_regenerate_segment_applies_edits_and_reruns_tts(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.pipeline.orchestrator import regenerate_segment
    from ivo.pipeline.synthesize import MockTtsAdapter

    project = DubbingProject.create(
        tmp_path / "regen.ivoproj",
        name="Regen",
        source_language="en",
        target_language="zh",
    )
    project.timeline.add_segment(
        DubbingSegment(
            id="seg-001",
            start_ms=0,
            end_ms=1_000,
            speaker_id="speaker-1",
            source_language="en",
            source_text="Hello.",
            target_language="zh",
            target_text="你好。",
            status="approved",
        )
    )

    result = regenerate_segment(
        project,
        "seg-001",
        MockTtsAdapter(),
        target_text="嗯，你好。",
        style_prompt="warm",
    )

    updated = project.timeline.get_segment("seg-001")
    assert updated.target_text == "嗯，你好。"
    assert updated.style_prompt == "warm"
    assert result.audio_path.is_file()
