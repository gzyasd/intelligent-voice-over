from __future__ import annotations

import json
from datetime import date


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


def test_evaluation_report_counts_tts_quality_flags(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.evaluation import build_project_evaluation_report, render_evaluation_markdown

    project = DubbingProject.create(
        tmp_path / "tts-quality-eval.ivoproj",
        name="TTS Quality Eval",
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
            quality_flags=["duration_too_short", "duration_too_long", "tts_retried", "silent_audio"],
        )
    )

    report = build_project_evaluation_report(project)
    markdown = render_evaluation_markdown(report)

    assert report.quality_flag_counts == {
        "duration_too_long": 1,
        "duration_too_short": 1,
        "silent_audio": 1,
        "tts_retried": 1,
    }
    assert "| duration_too_short | 1 |" in markdown
    assert "| tts_retried | 1 |" in markdown


def test_evaluation_report_includes_review_summary(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.evaluation import build_project_evaluation_report, render_evaluation_markdown

    project = DubbingProject.create(
        tmp_path / "review-summary.ivoproj",
        name="Review Summary",
        source_language="en",
        target_language="zh",
    )
    for segment_id, status, flags in [
        ("seg-001", "needs_review", ["duration_too_long"]),
        ("seg-002", "approved", []),
        ("seg-003", "rendered", []),
    ]:
        project.timeline.add_segment(
            DubbingSegment(
                id=segment_id,
                start_ms=0,
                end_ms=1_000,
                speaker_id="speaker-1",
                source_language="en",
                source_text="Hello.",
                target_language="zh",
                target_text="你好。",
                status=status,
                quality_flags=flags,
            )
        )

    report = build_project_evaluation_report(project)
    markdown = render_evaluation_markdown(report)

    assert report.review_summary.total_segments == 3
    assert report.review_summary.reviewed_segments == 2
    assert report.review_summary.rendered_segments == 1
    assert report.review_summary.quality_flagged_segments == 1
    assert "已审核片段：2" in markdown


def test_evaluate_batch_cli_outputs_project_summaries(tmp_path) -> None:
    from typer.testing import CliRunner

    from ivo.cli import app
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment

    good = DubbingProject.create(
        tmp_path / "episode-01.ivoproj",
        name="Episode 01",
        source_language="en",
        target_language="zh",
    )
    good.timeline.add_segment(
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
        )
    )
    broken = DubbingProject.create(
        tmp_path / "episode-02.ivoproj",
        name="Episode 02",
        source_language="ko",
        target_language="zh",
    )
    broken.timeline.add_segment(
        DubbingSegment(
            id="seg-001",
            start_ms=0,
            end_ms=1_000,
            speaker_id="speaker-1",
            source_language="ko",
            source_text="annyeonghaseyo.",
            target_language="zh",
            target_text="你好。",
            status="failed",
            quality_flags=["tts_failed"],
        )
    )
    broken.jobs.mark_failed("tts", "provider offline")
    output_path = tmp_path / "batch-evaluation.json"

    result = CliRunner().invoke(
        app,
        [
            "evaluate-batch",
            str(tmp_path),
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert output_path.is_file()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["project_count"] == 2
    assert payload["total_segments"] == 2
    assert payload["projects_with_failed_jobs"] == 1
    assert payload["quality_flag_counts"] == {"tts_failed": 1}
    assert payload["projects"][1]["failed_jobs"] == ["tts"]
    assert "Batch evaluation written" in result.output


def test_evaluation_document_mentions_evaluate_project_command() -> None:
    from pathlib import Path

    document = Path("docs/evaluation/real-video-evaluation.md").read_text(encoding="utf-8")

    assert "uv run ivo evaluate-project" in document
    assert "状态、质量标记和作业状态摘要" in document


def test_acceptance_matrix_documents_required_fields() -> None:
    from pathlib import Path

    text = Path("docs/evaluation/acceptance-matrix.md").read_text(encoding="utf-8")

    for heading in (
        "## 阶段验收矩阵",
        "## 样片分层",
        "## 模型组合",
        "## 通过条件",
        "## 失败处理",
    ):
        assert heading in text


def test_render_run_markdown_includes_command_and_result() -> None:
    from ivo.evaluation_runs import EvaluationRunRecord, render_run_markdown

    record = EvaluationRunRecord(
        date="2026-06-05",
        title="Real F5 20s",
        source_language="ja",
        duration_seconds=20,
        profile_path="examples/local_command_profiles.real_separation_asr_tts_f5_cpu_small.json",
        command="uv run ivo local-preview sample.mp4 output --profiles profile.json",
        output_video="C:/Temp/output.ivoproj/renders/local-preview.mp4",
        status="passed",
        notes=["5 segments rendered", "CPU F5 took about 7 minutes"],
    )

    markdown = render_run_markdown(record)

    assert "# 2026-06-05 Real F5 20s" in markdown
    assert "source_language: ja" in markdown
    assert "status: passed" in markdown
    assert "uv run ivo local-preview" in markdown
    assert "5 segments rendered" in markdown


def test_evaluation_write_run_cli_writes_markdown(tmp_path) -> None:
    from typer.testing import CliRunner

    from ivo.cli import app

    output = tmp_path / "run.md"

    result = CliRunner().invoke(
        app,
        [
            "evaluation",
            "write-run",
            "--title",
            "Real F5 20s",
            "--source-language",
            "ja",
            "--duration-seconds",
            "20",
            "--profile",
            "examples/local_command_profiles.real_separation_asr_tts_f5_cpu_small.json",
            "--command",
            "uv run ivo local-preview sample.mp4 output --profiles profile.json",
            "--output-video",
            "C:/Temp/output.ivoproj/renders/local-preview.mp4",
            "--status",
            "passed",
            "--note",
            "5 segments rendered",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0
    assert output.is_file()
    text = output.read_text(encoding="utf-8")
    assert f"# {date.today().isoformat()} Real F5 20s" in text
    assert "5 segments rendered" in text
