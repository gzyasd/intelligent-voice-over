from __future__ import annotations

import json


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
        source_video=source,
    )

    loaded = DubbingProject.load(project_path)

    assert loaded.source_video_path == source
    metadata = json.loads((project_path / "project.json").read_text(encoding="utf-8"))
    assert metadata["source_video_path"] == str(source)
