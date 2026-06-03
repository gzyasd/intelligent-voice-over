from __future__ import annotations

import json


def test_build_project_evaluation_report_summarizes_timeline_and_jobs(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.evaluation import build_project_evaluation_report, render_evaluation_markdown

    project = DubbingProject.create(
        tmp_path / "eval.ivoproj",
        name="Eval",
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
            status="rendered",
            quality_flags=["duration_ok"],
        )
    )
    project.timeline.add_segment(
        DubbingSegment(
            id="seg-002",
            start_ms=1_100,
            end_ms=2_000,
            speaker_id="speaker-2",
            source_language="en",
            source_text="Wait.",
            target_language="zh",
            target_text="等等。",
            status="needs_review",
            quality_flags=["duration_mismatch", "speaker_unmatched"],
        )
    )
    project.jobs.mark_completed("asr", "completed")
    project.jobs.mark_failed("tts", "provider offline")

    report = build_project_evaluation_report(project)
    markdown = render_evaluation_markdown(report)

    assert report.project_name == "Eval"
    assert report.segment_count == 2
    assert report.speaker_count == 2
    assert report.status_counts == {"needs_review": 1, "rendered": 1}
    assert report.quality_flag_counts == {
        "duration_mismatch": 1,
        "duration_ok": 1,
        "speaker_unmatched": 1,
    }
    assert [job.stage for job in report.jobs] == ["asr", "tts"]
    assert "# 项目评估报告：Eval" in markdown
    assert "| duration_mismatch | 1 |" in markdown
    assert "| tts | failed | provider offline |" in markdown


def test_evaluate_project_cli_outputs_json_and_markdown(tmp_path) -> None:
    from typer.testing import CliRunner

    from ivo.cli import app
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment

    project = DubbingProject.create(
        tmp_path / "cli-eval.ivoproj",
        name="CLI Eval",
        source_language="ja",
        target_language="zh",
    )
    project.timeline.add_segment(
        DubbingSegment(
            id="seg-001",
            start_ms=0,
            end_ms=1_000,
            speaker_id="speaker-1",
            source_language="ja",
            source_text="こんにちは。",
            target_language="zh",
            target_text="你好。",
            status="rendered",
            quality_flags=["duration_ok"],
        )
    )
    output_path = tmp_path / "report.md"

    json_result = CliRunner().invoke(app, ["evaluate-project", str(project.path), "--format", "json"])
    markdown_result = CliRunner().invoke(
        app,
        [
            "evaluate-project",
            str(project.path),
            "--format",
            "markdown",
            "--output",
            str(output_path),
        ],
    )

    payload = json.loads(json_result.output)
    assert json_result.exit_code == 0
    assert payload["project_name"] == "CLI Eval"
    assert payload["quality_flag_counts"] == {"duration_ok": 1}
    assert markdown_result.exit_code == 0
    assert output_path.is_file()
    assert "# 项目评估报告：CLI Eval" in output_path.read_text(encoding="utf-8")


def test_evaluation_document_mentions_evaluate_project_command() -> None:
    from pathlib import Path

    document = Path("docs/evaluation/real-video-evaluation.md").read_text(encoding="utf-8")

    assert "uv run ivo evaluate-project" in document
    assert "状态、质量标记和作业状态摘要" in document
