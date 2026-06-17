from __future__ import annotations

import json
from pathlib import Path


def test_create_project_initializes_workspace(tmp_path) -> None:
    from ivo.core.project import DubbingProject

    project_path = tmp_path / "episode-01.ivoproj"

    project = DubbingProject.create(
        project_path,
        name="Episode 01",
        source_language="en",
        target_language="zh",
    )

    assert project.path == project_path
    assert (project_path / "project.json").is_file()
    assert (project_path / "segments.sqlite").is_file()
    assert (project_path / "assets").is_dir()
    assert (project_path / "work").is_dir()
    assert (project_path / "renders").is_dir()

    metadata = json.loads((project_path / "project.json").read_text(encoding="utf-8"))
    assert metadata["name"] == "Episode 01"
    assert metadata["source_language"] == "en"
    assert metadata["target_language"] == "zh"


def test_load_project_reads_existing_metadata(tmp_path) -> None:
    from ivo.core.project import DubbingProject

    project_path = tmp_path / "episode-02.ivoproj"
    DubbingProject.create(
        project_path,
        name="Episode 02",
        source_language="ja",
        target_language="zh",
    )

    project = DubbingProject.load(project_path)

    assert project.name == "Episode 02"
    assert project.source_language == "ja"
    assert project.target_language == "zh"
    assert project.timeline.list_segments() == []


def test_project_metadata_persists_source_video_path(tmp_path) -> None:
    from ivo.core.project import DubbingProject

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    project_path = tmp_path / "episode-source.ivoproj"

    DubbingProject.create(
        project_path,
        name="Episode Source",
        source_language="ko",
        target_language="zh",
        source_media=source,
    )

    loaded = DubbingProject.load(project_path)

    assert loaded.source_media_path == source
    metadata = json.loads((project_path / "project.json").read_text(encoding="utf-8"))
    assert metadata["source_media_path"] == str(source)


def test_create_audio_project_sets_content_type(tmp_path: Path) -> None:
    """DubbingProject.create with content_type='audio' sets correct fields."""
    from ivo.core.project import DubbingProject

    project_path = tmp_path / "audio_proj.ivoproj"
    source_media = tmp_path / "test.mp3"
    source_media.write_bytes(b"fake audio")

    project = DubbingProject.create(
        project_path,
        name="Audio Project",
        source_language="ja",
        target_language="zh",
        source_media=source_media,
        content_type="audio",
    )
    assert project.content_type == "audio"
    assert project.source_media_path == source_media
    assert project.metadata.content_type == "audio"
    assert project.metadata.source_media_path == source_media
    # Verify project.json was written with correct fields
    metadata_path = project_path / "project.json"
    raw = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert raw["content_type"] == "audio"
    assert raw["source_media_path"] == str(source_media)
