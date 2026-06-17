"""End-to-end test: audio file dubbing via mock pipeline.

Usage:
    uv run python scripts/test_audio_e2e.py <audio_file_path>

Example:
    uv run python scripts/test_audio_e2e.py "D:\\music\\speech.mp3"
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from ivo.core.project import DubbingProject
from ivo.pipeline.mock_pipeline import run_mock_dubbing_pipeline

PROJECT_NAME = "audio_e2e_test"
OUTPUT_DIR = Path("test_e2e_output")


def main(audio_file: Path) -> None:
    # Clean up previous run
    project_path = OUTPUT_DIR / f"{PROJECT_NAME}.ivoproj"
    if project_path.exists():
        shutil.rmtree(project_path, ignore_errors=True)

    assert audio_file.is_file(), f"Audio file not found: {audio_file}"

    print(f"Source audio: {audio_file}")
    print(f"Project path: {project_path}")
    print("Content type: audio")
    print("Source language: ja -> zh")

    # Create project
    project = DubbingProject.create(
        project_path,
        name=PROJECT_NAME,
        source_language="ja",
        target_language="zh",
        source_media=audio_file,
        content_type="audio",
    )
    print(f"\nProject created. content_type={project.content_type}")
    print(f"source_media_path={project.source_media_path}")

    # Run mock pipeline
    print("\nRunning mock dubbing pipeline...")
    result = run_mock_dubbing_pipeline(
        project,
        source_media=audio_file,
    )
    print(f"Mock pipeline completed. final_output={result.final_output}")

    # Verify output
    output_path = result.final_output
    assert output_path is not None, "final_output is None"
    assert output_path.exists(), f"Output file not found: {output_path}"
    assert output_path.is_file(), f"Output is not a file: {output_path}"

    file_size = output_path.stat().st_size
    print(f"Output file size: {file_size} bytes")
    assert file_size > 0, "Output file is empty"

    # Verify output is WAV (local preview default for audio)
    assert output_path.suffix.lower() == ".wav", f"Expected .wav, got {output_path.suffix}"

    # Verify timeline segments exist
    segments = project.timeline.list_segments()
    print(f"Timeline segments: {len(segments)}")
    for seg in segments:
        print(f"  [{seg.id}] {seg.start_ms}ms-{seg.end_ms}ms: {seg.source_text} -> {seg.target_text}")

    # Verify project stages
    print("\nJob statuses:")
    for stage in ["import", "audio_extract", "separation", "asr", "diarization", "translation", "tts", "export"]:
        job = project.jobs.get(stage)
        if job:
            print(f"  {stage}: {job.status}")

    print("\n" + "=" * 50)
    print("ALL CHECKS PASSED!")
    print("=" * 50)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_audio_e2e.py <audio_file_path>")
        sys.exit(1)
    main(Path(sys.argv[1]))
