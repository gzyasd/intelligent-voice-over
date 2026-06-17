from __future__ import annotations

from pathlib import Path


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

    result = run_mock_dubbing_pipeline(project, source_media=source)

    assert result.final_output == project.path / "renders" / "preview.mp4"
    assert result.final_output.read_bytes() == b"mock-final-video"
    assert result.metadata["ai_dubbing"] == "true"
    assert [segment.target_text for segment in project.timeline.list_segments()] == ["嗯，你好。"]
    assert project.timeline.get_segment("seg-001").status == "rendered"


def test_mock_audio_pipeline_outputs_wav(tmp_path: Path) -> None:
    """Mock pipeline with audio content_type produces preview.wav."""
    from ivo.core.project import DubbingProject
    from ivo.pipeline.mock_pipeline import run_mock_dubbing_pipeline

    source_audio = tmp_path / "speech.mp3"
    source_audio.write_bytes(b"mock audio")

    project_path = tmp_path / "audio_mock.ivoproj"
    project = DubbingProject.create(
        project_path,
        name="Mock Audio",
        source_language="ja",
        target_language="zh",
        source_media=source_audio,
        content_type="audio",
    )
    result = run_mock_dubbing_pipeline(project, source_media=source_audio)
    assert result.final_output is not None
    assert result.final_output.suffix == ".wav"
    assert result.final_output.is_file()
    assert result.final_output.stat().st_size > 0
