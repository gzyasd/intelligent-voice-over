from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from ivo.core.jobs import JobRecord
from ivo.core.project import DubbingProject
from ivo.core.timeline import SourceLanguage, TargetLanguage


class ReviewSummary(BaseModel):
    total_segments: int
    reviewed_segments: int
    rendered_segments: int
    quality_flagged_segments: int


class ProjectEvaluationReport(BaseModel):
    project_name: str
    project_path: Path
    source_language: SourceLanguage
    target_language: TargetLanguage
    segment_count: int
    speaker_count: int
    status_counts: dict[str, int]
    quality_flag_counts: dict[str, int]
    review_summary: ReviewSummary
    jobs: list[JobRecord]


class BatchProjectEvaluationSummary(BaseModel):
    project_name: str
    project_path: Path
    segment_count: int
    status_counts: dict[str, int]
    quality_flag_counts: dict[str, int]
    failed_jobs: list[str]


class BatchEvaluationReport(BaseModel):
    project_count: int
    total_segments: int
    projects_with_failed_jobs: int
    status_counts: dict[str, int]
    quality_flag_counts: dict[str, int]
    projects: list[BatchProjectEvaluationSummary]


def build_project_evaluation_report(project: DubbingProject) -> ProjectEvaluationReport:
    segments = project.timeline.list_segments()
    status_counts: dict[str, int] = {}
    quality_flag_counts: dict[str, int] = {}
    speakers: set[str] = set()

    for segment in segments:
        status_counts[segment.status] = status_counts.get(segment.status, 0) + 1
        speakers.add(segment.speaker_id)
        for flag in segment.quality_flags:
            quality_flag_counts[flag] = quality_flag_counts.get(flag, 0) + 1

    return ProjectEvaluationReport(
        project_name=project.name,
        project_path=project.path,
        source_language=project.source_language,
        target_language=project.target_language,
        segment_count=len(segments),
        speaker_count=len(speakers),
        status_counts=dict(sorted(status_counts.items())),
        quality_flag_counts=dict(sorted(quality_flag_counts.items())),
        review_summary=ReviewSummary(
            total_segments=len(segments),
            reviewed_segments=sum(
                1 for segment in segments if segment.status in {"approved", "rendered"}
            ),
            rendered_segments=sum(1 for segment in segments if segment.status == "rendered"),
            quality_flagged_segments=sum(1 for segment in segments if segment.quality_flags),
        ),
        jobs=project.jobs.list_records(),
    )


def build_batch_evaluation_report(project_paths: list[Path]) -> BatchEvaluationReport:
    projects: list[BatchProjectEvaluationSummary] = []
    status_counts: dict[str, int] = {}
    quality_flag_counts: dict[str, int] = {}
    total_segments = 0

    for project_path in sorted(project_paths):
        report = build_project_evaluation_report(DubbingProject.load(project_path))
        failed_jobs = [job.stage for job in report.jobs if job.status == "failed"]
        total_segments += report.segment_count
        _merge_counts(status_counts, report.status_counts)
        _merge_counts(quality_flag_counts, report.quality_flag_counts)
        projects.append(
            BatchProjectEvaluationSummary(
                project_name=report.project_name,
                project_path=report.project_path,
                segment_count=report.segment_count,
                status_counts=report.status_counts,
                quality_flag_counts=report.quality_flag_counts,
                failed_jobs=failed_jobs,
            )
        )

    return BatchEvaluationReport(
        project_count=len(projects),
        total_segments=total_segments,
        projects_with_failed_jobs=sum(1 for project in projects if project.failed_jobs),
        status_counts=dict(sorted(status_counts.items())),
        quality_flag_counts=dict(sorted(quality_flag_counts.items())),
        projects=projects,
    )


def _merge_counts(target: dict[str, int], source: dict[str, int]) -> None:
    for key, count in source.items():
        target[key] = target.get(key, 0) + count


def render_evaluation_markdown(report: ProjectEvaluationReport) -> str:
    lines = [
        f"# 项目评估报告：{report.project_name}",
        "",
        "## 基本信息",
        "",
        f"- 项目路径：`{report.project_path}`",
        f"- 源语言：{report.source_language}",
        f"- 目标语言：{report.target_language}",
        f"- 片段数：{report.segment_count}",
        f"- 说话人数：{report.speaker_count}",
        f"- 总片段：{report.review_summary.total_segments}",
        f"- 已审核片段：{report.review_summary.reviewed_segments}",
        f"- 已生成片段：{report.review_summary.rendered_segments}",
        f"- 有质量标记片段：{report.review_summary.quality_flagged_segments}",
        "",
        "## 片段状态",
        "",
        "| 状态 | 数量 |",
        "| --- | --- |",
    ]
    lines.extend(
        f"| {status} | {count} |" for status, count in report.status_counts.items()
    )
    if not report.status_counts:
        lines.append("| none | 0 |")

    lines.extend(["", "## 质量标记", "", "| 标记 | 数量 |", "| --- | --- |"])
    lines.extend(
        f"| {flag} | {count} |" for flag, count in report.quality_flag_counts.items()
    )
    if not report.quality_flag_counts:
        lines.append("| none | 0 |")

    lines.extend(["", "## 作业状态", "", "| 阶段 | 状态 | 信息 |", "| --- | --- | --- |"])
    lines.extend(f"| {job.stage} | {job.status} | {job.message} |" for job in report.jobs)
    if not report.jobs:
        lines.append("| none | none | no job records |")
    lines.append("")
    return "\n".join(lines)
