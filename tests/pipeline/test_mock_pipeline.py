from __future__ import annotations


def test_run_mock_dubbing_pipeline_creates_preview_video_and_timeline(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.pipeline.mock_pipeline import run_mock_dubbing_pipeline

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    project = DubbingProject.create(
        tmp_path / "mock.ivoproj",
        name="Mock",
        source_language="en",
        target_language="zh",
    )

    result = run_mock_dubbing_pipeline(project, source_video=source)

    assert result.final_video == project.path / "renders" / "preview.mp4"
    assert result.final_video.read_bytes() == b"mock-final-video"
    assert result.metadata["ai_dubbing"] == "true"
    assert [segment.target_text for segment in project.timeline.list_segments()] == ["嗯，你好。"]
    assert project.timeline.get_segment("seg-001").status == "rendered"
